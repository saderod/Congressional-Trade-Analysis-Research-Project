"""FinBERT sentiment classification entry points."""

from __future__ import annotations

from typing import TypedDict

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from src.config import FINBERT_MODEL


BATCH_SIZE = 32
LABEL_MAP = {"positive": "bullish", "negative": "bearish", "neutral": "neutral"}
LABELS = ["bearish", "neutral", "bullish"]

_TOKENIZER: AutoTokenizer | None = None
_MODEL: AutoModelForSequenceClassification | None = None


class Classification(TypedDict):
    """Sentiment classification output."""

    label: str
    confidence: float


def _load_model() -> tuple[AutoTokenizer, AutoModelForSequenceClassification]:
    """Load FinBERT once per process."""
    global _MODEL, _TOKENIZER
    if _TOKENIZER is None:
        _TOKENIZER = AutoTokenizer.from_pretrained(FINBERT_MODEL)
    if _MODEL is None:
        _MODEL = AutoModelForSequenceClassification.from_pretrained(FINBERT_MODEL)
        _MODEL.eval()
    return _TOKENIZER, _MODEL


def _label_from_model(model: AutoModelForSequenceClassification, label_index: int) -> str:
    """Normalize a FinBERT label id into the project label set."""
    raw_label = model.config.id2label.get(label_index, str(label_index)).lower()
    return LABEL_MAP.get(raw_label, raw_label)


def classify_finbert(texts: list[str]) -> list[Classification]:
    """Classify text sentiment with ProsusAI/finbert."""
    if not texts:
        return []

    tokenizer, model = _load_model()
    results: list[Classification] = []
    with torch.inference_mode():
        for start in range(0, len(texts), BATCH_SIZE):
            batch = texts[start : start + BATCH_SIZE]
            inputs = tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=128,
                return_tensors="pt",
            )
            logits = model(**inputs).logits
            probabilities = torch.softmax(logits, dim=-1)
            confidences, indexes = probabilities.max(dim=-1)
            for confidence, index in zip(confidences.tolist(), indexes.tolist(), strict=True):
                results.append(
                    {
                        "label": _label_from_model(model, int(index)),
                        "confidence": float(confidence),
                    }
                )
    return results


def classify_finbert_proba(texts: list[str]) -> list[dict[str, float]]:
    """Return full FinBERT class probabilities for weighted ensembling."""
    if not texts:
        return []

    tokenizer, model = _load_model()
    results: list[dict[str, float]] = []
    with torch.inference_mode():
        for start in range(0, len(texts), BATCH_SIZE):
            batch = texts[start : start + BATCH_SIZE]
            inputs = tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=128,
                return_tensors="pt",
            )
            probabilities = torch.softmax(model(**inputs).logits, dim=-1)
            for probability_row in probabilities.tolist():
                row = dict.fromkeys(LABELS, 0.0)
                for index, probability in enumerate(probability_row):
                    row[_label_from_model(model, index)] = float(probability)
                results.append(row)
    return results
