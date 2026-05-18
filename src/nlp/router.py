"""Backward-compatible entry points for the weighted sentiment ensemble."""

from src.nlp.ensemble import classify_headline, classify_news, main, run_classification_pipeline


__all__ = ["classify_headline", "classify_news", "main", "run_classification_pipeline"]
