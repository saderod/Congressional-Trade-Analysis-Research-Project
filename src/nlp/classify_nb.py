"""Naive Bayes sentiment classification entry points."""

from __future__ import annotations

import zipfile
from typing import TypedDict

import joblib
from huggingface_hub import hf_hub_download
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

from src.config import PROCESSED_DIR


NB_MODEL_PATH = PROCESSED_DIR / "nb_model.joblib"
PHRASEBANK_REPO = "takala/financial_phrasebank"
PHRASEBANK_ZIP = "data/FinancialPhraseBank-v1.0.zip"
PHRASEBANK_FILE = "Sentences_75Agree.txt"
LABEL_MAP = {"positive": "bullish", "negative": "bearish", "neutral": "neutral"}
LABELS = ["bearish", "neutral", "bullish"]


class Classification(TypedDict):
    """Sentiment classification output."""

    label: str
    confidence: float


def _load_phrasebank() -> tuple[list[str], list[str]]:
    """Download and parse Financial PhraseBank training rows."""
    archive_path = hf_hub_download(
        repo_id=PHRASEBANK_REPO,
        filename=PHRASEBANK_ZIP,
        repo_type="dataset",
    )
    with zipfile.ZipFile(archive_path) as archive:
        member = next(name for name in archive.namelist() if name.endswith(PHRASEBANK_FILE))
        raw_lines = archive.read(member).decode("latin-1").splitlines()

    texts: list[str] = []
    labels: list[str] = []
    for line in raw_lines:
        if "@" not in line:
            continue
        text, label = line.rsplit("@", maxsplit=1)
        normalized_label = LABEL_MAP.get(label.strip().lower())
        if text.strip() and normalized_label:
            texts.append(text.strip())
            labels.append(normalized_label)

    if not texts:
        raise RuntimeError("Financial PhraseBank training set parsed zero rows")
    return texts, labels


def train_nb(force: bool = False) -> Pipeline:
    """Train and persist the TF-IDF + MultinomialNB baseline model."""
    if NB_MODEL_PATH.exists() and not force:
        return joblib.load(NB_MODEL_PATH)

    texts, labels = _load_phrasebank()
    model = Pipeline(
        steps=[
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_df=0.95)),
            ("nb", MultinomialNB(alpha=0.5)),
        ]
    )
    model.fit(texts, labels)

    NB_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, NB_MODEL_PATH)
    return model


def _model() -> Pipeline:
    """Load the trained NB model, training it on first use."""
    return train_nb(force=False)


def classify_nb(texts: list[str]) -> list[Classification]:
    """Classify text sentiment with the persisted Naive Bayes model."""
    if not texts:
        return []

    model = _model()
    probabilities = model.predict_proba(texts)
    labels = list(model.classes_)
    results: list[Classification] = []
    for row in probabilities:
        best_index = int(row.argmax())
        results.append(
            {
                "label": str(labels[best_index]),
                "confidence": float(row[best_index]),
            }
        )
    return results


def classify_nb_proba(texts: list[str]) -> list[dict[str, float]]:
    """Return full NB class probabilities for weighted ensembling."""
    if not texts:
        return []

    model = _model()
    probabilities = model.predict_proba(texts)
    classes = [str(label) for label in model.classes_]
    rows: list[dict[str, float]] = []
    for probability_row in probabilities:
        row = dict.fromkeys(LABELS, 0.0)
        for label, probability in zip(classes, probability_row, strict=True):
            row[label] = float(probability)
        rows.append(row)
    return rows


def main() -> None:
    """Train the NB model from the command line."""
    texts, _ = _load_phrasebank()
    train_nb(force=True)
    print(f"Trained NB model on {len(texts):,} Financial PhraseBank rows -> {NB_MODEL_PATH}")


if __name__ == "__main__":
    main()
