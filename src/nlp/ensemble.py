"""Weighted ensemble sentiment scoring for retrieved news headlines."""

from __future__ import annotations

import json
import time
from collections import Counter
from typing import TypedDict

import pandas as pd

from src.config import PROCESSED_DIR, RESULTS_DIR
from src.nlp.classify_finbert import classify_finbert_proba
from src.nlp.classify_nb import classify_nb_proba, train_nb
from src.nlp.llm_local import OLLAMA_REQUEST_TIMEOUT_SECONDS, classify_local


LABELS = ["bearish", "neutral", "bullish"]
NB_WEIGHT = 0.35
FINBERT_WEIGHT = 0.65
LLM_WEIGHT = 0.75
NEWS_PATH = PROCESSED_DIR / "news.parquet"
RETRIEVAL_PATH = PROCESSED_DIR / "trade_news_retrieval.parquet"
NEWS_SENTIMENT_PATH = PROCESSED_DIR / "news_sentiment.parquet"
ROUTING_STATS_PATH = RESULTS_DIR / "nlp_routing.json"
SENTIMENT_COLUMNS = [
    "news_id",
    "headline",
    "label",
    "confidence",
    "source",
    "nb_label",
    "nb_confidence",
    "finbert_label",
    "finbert_confidence",
    "llm_label",
    "llm_confidence",
    "llm_elapsed_seconds",
]


class EnsembleClassification(TypedDict):
    """Sentiment output with ensemble metadata."""

    label: str
    confidence: float
    source: str


def _top_label(scores: dict[str, float]) -> tuple[str, float, float]:
    """Return top label, confidence, and margin to the runner-up."""
    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    top_label, top_score = ordered[0]
    runner_up = ordered[1][1] if len(ordered) > 1 else 0.0
    return top_label, float(top_score), float(top_score - runner_up)


def _weighted_scores(*weighted_votes: tuple[dict[str, float], float]) -> dict[str, float]:
    """Combine probability dictionaries with normalized weights."""
    total_weight = sum(weight for _, weight in weighted_votes)
    scores = dict.fromkeys(LABELS, 0.0)
    for probabilities, weight in weighted_votes:
        for label in LABELS:
            scores[label] += probabilities.get(label, 0.0) * weight
    return {label: score / total_weight for label, score in scores.items()}


def _label_confidence(probabilities: dict[str, float]) -> tuple[str, float]:
    """Return the highest-probability label and confidence."""
    label, confidence, _ = _top_label(probabilities)
    return label, confidence


def _llm_probabilities(label: str, confidence: float) -> dict[str, float]:
    """Convert a single LLM label/confidence into a probability-like vote."""
    confidence = max(0.0, min(1.0, confidence))
    remainder = (1.0 - confidence) / (len(LABELS) - 1)
    probabilities = dict.fromkeys(LABELS, remainder)
    probabilities[label] = confidence
    return probabilities


def classify_headline(text: str) -> EnsembleClassification:
    """Classify one headline with a weighted NB + FinBERT + Ollama ensemble."""
    nb_probabilities = classify_nb_proba([text])[0]
    finbert_probabilities = classify_finbert_proba([text])[0]
    llm_result = classify_local(text, timeout_seconds=OLLAMA_REQUEST_TIMEOUT_SECONDS)
    weighted_votes = [
        (nb_probabilities, NB_WEIGHT),
        (finbert_probabilities, FINBERT_WEIGHT),
    ]
    source = "ensemble_all_models"
    if llm_result["reasoning"] == "fallback":
        source = "ensemble_fallback"
    else:
        weighted_votes.append(
            (_llm_probabilities(llm_result["label"], llm_result["confidence"]), LLM_WEIGHT)
        )

    scores = _weighted_scores(*weighted_votes)
    label, confidence, _ = _top_label(scores)
    return {"label": label, "confidence": confidence, "source": source}


def _load_checked_news() -> pd.DataFrame:
    """Load only news rows whose news_id appears in trade-news retrieval."""
    if not NEWS_PATH.exists():
        raise FileNotFoundError(f"Missing processed news parquet: {NEWS_PATH}")
    if not RETRIEVAL_PATH.exists():
        raise FileNotFoundError(f"Missing retrieval parquet: {RETRIEVAL_PATH}")

    retrieval = pd.read_parquet(RETRIEVAL_PATH, columns=["news_id"])
    checked_ids = sorted(set(retrieval["news_id"].dropna().astype(int).tolist()))
    news = pd.read_parquet(NEWS_PATH)
    checked_news = news.loc[news["news_id"].isin(checked_ids)].copy()
    return checked_news.sort_values("news_id").reset_index(drop=True)


def _write_ensemble_stats(
    sentiment: pd.DataFrame,
    *,
    checked_news: int,
    total_news: int,
    retrieval_rows: int,
    llm_elapsed_seconds: float,
) -> dict[str, object]:
    """Persist ensemble usage counts and percentages."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    counts = Counter(sentiment["source"].astype(str))
    total = int(sum(counts.values()))
    stats = {
        "mode": "weighted_ensemble",
        "total_scored_news": total,
        "checked_news": checked_news,
        "total_processed_news": total_news,
        "retrieval_rows": retrieval_rows,
        "weights": {
            "nb": NB_WEIGHT,
            "finbert": FINBERT_WEIGHT,
            "ollama": LLM_WEIGHT,
        },
        "llm": {
            "policy": "run_on_every_checked_headline",
            "per_call_timeout_seconds": OLLAMA_REQUEST_TIMEOUT_SECONDS,
        },
        "llm_elapsed_seconds": round(llm_elapsed_seconds, 2),
        "counts": dict(sorted(counts.items())),
        "percentages": {
            source: round((count / total) * 100, 2) if total else 0.0
            for source, count in sorted(counts.items())
        },
    }
    ROUTING_STATS_PATH.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    return stats


def classify_news(news: pd.DataFrame) -> pd.DataFrame:
    """Score checked news with a weighted ensemble."""
    headlines = news["headline"].fillna("").astype(str).tolist()
    nb_rows = classify_nb_proba(headlines)
    finbert_rows = classify_finbert_proba(headlines)
    output_rows: list[dict[str, object]] = []

    for row, nb_probabilities, finbert_probabilities in zip(
        news.itertuples(index=False),
        nb_rows,
        finbert_rows,
        strict=True,
    ):
        weighted_votes = [
            (nb_probabilities, NB_WEIGHT),
            (finbert_probabilities, FINBERT_WEIGHT),
        ]
        source = "ensemble_all_models"
        llm_label = ""
        llm_confidence = 0.0
        llm_call_started_at = time.monotonic()
        llm_result = classify_local(
            str(row.headline),
            timeout_seconds=OLLAMA_REQUEST_TIMEOUT_SECONDS,
        )
        llm_elapsed_seconds = time.monotonic() - llm_call_started_at
        llm_label = llm_result["label"]
        llm_confidence = llm_result["confidence"]
        if llm_result["reasoning"] == "fallback":
            source = "ensemble_fallback"
        else:
            weighted_votes.append(
                (_llm_probabilities(llm_label, llm_confidence), LLM_WEIGHT)
            )

        scores = _weighted_scores(*weighted_votes)
        label, confidence, _ = _top_label(scores)

        nb_label, nb_confidence = _label_confidence(nb_probabilities)
        finbert_label, finbert_confidence = _label_confidence(finbert_probabilities)
        output_rows.append(
            {
                "news_id": int(row.news_id),
                "headline": str(row.headline),
                "label": label,
                "confidence": confidence,
                "source": source,
                "nb_label": nb_label,
                "nb_confidence": nb_confidence,
                "finbert_label": finbert_label,
                "finbert_confidence": finbert_confidence,
                "llm_label": llm_label,
                "llm_confidence": llm_confidence,
                "llm_elapsed_seconds": llm_elapsed_seconds,
            }
        )

    return pd.DataFrame(output_rows, columns=SENTIMENT_COLUMNS)


def run_classification_pipeline() -> pd.DataFrame:
    """Train NB if needed, classify retrieved news, and persist outputs."""
    train_nb(force=False)
    news = pd.read_parquet(NEWS_PATH)
    retrieval = pd.read_parquet(RETRIEVAL_PATH, columns=["news_id"])
    checked_news = _load_checked_news()
    sentiment = classify_news(checked_news)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    sentiment.to_parquet(NEWS_SENTIMENT_PATH, index=False)
    stats = _write_ensemble_stats(
        sentiment,
        checked_news=len(checked_news),
        total_news=len(news),
        retrieval_rows=len(retrieval),
        llm_elapsed_seconds=float(sentiment["llm_elapsed_seconds"].sum())
        if not sentiment.empty
        else 0.0,
    )

    print(f"News sentiment rows: {len(sentiment):,} -> {NEWS_SENTIMENT_PATH}")
    print(f"Ensemble stats: {json.dumps(stats, indent=2)}")
    print("Sample classifications:")
    print(sentiment.head(10).to_string(index=False))
    return sentiment


def main() -> None:
    """Run the weighted sentiment ensemble from the command line."""
    run_classification_pipeline()


if __name__ == "__main__":
    main()
