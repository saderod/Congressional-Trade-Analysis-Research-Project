"""Weighted ensemble sentiment scoring for retrieved news headlines."""

from __future__ import annotations

import json
from collections import Counter
from typing import TypedDict

import pandas as pd

from src.config import PROCESSED_DIR, RESULTS_DIR
from src.nlp.classify_finbert import classify_finbert_proba
from src.nlp.classify_nb import classify_nb_proba, train_nb
from src.nlp.llm_local import classify_local


LABELS = ["bearish", "neutral", "bullish"]
NB_WEIGHT = 0.35
FINBERT_WEIGHT = 0.65
LLM_WEIGHT = 0.75
ENSEMBLE_CONFIDENCE_THRESHOLD = 0.70
ENSEMBLE_MARGIN_THRESHOLD = 0.20
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


def _needs_llm(confidence: float, margin: float) -> bool:
    """Return True when the NB+FinBERT ensemble is too uncertain."""
    return confidence < ENSEMBLE_CONFIDENCE_THRESHOLD or margin < ENSEMBLE_MARGIN_THRESHOLD


def classify_headline(text: str) -> EnsembleClassification:
    """Classify one headline with a weighted NB + FinBERT ensemble and optional Ollama."""
    nb_probabilities = classify_nb_proba([text])[0]
    finbert_probabilities = classify_finbert_proba([text])[0]
    scores = _weighted_scores(
        (nb_probabilities, NB_WEIGHT),
        (finbert_probabilities, FINBERT_WEIGHT),
    )
    label, confidence, margin = _top_label(scores)
    if not _needs_llm(confidence, margin):
        return {"label": label, "confidence": confidence, "source": "ensemble"}

    llm_result = classify_local(text)
    if llm_result["reasoning"] == "fallback":
        return {"label": label, "confidence": confidence, "source": "ensemble_fallback"}

    llm_scores = _weighted_scores(
        (scores, NB_WEIGHT + FINBERT_WEIGHT),
        (_llm_probabilities(llm_result["label"], llm_result["confidence"]), LLM_WEIGHT),
    )
    label, confidence, _ = _top_label(llm_scores)
    return {"label": label, "confidence": confidence, "source": "ensemble_ollama"}


def _load_checked_news() -> pd.DataFrame:
    """Load only news rows that are actually referenced by retrieval."""
    if not NEWS_PATH.exists():
        raise FileNotFoundError(f"Missing processed news parquet: {NEWS_PATH}")
    if not RETRIEVAL_PATH.exists():
        raise FileNotFoundError(f"Missing retrieval parquet: {RETRIEVAL_PATH}")

    news = pd.read_parquet(NEWS_PATH)
    retrieval = pd.read_parquet(RETRIEVAL_PATH, columns=["news_id"])
    checked_ids = sorted(set(retrieval["news_id"].dropna().astype(int).tolist()))
    checked_news = news.loc[news["news_id"].isin(checked_ids)].copy()
    return checked_news.sort_values("news_id").reset_index(drop=True)


def _write_ensemble_stats(
    sentiment: pd.DataFrame,
    *,
    checked_news: int,
    total_news: int,
    retrieval_rows: int,
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
        "thresholds": {
            "ensemble_confidence": ENSEMBLE_CONFIDENCE_THRESHOLD,
            "ensemble_margin": ENSEMBLE_MARGIN_THRESHOLD,
        },
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
        scores = _weighted_scores(
            (nb_probabilities, NB_WEIGHT),
            (finbert_probabilities, FINBERT_WEIGHT),
        )
        label, confidence, margin = _top_label(scores)
        source = "ensemble"
        llm_label = ""
        llm_confidence = 0.0

        if _needs_llm(confidence, margin):
            llm_result = classify_local(str(row.headline))
            llm_label = llm_result["label"]
            llm_confidence = llm_result["confidence"]
            if llm_result["reasoning"] == "fallback":
                source = "ensemble_fallback"
            else:
                source = "ensemble_ollama"
                scores = _weighted_scores(
                    (scores, NB_WEIGHT + FINBERT_WEIGHT),
                    (_llm_probabilities(llm_label, llm_confidence), LLM_WEIGHT),
                )
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
