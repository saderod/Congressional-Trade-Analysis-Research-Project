"""Routing logic for the three-tier sentiment cascade."""

from __future__ import annotations

import json
from collections import Counter
from typing import TypedDict

import pandas as pd

from src.config import PROCESSED_DIR, RESULTS_DIR
from src.nlp.classify_finbert import classify_finbert
from src.nlp.classify_nb import classify_nb, train_nb
from src.nlp.llm_local import classify_local


NB_THRESHOLD = 0.85
FINBERT_THRESHOLD = 0.80
NEWS_PATH = PROCESSED_DIR / "news.parquet"
NEWS_SENTIMENT_PATH = PROCESSED_DIR / "news_sentiment.parquet"
ROUTING_STATS_PATH = RESULTS_DIR / "nlp_routing.json"
SENTIMENT_COLUMNS = ["news_id", "headline", "label", "confidence", "source"]


class RoutedClassification(TypedDict):
    """Sentiment output with cascade source metadata."""

    label: str
    confidence: float
    source: str


def _with_source(result: dict[str, object], source: str) -> RoutedClassification:
    """Attach routing source to a classifier result."""
    return {
        "label": str(result["label"]),
        "confidence": float(result["confidence"]),
        "source": source,
    }


def classify_headline(text: str) -> RoutedClassification:
    """Classify one headline through NB -> FinBERT -> Ollama."""
    nb_result = classify_nb([text])[0]
    if nb_result["confidence"] > NB_THRESHOLD:
        return _with_source(nb_result, "nb")

    finbert_result = classify_finbert([text])[0]
    if finbert_result["confidence"] > FINBERT_THRESHOLD:
        return _with_source(finbert_result, "finbert")

    llm_result = classify_local(text)
    source = "fallback_neutral" if llm_result["reasoning"] == "fallback" else "ollama"
    return _with_source(llm_result, source)


def _load_news() -> pd.DataFrame:
    """Load processed news for sentiment classification."""
    if not NEWS_PATH.exists():
        raise FileNotFoundError(f"Missing processed news parquet: {NEWS_PATH}")
    news = pd.read_parquet(NEWS_PATH)
    return news.sort_values("news_id").reset_index(drop=True)


def _write_routing_stats(sentiment: pd.DataFrame) -> dict[str, object]:
    """Persist tier usage counts and percentages."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    counts = Counter(sentiment["source"].astype(str))
    total = int(sum(counts.values()))
    stats = {
        "total": total,
        "counts": dict(sorted(counts.items())),
        "percentages": {
            source: round((count / total) * 100, 2) if total else 0.0
            for source, count in sorted(counts.items())
        },
    }
    ROUTING_STATS_PATH.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    return stats


def classify_news(news: pd.DataFrame) -> pd.DataFrame:
    """Apply the three-tier cascade to a processed news table."""
    headlines = news["headline"].fillna("").astype(str).tolist()
    rows: list[RoutedClassification] = [
        {"label": "", "confidence": 0.0, "source": ""} for _ in headlines
    ]

    nb_results = classify_nb(headlines)
    finbert_indexes: list[int] = []
    for index, result in enumerate(nb_results):
        if result["confidence"] > NB_THRESHOLD:
            rows[index] = _with_source(result, "nb")
        else:
            finbert_indexes.append(index)

    if finbert_indexes:
        finbert_texts = [headlines[index] for index in finbert_indexes]
        finbert_results = classify_finbert(finbert_texts)
        ollama_indexes: list[int] = []
        for index, result in zip(finbert_indexes, finbert_results, strict=True):
            if result["confidence"] > FINBERT_THRESHOLD:
                rows[index] = _with_source(result, "finbert")
            else:
                ollama_indexes.append(index)

        for index in ollama_indexes:
            result = classify_local(headlines[index])
            source = "fallback_neutral" if result["reasoning"] == "fallback" else "ollama"
            rows[index] = _with_source(result, source)

    sentiment = pd.DataFrame(rows)
    output = pd.concat(
        [
            news[["news_id", "headline"]].reset_index(drop=True),
            sentiment[["label", "confidence", "source"]],
        ],
        axis=1,
    )
    return output[SENTIMENT_COLUMNS]


def run_classification_pipeline() -> pd.DataFrame:
    """Train NB if needed, classify all processed news, and persist outputs."""
    train_nb(force=False)
    news = _load_news()
    sentiment = classify_news(news)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    sentiment.to_parquet(NEWS_SENTIMENT_PATH, index=False)
    stats = _write_routing_stats(sentiment)

    print(f"News sentiment rows: {len(sentiment):,} -> {NEWS_SENTIMENT_PATH}")
    print(f"Routing stats: {json.dumps(stats, indent=2)}")
    print("Sample classifications:")
    print(sentiment.head(10).to_string(index=False))
    return sentiment


def main() -> None:
    """Run the sentiment cascade from the command line."""
    run_classification_pipeline()


if __name__ == "__main__":
    main()
