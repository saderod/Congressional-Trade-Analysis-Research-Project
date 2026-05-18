"""Local Ollama-backed sentiment classification entry points."""

from __future__ import annotations

import json
from typing import Any, TypedDict

import ollama

from src.config import OLLAMA_MODEL


VALID_LABELS = {"bullish", "bearish", "neutral"}
_OLLAMA_AVAILABLE: bool | None = None


class LLMClassification(TypedDict):
    """Local LLM sentiment classification output."""

    label: str
    confidence: float
    reasoning: str


def _fallback(reason: str) -> LLMClassification:
    """Return a deterministic neutral fallback."""
    return {"label": "neutral", "confidence": 0.5, "reasoning": reason}


def _is_ollama_available() -> bool:
    """Check Ollama availability once per process."""
    global _OLLAMA_AVAILABLE
    if _OLLAMA_AVAILABLE is not None:
        return _OLLAMA_AVAILABLE

    try:
        ollama.list()
        _OLLAMA_AVAILABLE = True
    except Exception as exc:
        print(f"Ollama unavailable; using neutral fallback for LLM-routed items: {exc}")
        _OLLAMA_AVAILABLE = False
    return _OLLAMA_AVAILABLE


def _parse_response(content: str) -> LLMClassification:
    """Parse and validate the model's JSON response."""
    data: Any = json.loads(content)
    if not isinstance(data, dict):
        raise ValueError("Ollama response was not a JSON object")

    label = str(data.get("label", "")).lower().strip()
    if label not in VALID_LABELS:
        raise ValueError(f"Invalid sentiment label: {label}")

    confidence = float(data.get("confidence", 0.5))
    confidence = max(0.0, min(1.0, confidence))
    reasoning = str(data.get("reasoning", "")).strip() or "No reasoning returned."
    return {"label": label, "confidence": confidence, "reasoning": reasoning}


def classify_local(text: str) -> LLMClassification:
    """Classify one headline with a local Ollama model."""
    if not _is_ollama_available():
        return _fallback("fallback")

    prompt = (
        "Classify the finance headline as bullish, bearish, or neutral for the company. "
        "Return only JSON with keys label, confidence, and reasoning. "
        "Confidence must be a number from 0 to 1. Reasoning must be one short sentence.\n\n"
        f"Headline: {text}"
    )
    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0},
            format="json",
        )
        message = response.get("message", {}) if isinstance(response, dict) else {}
        content = message.get("content", "")
        return _parse_response(content)
    except Exception as exc:
        print(f"Ollama classification fallback: {exc}")
        return _fallback("fallback")
