"""Clean raw parquet files and load the processed DuckDB layer."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from src.config import DUCKDB_PATH, PROCESSED_DIR, RAW_DIR


TRADES_PATH = RAW_DIR / "senate_trades" / "trades.parquet"
PRICES_DIR = RAW_DIR / "prices"
NEWS_DIR = RAW_DIR / "news"
TRADE_REQUIRED_COLUMNS = [
    "senator",
    "ticker",
    "transaction_date",
    "disclosure_date",
    "type",
    "amount_range_low",
    "amount_range_high",
    "asset_type",
]
PRICE_COLUMNS = ["date", "ticker", "open", "high", "low", "close", "adj_close", "volume"]
NEWS_COLUMNS = ["news_id", "ticker", "headline", "summary", "publisher", "published_at", "url", "source"]
PROCESSED_TRADES_PATH = PROCESSED_DIR / "trades.parquet"
PROCESSED_PRICES_PATH = PROCESSED_DIR / "prices.parquet"
PROCESSED_NEWS_PATH = PROCESSED_DIR / "news.parquet"


def _read_parquet_dir(directory: Path) -> pd.DataFrame:
    """Read all parquet files in a directory into one DataFrame."""
    paths = sorted(directory.glob("*.parquet"))
    if not paths:
        raise FileNotFoundError(f"No parquet files found in {directory}")
    return pd.concat((pd.read_parquet(path) for path in paths), ignore_index=True)


def clean_trades() -> pd.DataFrame:
    """Clean Senate trades and drop records that violate required constraints."""
    if not TRADES_PATH.exists():
        raise FileNotFoundError(f"Missing raw trades parquet: {TRADES_PATH}")

    trades = pd.read_parquet(TRADES_PATH)
    trades = trades[TRADE_REQUIRED_COLUMNS].copy()
    trades["ticker"] = trades["ticker"].astype("string").str.upper().str.strip()
    trades["senator"] = trades["senator"].astype("string").str.strip()
    trades["type"] = trades["type"].astype("string").str.lower().str.strip()
    trades["asset_type"] = trades["asset_type"].astype("string").str.strip()
    trades["transaction_date"] = pd.to_datetime(trades["transaction_date"], errors="coerce")
    trades["disclosure_date"] = pd.to_datetime(trades["disclosure_date"], errors="coerce")

    before_required = len(trades)
    trades = trades.dropna(subset=TRADE_REQUIRED_COLUMNS)
    dropped_required = before_required - len(trades)

    before_violations = len(trades)
    trades = trades.loc[trades["disclosure_date"] >= trades["transaction_date"]].copy()
    dropped_violations = before_violations - len(trades)

    before_dedupe = len(trades)
    trades = trades.drop_duplicates().sort_values(["disclosure_date", "transaction_date", "senator"])
    dropped_duplicates = before_dedupe - len(trades)

    print(f"Trades dropped missing required fields: {dropped_required:,}")
    print(f"Trades dropped disclosure_date < transaction_date: {dropped_violations:,}")
    print(f"Trades dropped duplicates: {dropped_duplicates:,}")
    return trades.reset_index(drop=True)


def clean_prices() -> pd.DataFrame:
    """Clean per-ticker price parquet files into one long-format table."""
    prices = _read_parquet_dir(PRICES_DIR)
    prices["ticker"] = prices["ticker"].astype("string").str.upper().str.strip()
    prices["date"] = pd.to_datetime(prices["date"], errors="coerce")
    for column in ["open", "high", "low", "close", "adj_close", "volume"]:
        prices[column] = pd.to_numeric(prices[column], errors="coerce")

    prices = prices.dropna(subset=["ticker", "date", "open", "high", "low", "close", "volume"])
    prices = prices[PRICE_COLUMNS].drop_duplicates(subset=["ticker", "date"])
    return prices.sort_values(["ticker", "date"]).reset_index(drop=True)


def clean_news() -> pd.DataFrame:
    """Clean per-ticker news parquet files into one UTC timestamped table."""
    news = _read_parquet_dir(NEWS_DIR)
    news["ticker"] = news["ticker"].astype("string").str.upper().str.strip()
    news["headline"] = news["headline"].astype("string").str.strip()
    news["summary"] = news["summary"].fillna("").astype("string")
    news["publisher"] = news["publisher"].fillna("").astype("string")
    news["url"] = news["url"].fillna("").astype("string")
    news["source"] = news["source"].fillna("yfinance").astype("string")
    news["published_at"] = pd.to_datetime(
        news["published_at"],
        utc=True,
        errors="coerce",
        format="ISO8601",
    )

    news = news.dropna(subset=["ticker", "headline", "published_at"])
    news = news.drop_duplicates(subset=["ticker", "headline", "published_at", "url"])
    news = news.sort_values(["ticker", "published_at", "headline"]).reset_index(drop=True)
    news.insert(0, "news_id", range(1, len(news) + 1))
    return news[NEWS_COLUMNS]


def _write_table(connection: duckdb.DuckDBPyConnection, name: str, frame: pd.DataFrame) -> None:
    """Replace a DuckDB table with a pandas DataFrame."""
    connection.register(f"{name}_df", frame)
    connection.execute(f"CREATE OR REPLACE TABLE {name} AS SELECT * FROM {name}_df")
    connection.unregister(f"{name}_df")


def _print_sanity(connection: duckdb.DuckDBPyConnection) -> None:
    """Print processed-layer row counts and coverage metrics."""
    counts = connection.execute(
        """
        SELECT 'trades' AS table_name, COUNT(*) AS row_count FROM trades
        UNION ALL
        SELECT 'prices', COUNT(*) FROM prices
        UNION ALL
        SELECT 'news', COUNT(*) FROM news
        UNION ALL
        SELECT 'senator_trade_universe', COUNT(*) FROM senator_trade_universe
        """
    ).fetchdf()
    print(counts.to_string(index=False))

    coverage = connection.execute(
        """
        SELECT
            (SELECT MIN(transaction_date) FROM trades) AS trade_start,
            (SELECT MAX(transaction_date) FROM trades) AS trade_end,
            (SELECT MIN(date) FROM prices) AS price_start,
            (SELECT MAX(date) FROM prices) AS price_end,
            (SELECT MIN(published_at) FROM news) AS news_start,
            (SELECT MAX(published_at) FROM news) AS news_end
        """
    ).fetchdf()
    print(coverage.to_string(index=False))

    news_before_disclosure = connection.execute(
        """
        WITH numbered_trades AS (
            SELECT
                ROW_NUMBER() OVER () AS trade_id,
                *
            FROM trades AS t
        ),
        trade_news AS (
            SELECT
                trade_id,
                EXISTS (
                    SELECT 1
                    FROM news AS n
                    WHERE n.ticker = t.ticker
                        AND n.published_at < CAST(t.disclosure_date AS TIMESTAMPTZ)
                ) AS has_pre_disclosure_news
            FROM numbered_trades AS t
        )
        SELECT
            COUNT(*) AS total_trades,
            SUM(has_pre_disclosure_news)::INTEGER AS trades_with_pre_disclosure_news,
            ROUND(100.0 * AVG(has_pre_disclosure_news::INTEGER), 2) AS pct_with_news
        FROM trade_news
        """
    ).fetchdf()
    print(news_before_disclosure.to_string(index=False))


def _write_cleaned_parquets(trades: pd.DataFrame, prices: pd.DataFrame, news: pd.DataFrame) -> None:
    """Persist cleaned tables as parquet snapshots."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    trades.to_parquet(PROCESSED_TRADES_PATH, index=False)
    prices.to_parquet(PROCESSED_PRICES_PATH, index=False)
    news.to_parquet(PROCESSED_NEWS_PATH, index=False)


def _load_tables_and_print_sanity(
    connection: duckdb.DuckDBPyConnection,
    trades: pd.DataFrame,
    prices: pd.DataFrame,
    news: pd.DataFrame,
) -> None:
    """Load cleaned frames into a DuckDB connection and print sanity metrics."""
    _write_table(connection, "trades", trades)
    _write_table(connection, "prices", prices)
    _write_table(connection, "news", news)
    connection.execute(
        """
        CREATE OR REPLACE VIEW senator_trade_universe AS
        SELECT DISTINCT t.*
        FROM trades AS t
        INNER JOIN prices AS p
            ON p.ticker = t.ticker
        """
    )
    _print_sanity(connection)


def load_processed_layer() -> None:
    """Clean raw data and write processed DuckDB tables/views."""
    trades = clean_trades()
    prices = clean_prices()
    news = clean_news()
    _write_cleaned_parquets(trades, prices, news)

    DUCKDB_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        with duckdb.connect(DUCKDB_PATH) as connection:
            _load_tables_and_print_sanity(connection, trades, prices, news)
    except duckdb.IOException as exc:
        if "being used by another process" not in str(exc):
            raise
        print(f"Could not update {DUCKDB_PATH}: {exc}")
        print("Cleaned parquet snapshots were written; running sanity checks in memory.")
        with duckdb.connect() as connection:
            _load_tables_and_print_sanity(connection, trades, prices, news)


def main() -> None:
    """Run the processed-layer transformation."""
    load_processed_layer()


if __name__ == "__main__":
    main()
