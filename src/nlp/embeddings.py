"""Sentence-transformer embeddings and lookahead-safe news retrieval."""

from __future__ import annotations

import hashlib
from typing import Any

import duckdb
import numpy as np
import pandas as pd
from pandas.tseries.offsets import BDay
from sentence_transformers import SentenceTransformer

from src.config import DUCKDB_PATH, EMBEDDINGS_DIR, EMBED_MODEL, PROCESSED_DIR


NEWS_EMBEDDINGS_PATH = PROCESSED_DIR / "news_embeddings.parquet"
TRADE_EMBEDDINGS_PATH = PROCESSED_DIR / "trade_context_embeddings.parquet"
RETRIEVAL_PATH = PROCESSED_DIR / "trade_news_retrieval.parquet"
RETRIEVAL_COLUMNS = ["trade_id", "news_id", "ticker", "similarity", "rank"]

_MODEL: SentenceTransformer | None = None


def _model() -> SentenceTransformer:
    """Load the configured sentence-transformer model once per process."""
    global _MODEL
    if _MODEL is None:
        _MODEL = SentenceTransformer(EMBED_MODEL)
    return _MODEL


def _cache_key(texts: list[str]) -> str:
    """Build a stable cache key for a model/text batch."""
    digest = hashlib.sha256()
    digest.update(EMBED_MODEL.encode("utf-8"))
    for text in texts:
        digest.update(b"\0")
        digest.update(text.encode("utf-8", errors="ignore"))
    return digest.hexdigest()


def embed_texts(texts: list[str]) -> np.ndarray:
    """Embed texts with sentence-transformers, caching exact batches to disk."""
    EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)
    normalized_texts = [text if text else "" for text in texts]
    cache_path = EMBEDDINGS_DIR / f"{_cache_key(normalized_texts)}.npy"
    if cache_path.exists():
        return np.load(cache_path)

    embeddings = _model().encode(
        normalized_texts,
        batch_size=64,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=True,
    )
    np.save(cache_path, embeddings)
    return embeddings


def _embedding_frame(ids: pd.Series, texts: list[str], id_column: str) -> pd.DataFrame:
    """Create a parquet-friendly DataFrame of text embeddings."""
    embeddings = embed_texts(texts)
    return pd.DataFrame(
        {
            id_column: ids.to_list(),
            "text": texts,
            "embedding": [vector.astype(float).tolist() for vector in embeddings],
        }
    )


def _trade_context(row: pd.Series) -> str:
    """Build the natural-language context string for a trade."""
    disclosure_date = pd.Timestamp(row["disclosure_date"]).date().isoformat()
    verb = "buys" if row["type"] == "buy" else "sells"
    return f"{row['senator']} {verb} {row['ticker']} disclosed {disclosure_date}"


def _load_processed_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load processed trades and news from DuckDB."""
    if not DUCKDB_PATH.exists():
        raise FileNotFoundError(f"Missing processed DuckDB database: {DUCKDB_PATH}")

    try:
        with duckdb.connect(DUCKDB_PATH, read_only=True) as connection:
            trades = connection.execute(
                """
                SELECT
                    ROW_NUMBER() OVER (ORDER BY disclosure_date, transaction_date, senator, ticker) AS trade_id,
                    *
                FROM trades
                """
            ).fetchdf()
            news = connection.execute("SELECT * FROM news ORDER BY news_id").fetchdf()
    except duckdb.IOException as exc:
        print(f"Could not read DuckDB directly ({exc}); falling back to cleaned raw parquet.")
        from src.clean.transform import clean_news, clean_trades

        trades = clean_trades().reset_index(drop=True)
        trades.insert(0, "trade_id", range(1, len(trades) + 1))
        news = clean_news()
    return trades, news


def _prepare_trades(trades: pd.DataFrame) -> pd.DataFrame:
    """Add signal dates and context strings to processed trades."""
    trades = trades.copy()
    trades["disclosure_date"] = pd.to_datetime(trades["disclosure_date"], errors="coerce")
    trades["signal_date"] = trades["disclosure_date"] + BDay(1)
    trades["context"] = trades.apply(_trade_context, axis=1)
    return trades


def _prepare_news(news: pd.DataFrame) -> pd.DataFrame:
    """Normalize processed news timestamps and text fields."""
    news = news.copy()
    news["published_at"] = pd.to_datetime(
        news["published_at"],
        utc=True,
        errors="coerce",
        format="ISO8601",
    )
    news["headline"] = news["headline"].fillna("").astype(str)
    news["summary"] = news["summary"].fillna("").astype(str)
    news["text"] = (news["headline"] + ". " + news["summary"]).str.strip()
    return news


def _cutoff_from_trade(trade_row: pd.Series | dict[str, Any]) -> pd.Timestamp:
    """Return the strict news cutoff: published before signal_date minus one business day."""
    signal_date = pd.Timestamp(trade_row["signal_date"])
    cutoff = signal_date - BDay(1)
    return pd.Timestamp(cutoff).tz_localize("UTC")


def find_similar_news(trade_row: pd.Series, news_df: pd.DataFrame, k: int = 5) -> pd.DataFrame:
    """Find top-k same-ticker news published before the lookahead-safe cutoff."""
    cutoff = _cutoff_from_trade(trade_row)
    candidates = news_df.loc[
        (news_df["ticker"] == trade_row["ticker"]) & (news_df["published_at"] < cutoff)
    ].copy()
    if candidates.empty:
        return pd.DataFrame(columns=["news_id", "similarity"])

    trade_embedding = embed_texts([_trade_context(trade_row)])[0]
    news_embeddings = embed_texts(candidates["text"].tolist())
    similarities = news_embeddings @ trade_embedding
    candidates["similarity"] = similarities
    return candidates.sort_values("similarity", ascending=False).head(k)[["news_id", "similarity"]]


def _build_retrieval(trades: pd.DataFrame, news: pd.DataFrame, k: int = 5) -> tuple[pd.DataFrame, float]:
    """Build top-k news retrieval rows for each trade."""
    retrieval_rows: list[dict[str, Any]] = []
    candidate_counts: list[int] = []

    for trade in trades.itertuples(index=False):
        trade_row = pd.Series(trade._asdict())
        cutoff = _cutoff_from_trade(trade_row)
        candidates = news.loc[
            (news["ticker"] == trade_row["ticker"]) & (news["published_at"] < cutoff)
        ].copy()
        candidate_counts.append(len(candidates))
        if candidates.empty:
            continue

        trade_embedding = embed_texts([trade_row["context"]])[0]
        news_embeddings = embed_texts(candidates["text"].tolist())
        candidates["similarity"] = news_embeddings @ trade_embedding
        top = candidates.sort_values("similarity", ascending=False).head(k)
        for rank, row in enumerate(top.itertuples(index=False), start=1):
            retrieval_rows.append(
                {
                    "trade_id": int(trade_row["trade_id"]),
                    "news_id": int(row.news_id),
                    "ticker": trade_row["ticker"],
                    "similarity": float(row.similarity),
                    "rank": rank,
                }
            )

    retrieval = pd.DataFrame(retrieval_rows, columns=RETRIEVAL_COLUMNS)
    avg_candidates = float(np.mean(candidate_counts)) if candidate_counts else 0.0
    return retrieval, avg_candidates


def run_embeddings_pipeline() -> None:
    """Build embeddings and lookahead-safe trade-news retrieval artifacts."""
    trades, news = _load_processed_data()
    trades = _prepare_trades(trades)
    news = _prepare_news(news)

    news_embedding_frame = _embedding_frame(news["news_id"], news["text"].tolist(), "news_id")
    trade_embedding_frame = _embedding_frame(trades["trade_id"], trades["context"].tolist(), "trade_id")
    news_embedding_frame.to_parquet(NEWS_EMBEDDINGS_PATH, index=False)
    trade_embedding_frame.to_parquet(TRADE_EMBEDDINGS_PATH, index=False)

    retrieval, avg_candidates = _build_retrieval(trades, news, k=5)
    retrieval.to_parquet(RETRIEVAL_PATH, index=False)

    top1 = retrieval.loc[retrieval["rank"] == 1, "similarity"]
    avg_top1 = float(top1.mean()) if not top1.empty else float("nan")
    print(f"News embeddings: {len(news_embedding_frame):,} -> {NEWS_EMBEDDINGS_PATH}")
    print(f"Trade context embeddings: {len(trade_embedding_frame):,} -> {TRADE_EMBEDDINGS_PATH}")
    print(f"Retrieval rows: {len(retrieval):,} -> {RETRIEVAL_PATH}")
    print(f"Avg pre-disclosure news headlines per trade: {avg_candidates:.2f}")
    print(f"Avg top-1 similarity: {avg_top1 if not np.isnan(avg_top1) else 'n/a'}")


def main() -> None:
    """Run the embeddings and cosine retrieval pipeline."""
    run_embeddings_pipeline()


if __name__ == "__main__":
    main()
