"""Tests for scoped ensemble classification."""

from __future__ import annotations

import pandas as pd

from src.nlp import ensemble


def test_load_checked_news_uses_only_retrieved_news_ids(tmp_path, monkeypatch) -> None:
    """The ensemble must classify only headlines referenced by retrieval."""
    news_path = tmp_path / "news.parquet"
    retrieval_path = tmp_path / "trade_news_retrieval.parquet"
    monkeypatch.setattr(ensemble, "NEWS_PATH", news_path)
    monkeypatch.setattr(ensemble, "RETRIEVAL_PATH", retrieval_path)

    pd.DataFrame(
        {
            "news_id": [1, 2, 3, 4],
            "headline": ["unused", "checked b", "checked c", "unused d"],
            "ticker": ["A", "B", "C", "D"],
        }
    ).to_parquet(news_path, index=False)
    pd.DataFrame({"news_id": [3, 2, 3]}).to_parquet(retrieval_path, index=False)

    checked_news = ensemble._load_checked_news()

    assert checked_news["news_id"].tolist() == [2, 3]
    assert checked_news["headline"].tolist() == ["checked b", "checked c"]
