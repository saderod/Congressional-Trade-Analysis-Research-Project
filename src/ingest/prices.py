"""Download daily OHLCV data for the Senate trade ticker universe."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import yfinance as yf

from src.config import RAW_DIR


TRADES_PATH = RAW_DIR / "senate_trades" / "trades.parquet"
PRICES_DIR = RAW_DIR / "prices"
BATCH_SIZE = 50


def _batched(items: list[str], batch_size: int) -> list[list[str]]:
    """Split a list into fixed-size batches."""
    return [items[index : index + batch_size] for index in range(0, len(items), batch_size)]


def _ticker_output_path(ticker: str) -> Path:
    """Return the parquet path for a ticker's downloaded price history."""
    return PRICES_DIR / f"{ticker}.parquet"


def _normalize_price_frame(frame: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """Convert a yfinance ticker frame to a predictable parquet schema."""
    output = frame.dropna(how="all").reset_index()
    output.columns = [str(column).lower().replace(" ", "_") for column in output.columns]
    if "date" not in output.columns and "index" in output.columns:
        output = output.rename(columns={"index": "date"})

    output.insert(0, "ticker", ticker)
    wanted = ["ticker", "date", "open", "high", "low", "close", "adj_close", "volume"]
    available = [column for column in wanted if column in output.columns]
    return output[available]


def _extract_ticker_frame(download: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """Pull one ticker out of a yfinance batch response."""
    if download.empty:
        return pd.DataFrame()

    if isinstance(download.columns, pd.MultiIndex):
        top_level = download.columns.get_level_values(0)
        if ticker not in top_level:
            return pd.DataFrame()
        return download[ticker]

    return download


def fetch_prices(tickers: list[str], start: str, end: str) -> tuple[list[str], list[str]]:
    """Download daily OHLCV in batches and save one parquet file per ticker."""
    PRICES_DIR.mkdir(parents=True, exist_ok=True)

    universe = sorted({ticker.strip().upper() for ticker in tickers if ticker and ticker.strip()})
    if "SPY" not in universe:
        universe.append("SPY")
        universe.sort()

    successful: list[str] = []
    failed: list[str] = []

    for batch_number, batch in enumerate(_batched(universe, BATCH_SIZE), start=1):
        print(f"Downloading batch {batch_number}: {len(batch)} tickers")
        try:
            download = yf.download(
                tickers=batch,
                start=start,
                end=end,
                group_by="ticker",
                auto_adjust=False,
                progress=False,
                threads=True,
            )
        except Exception as exc:
            print(f"Batch failed: {exc}")
            failed.extend(batch)
            continue

        for ticker in batch:
            ticker_frame = _extract_ticker_frame(download, ticker)
            if ticker_frame.empty or ticker_frame.dropna(how="all").empty:
                print(f"No price data for {ticker}")
                failed.append(ticker)
                continue

            normalized = _normalize_price_frame(ticker_frame, ticker)
            normalized.to_parquet(_ticker_output_path(ticker), index=False)
            successful.append(ticker)

    print(f"Successful tickers: {len(successful):,}")
    print(f"Failed tickers: {len(failed):,}")
    if failed:
        print(f"Failed ticker list: {', '.join(failed)}")

    return successful, failed


def load_ticker_universe() -> list[str]:
    """Load distinct tickers from Phase 2a's Senate trade parquet."""
    if not TRADES_PATH.exists():
        raise FileNotFoundError(f"Missing Phase 2a trades parquet: {TRADES_PATH}")

    trades = pd.read_parquet(TRADES_PATH, columns=["ticker"])
    return trades["ticker"].dropna().astype(str).tolist()


def main() -> None:
    """Run daily price ingestion from the command line."""
    tickers = load_ticker_universe()
    start = "2012-01-01"
    # yfinance treats end as exclusive; add one day for today's available history.
    end = (date.today() + timedelta(days=1)).isoformat()
    fetch_prices(tickers, start=start, end=end)


if __name__ == "__main__":
    main()
