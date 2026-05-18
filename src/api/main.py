"""FastAPI application for serving research artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from src.config import PROCESSED_DIR, RESULTS_DIR


EDA_DIR = RESULTS_DIR / "eda"
FEATURES_PATH = PROCESSED_DIR / "features.parquet"
RETRIEVAL_PATH = PROCESSED_DIR / "trade_news_retrieval.parquet"
NEWS_PATH = PROCESSED_DIR / "news.parquet"


app = FastAPI(title="congressional-alpha")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _read_json(path: Path) -> Any:
    """Read a generated JSON artifact or return a 404."""
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Missing artifact: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _read_features() -> pd.DataFrame:
    """Read feature parquet or return a 404."""
    if not FEATURES_PATH.exists():
        raise HTTPException(status_code=404, detail=f"Missing artifact: {FEATURES_PATH}")
    return pd.read_parquet(FEATURES_PATH)


@app.get("/health")
def health() -> dict[str, str]:
    """Return a basic health response."""
    return {"status": "ok"}


@app.get("/api/overview")
def overview() -> Any:
    """Return EDA overview stats."""
    return _read_json(EDA_DIR / "overview.json")


@app.get("/api/senators")
def senators() -> Any:
    """Return senator-level EDA stats."""
    return _read_json(EDA_DIR / "by_senator.json")


@app.get("/api/sentiment-buckets")
def sentiment_buckets() -> Any:
    """Return sentiment-bucket EDA stats."""
    return _read_json(EDA_DIR / "by_sentiment.json")


@app.get("/api/nlp-routing")
def nlp_routing() -> Any:
    """Return NLP ensemble usage stats."""
    return _read_json(RESULTS_DIR / "nlp_routing.json")


@app.get("/api/backtest")
def backtest() -> Any:
    """Return backtest results."""
    return _read_json(RESULTS_DIR / "backtest.json")


@app.get("/api/trades/recent")
def recent_trades(n: int = Query(default=50, ge=1, le=500)) -> list[dict[str, Any]]:
    """Return recent trades with engineered NLP features."""
    features = _read_features().copy()
    if RETRIEVAL_PATH.exists() and NEWS_PATH.exists():
        retrieval = pd.read_parquet(RETRIEVAL_PATH)
        news = pd.read_parquet(NEWS_PATH, columns=["news_id", "headline", "published_at", "publisher"])
        top_news = (
            retrieval.loc[retrieval["rank"] == 1, ["trade_id", "news_id"]]
            .merge(news, on="news_id", how="left")
            .rename(
                columns={
                    "headline": "top_news_headline",
                    "published_at": "top_news_published_at",
                    "publisher": "top_news_publisher",
                }
            )
        )
        features = features.merge(top_news, on="trade_id", how="left")
    else:
        features["top_news_headline"] = None
        features["top_news_published_at"] = None
        features["top_news_publisher"] = None

    features["disclosure_date"] = pd.to_datetime(features["disclosure_date"], errors="coerce")
    features["signal_date"] = pd.to_datetime(features["signal_date"], errors="coerce")
    features["top_news_published_at"] = pd.to_datetime(features["top_news_published_at"], errors="coerce")
    columns = [
        "trade_id",
        "senator",
        "ticker",
        "type",
        "disclosure_date",
        "signal_date",
        "entry_price",
        "fwd_return_21d",
        "excess_return_21d",
        "news_count_30d",
        "sentiment_score_30d",
        "top_news_similarity",
        "top_news_sentiment",
        "top_news_headline",
        "top_news_published_at",
        "top_news_publisher",
    ]
    recent = features.sort_values(["disclosure_date", "trade_id"], ascending=[False, False]).head(n)
    recent = recent[columns]
    for column in ["disclosure_date", "signal_date"]:
        recent[column] = recent[column].dt.date.astype(str)
    recent["top_news_published_at"] = recent["top_news_published_at"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return recent.where(pd.notna(recent), None).to_dict(orient="records")
