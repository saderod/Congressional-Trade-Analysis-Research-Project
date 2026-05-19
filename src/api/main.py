"""FastAPI application for serving research artifacts."""

from __future__ import annotations

import json
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from src.config import PROCESSED_DIR, PROJECT_ROOT, RESULTS_DIR


EDA_DIR = RESULTS_DIR / "eda"
FEATURES_PATH = PROCESSED_DIR / "features.parquet"
RETRIEVAL_PATH = PROCESSED_DIR / "trade_news_retrieval.parquet"
NEWS_PATH = PROCESSED_DIR / "news.parquet"
RERUN_MODULES = [
    ("Scoring related news headlines", "src.nlp.ensemble"),
    ("Rebuilding trade features", "src.features.build"),
    ("Refreshing research summaries", "src.research.eda"),
    ("Refreshing backtest results", "src.research.backtest"),
]
_RERUN_LOCK = threading.Lock()
_RERUN_STATUS: dict[str, Any] = {
    "running": False,
    "step": "Idle",
    "message": "Ready",
    "started_at": None,
    "finished_at": None,
    "success": None,
}


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


def _set_rerun_status(**updates: Any) -> None:
    """Update rerun status shared by the API endpoints."""
    with _RERUN_LOCK:
        _RERUN_STATUS.update(updates)


def _get_rerun_status() -> dict[str, Any]:
    """Return a copy of the current rerun status."""
    with _RERUN_LOCK:
        return dict(_RERUN_STATUS)


def _run_analysis_pipeline() -> None:
    """Run the local analysis refresh pipeline in the background."""
    _set_rerun_status(
        running=True,
        step=RERUN_MODULES[0][0],
        message="Starting rerun...",
        started_at=pd.Timestamp.utcnow().isoformat(),
        finished_at=None,
        success=None,
    )
    try:
        for label, module in RERUN_MODULES:
            _set_rerun_status(step=label, message=label)
            result = subprocess.run(
                [sys.executable, "-m", module],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=900,
                check=False,
            )
            if result.returncode != 0:
                output = (result.stderr or result.stdout or "No output").strip()
                raise RuntimeError(f"{label} failed: {output[-1000:]}")
        _set_rerun_status(
            running=False,
            step="Complete",
            message="Analysis refreshed successfully.",
            finished_at=pd.Timestamp.utcnow().isoformat(),
            success=True,
        )
    except Exception as exc:
        _set_rerun_status(
            running=False,
            step="Failed",
            message=str(exc),
            finished_at=pd.Timestamp.utcnow().isoformat(),
            success=False,
        )


@app.get("/health")
def health() -> dict[str, str]:
    """Return a basic health response."""
    return {"status": "ok"}


@app.post("/api/rerun")
def rerun_analysis(background_tasks: BackgroundTasks) -> dict[str, Any]:
    """Start a background refresh of analysis artifacts."""
    status = _get_rerun_status()
    if status["running"]:
        return status

    background_tasks.add_task(_run_analysis_pipeline)
    _set_rerun_status(
        running=True,
        step="Queued",
        message="Rerun queued.",
        started_at=pd.Timestamp.utcnow().isoformat(),
        finished_at=None,
        success=None,
    )
    return _get_rerun_status()


@app.get("/api/rerun/status")
def rerun_status() -> dict[str, Any]:
    """Return the current analysis rerun status."""
    return _get_rerun_status()


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
        news = pd.read_parquet(
            NEWS_PATH, columns=["news_id", "headline", "published_at", "publisher"]
        )
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
    features["top_news_published_at"] = pd.to_datetime(
        features["top_news_published_at"], errors="coerce"
    )
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
    recent["top_news_published_at"] = recent["top_news_published_at"].dt.strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    return recent.where(pd.notna(recent), None).to_dict(orient="records")
