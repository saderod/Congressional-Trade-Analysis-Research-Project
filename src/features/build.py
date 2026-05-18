"""Lookahead-safe trade and NLP feature engineering."""

from __future__ import annotations

import duckdb
import pandas as pd
from pandas.tseries.offsets import BDay

from src.config import DUCKDB_PATH, PROCESSED_DIR


FEATURES_PATH = PROCESSED_DIR / "features.parquet"
RETRIEVAL_PATH = PROCESSED_DIR / "trade_news_retrieval.parquet"
NEWS_SENTIMENT_PATH = PROCESSED_DIR / "news_sentiment.parquet"


def _signal_frame(trades: pd.DataFrame) -> pd.DataFrame:
    """Add signal/cutoff dates and trade metadata."""
    frame = trades.copy()
    frame["transaction_date"] = pd.to_datetime(frame["transaction_date"])
    frame["disclosure_date"] = pd.to_datetime(frame["disclosure_date"])
    frame["signal_date"] = frame["disclosure_date"] + BDay(1)
    frame["news_cutoff_date"] = frame["signal_date"] - BDay(1)
    frame["disclosure_lag_days"] = (
        frame["disclosure_date"] - frame["transaction_date"]
    ).dt.days
    frame["is_buy"] = frame["type"].eq("buy")
    return frame


def _price_features(prices: pd.DataFrame) -> pd.DataFrame:
    """Create per-ticker forward return features from daily prices."""
    frame = prices.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame = frame.sort_values(["ticker", "date"]).reset_index(drop=True)
    grouped = frame.groupby("ticker", group_keys=False)
    for horizon in [5, 21, 63]:
        frame[f"fwd_close_{horizon}d"] = grouped["close"].shift(-horizon)
        frame[f"fwd_return_{horizon}d"] = (
            frame[f"fwd_close_{horizon}d"] / frame["close"] - 1.0
        )

    return frame[
        [
            "ticker",
            "date",
            "open",
            "close",
            "fwd_return_5d",
            "fwd_return_21d",
            "fwd_return_63d",
        ]
    ]


def _sentiment_score_expression() -> str:
    """Return SQL for confidence-weighted signed sentiment."""
    return """
        CASE
            WHEN s.news_id IS NULL THEN NULL
            WHEN s.label = 'bullish' THEN s.confidence
            WHEN s.label = 'bearish' THEN -s.confidence
            ELSE 0
        END
    """


def build_features() -> pd.DataFrame:
    """Build and persist the feature table."""
    if not DUCKDB_PATH.exists():
        raise FileNotFoundError(f"Missing processed DuckDB database: {DUCKDB_PATH}")
    if not RETRIEVAL_PATH.exists():
        raise FileNotFoundError(f"Missing retrieval parquet: {RETRIEVAL_PATH}")
    if not NEWS_SENTIMENT_PATH.exists():
        raise FileNotFoundError(f"Missing news sentiment parquet: {NEWS_SENTIMENT_PATH}")

    with duckdb.connect(DUCKDB_PATH) as connection:
        trades = connection.execute("SELECT * FROM trades ORDER BY trade_id").fetchdf()
        prices = connection.execute("SELECT * FROM prices").fetchdf()
        news = connection.execute("SELECT * FROM news").fetchdf()

        signal_trades = _signal_frame(trades)
        price_features = _price_features(prices)
        spy_features = price_features.loc[price_features["ticker"].eq("SPY")].copy()
        spy_features = spy_features.rename(
            columns={
                "open": "spy_open",
                "close": "spy_close",
                "fwd_return_5d": "spy_fwd_return_5d",
                "fwd_return_21d": "spy_fwd_return_21d",
                "fwd_return_63d": "spy_fwd_return_63d",
            }
        )

        retrieval = pd.read_parquet(RETRIEVAL_PATH)
        sentiment = pd.read_parquet(NEWS_SENTIMENT_PATH)

        connection.register("signal_trades_df", signal_trades)
        connection.register("price_features_df", price_features)
        connection.register("spy_features_df", spy_features)
        connection.register("news_df", news)
        connection.register("retrieval_df", retrieval)
        connection.register("sentiment_df", sentiment)

        signed_sentiment = _sentiment_score_expression()
        features = connection.execute(
            f"""
            WITH trade_base AS (
                SELECT
                    trade_id,
                    senator,
                    ticker,
                    transaction_date::DATE AS transaction_date,
                    disclosure_date::DATE AS disclosure_date,
                    signal_date::DATE AS signal_date,
                    news_cutoff_date::DATE AS news_cutoff_date,
                    type,
                    amount_range_low,
                    amount_range_high,
                    disclosure_lag_days,
                    is_buy
                FROM signal_trades_df
            ),
            nlp_30d AS (
                SELECT
                    t.trade_id,
                    COUNT(s.news_id)::INTEGER AS news_count_30d,
                    AVG({signed_sentiment}) AS sentiment_score_30d
                FROM trade_base AS t
                LEFT JOIN news_df AS n
                    ON n.ticker = t.ticker
                    AND n.published_at >= CAST(t.signal_date AS TIMESTAMPTZ) - INTERVAL 30 DAY
                    -- Explicit no-lookahead guard: only news before signal_date - 1 BDay.
                    AND n.published_at < CAST(t.news_cutoff_date AS TIMESTAMPTZ)
                LEFT JOIN sentiment_df AS s
                    ON s.news_id = n.news_id
                GROUP BY t.trade_id
            ),
            top_news AS (
                SELECT
                    r.trade_id,
                    r.similarity AS top_news_similarity,
                    s.label AS top_news_sentiment
                FROM retrieval_df AS r
                INNER JOIN trade_base AS t
                    ON t.trade_id = r.trade_id
                INNER JOIN news_df AS n
                    ON n.news_id = r.news_id
                    -- Explicit no-lookahead guard for the retrieved headline.
                    AND n.published_at < CAST(t.news_cutoff_date AS TIMESTAMPTZ)
                LEFT JOIN sentiment_df AS s
                    ON s.news_id = r.news_id
                WHERE r.rank = 1
            )
            SELECT
                t.trade_id,
                t.senator,
                t.ticker,
                t.transaction_date,
                t.disclosure_date,
                t.signal_date,
                t.type,
                t.amount_range_low,
                t.amount_range_high,
                t.disclosure_lag_days,
                t.is_buy,
                p.open AS entry_price,
                p.close AS signal_close,
                p.fwd_return_5d,
                p.fwd_return_21d,
                p.fwd_return_63d,
                spy.spy_fwd_return_5d,
                spy.spy_fwd_return_21d,
                spy.spy_fwd_return_63d,
                p.fwd_return_5d - spy.spy_fwd_return_5d AS excess_return_5d,
                p.fwd_return_21d - spy.spy_fwd_return_21d AS excess_return_21d,
                p.fwd_return_63d - spy.spy_fwd_return_63d AS excess_return_63d,
                COALESCE(nlp.news_count_30d, 0) AS news_count_30d,
                nlp.sentiment_score_30d,
                top.top_news_similarity,
                top.top_news_sentiment
            FROM trade_base AS t
            LEFT JOIN price_features_df AS p
                ON p.ticker = t.ticker
                AND p.date = t.signal_date
            LEFT JOIN spy_features_df AS spy
                ON spy.date = t.signal_date
            LEFT JOIN nlp_30d AS nlp
                ON nlp.trade_id = t.trade_id
            LEFT JOIN top_news AS top
                ON top.trade_id = t.trade_id
            ORDER BY t.trade_id
            """
        ).fetchdf()

        for column in ["transaction_date", "disclosure_date", "signal_date"]:
            features[column] = pd.to_datetime(features[column]).dt.date

        FEATURES_PATH.parent.mkdir(parents=True, exist_ok=True)
        features.to_parquet(FEATURES_PATH, index=False)
        connection.register("features_df", features)
        connection.execute(
            """
            CREATE OR REPLACE TABLE features (
                trade_id INTEGER PRIMARY KEY,
                senator VARCHAR,
                ticker VARCHAR,
                transaction_date DATE,
                disclosure_date DATE,
                signal_date DATE,
                type VARCHAR,
                amount_range_low BIGINT,
                amount_range_high BIGINT,
                disclosure_lag_days BIGINT,
                is_buy BOOLEAN,
                entry_price DOUBLE,
                signal_close DOUBLE,
                fwd_return_5d DOUBLE,
                fwd_return_21d DOUBLE,
                fwd_return_63d DOUBLE,
                spy_fwd_return_5d DOUBLE,
                spy_fwd_return_21d DOUBLE,
                spy_fwd_return_63d DOUBLE,
                excess_return_5d DOUBLE,
                excess_return_21d DOUBLE,
                excess_return_63d DOUBLE,
                news_count_30d INTEGER,
                sentiment_score_30d DOUBLE,
                top_news_similarity DOUBLE,
                top_news_sentiment VARCHAR
            )
            """
        )
        connection.execute(
            """
            INSERT INTO features
            SELECT
                trade_id::INTEGER,
                senator,
                ticker,
                transaction_date::DATE,
                disclosure_date::DATE,
                signal_date::DATE,
                type,
                amount_range_low,
                amount_range_high,
                disclosure_lag_days,
                is_buy,
                entry_price,
                signal_close,
                fwd_return_5d,
                fwd_return_21d,
                fwd_return_63d,
                spy_fwd_return_5d,
                spy_fwd_return_21d,
                spy_fwd_return_63d,
                excess_return_5d,
                excess_return_21d,
                excess_return_63d,
                news_count_30d,
                sentiment_score_30d,
                top_news_similarity,
                top_news_sentiment
            FROM features_df
            ORDER BY trade_id
            """
        )
        connection.unregister("features_df")

    return features


def _print_summary(features: pd.DataFrame) -> None:
    """Print Phase 6 coverage and summary statistics."""
    total = len(features)
    with_top_news = int(features["top_news_similarity"].notna().sum())
    with_30d_news = int(features["news_count_30d"].fillna(0).gt(0).sum())
    with_entry = int(features["entry_price"].notna().sum())
    print(f"Feature rows: {total:,} -> {FEATURES_PATH}")
    print(f"Entry price coverage: {with_entry:,}/{total:,} ({with_entry / total:.2%})")
    print(f"Trades with top retrieved NLP feature: {with_top_news:,}/{total:,} ({with_top_news / total:.2%})")
    print(f"Trades with 30d sentiment news: {with_30d_news:,}/{total:,} ({with_30d_news / total:.2%})")
    summary_columns = [
        "disclosure_lag_days",
        "news_count_30d",
        "sentiment_score_30d",
        "top_news_similarity",
        "fwd_return_5d",
        "fwd_return_21d",
        "fwd_return_63d",
        "excess_return_5d",
        "excess_return_21d",
        "excess_return_63d",
    ]
    print(features[summary_columns].describe().to_string())


def main() -> None:
    """Run feature engineering."""
    features = build_features()
    _print_summary(features)


if __name__ == "__main__":
    main()
