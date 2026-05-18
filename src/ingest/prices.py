"""Download daily OHLCV data for the Senate trade ticker universe."""

from __future__ import annotations

import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import yfinance as yf

from src.config import RAW_DIR


TRADES_PATH = RAW_DIR / "senate_trades" / "trades.parquet"
PRICES_DIR = RAW_DIR / "prices"
BATCH_SIZE = 25
RETRY_BATCH_SIZE = 5
RETRY_SLEEP_SECONDS = 1.0
FRESH_PRICE_GRACE_DAYS = 7
YAHOO_TICKER_ALIASES = {
    "BRK.B": "BRK-B",
    "BRKB": "BRK-B",
    "DISCA": "WBD",
    "DISCK": "WBD",
    "FB": "META",
    "RDS-A": "SHEL",
    "RDS-B": "SHEL",
    "RDSA": "SHEL",
    "RDSA.AS": "SHELL.AS",
    "SQ": "XYZ",
    "UA-C": "UAA",
}


def _batched(items: list[str], batch_size: int) -> list[list[str]]:
    """Split a list into fixed-size batches."""
    return [items[index : index + batch_size] for index in range(0, len(items), batch_size)]


def _ticker_output_path(ticker: str) -> Path:
    """Return the parquet path for a ticker's downloaded price history."""
    return PRICES_DIR / f"{ticker}.parquet"


def _has_saved_price_file(ticker: str) -> bool:
    """Return True when a ticker already has a non-empty saved price file."""
    return _saved_price_max_date(ticker) is not None


def _saved_price_max_date(ticker: str) -> pd.Timestamp | None:
    """Return the latest date saved for a ticker, if readable."""
    path = _ticker_output_path(ticker)
    if not path.exists() or path.stat().st_size == 0:
        return None

    try:
        dates = pd.read_parquet(path, columns=["date"])["date"]
    except (OSError, ValueError, KeyError, FileNotFoundError):
        return None

    if dates.empty:
        return None
    return pd.to_datetime(dates, errors="coerce").max()


def _has_fresh_saved_price_file(ticker: str, end: str) -> bool:
    """Return True when existing prices are close to the requested end date."""
    max_date = _saved_price_max_date(ticker)
    if pd.isna(max_date):
        return False

    target_date = pd.Timestamp(end) - pd.Timedelta(days=FRESH_PRICE_GRACE_DAYS)
    return bool(max_date >= target_date)


def _yahoo_ticker(ticker: str) -> str:
    """Map source tickers to the Yahoo symbols needed for price downloads."""
    return YAHOO_TICKER_ALIASES.get(ticker, ticker)


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
        for level in range(download.columns.nlevels):
            values = download.columns.get_level_values(level)
            if ticker in values:
                return download.xs(ticker, axis=1, level=level, drop_level=True)
        return pd.DataFrame()

    return download


def _download_batch(batch: list[str], start: str, end: str, *, threads: bool) -> pd.DataFrame:
    """Download one Yahoo batch."""
    yahoo_batch = sorted({_yahoo_ticker(ticker) for ticker in batch})
    return yf.download(
        tickers=yahoo_batch,
        start=start,
        end=end,
        group_by="ticker",
        auto_adjust=False,
        progress=False,
        threads=threads,
    )


def _save_batch_prices(
    batch: list[str],
    download: pd.DataFrame,
    successful: set[str],
    failed: set[str],
) -> None:
    """Save available price frames from one downloaded batch."""
    for ticker in batch:
        yahoo_ticker = _yahoo_ticker(ticker)
        ticker_frame = _extract_ticker_frame(download, yahoo_ticker)
        if ticker_frame.empty or ticker_frame.dropna(how="all").empty:
            failed.add(ticker)
            continue

        normalized = _normalize_price_frame(ticker_frame, ticker)
        normalized.to_parquet(_ticker_output_path(ticker), index=False)
        successful.add(ticker)
        failed.discard(ticker)


def fetch_prices(tickers: list[str], start: str, end: str) -> tuple[list[str], list[str]]:
    """Download daily OHLCV in batches and save one parquet file per ticker."""
    PRICES_DIR.mkdir(parents=True, exist_ok=True)

    universe = sorted({ticker.strip().upper() for ticker in tickers if ticker and ticker.strip()})
    if "SPY" not in universe:
        universe.append("SPY")
        universe.sort()

    successful: set[str] = {
        ticker for ticker in universe if _has_fresh_saved_price_file(ticker, end)
    }
    failed: set[str] = set()
    download_universe = [ticker for ticker in universe if ticker not in successful]
    if successful:
        print(f"Using fresh saved price files for {len(successful):,} tickers")

    for batch_number, batch in enumerate(_batched(download_universe, BATCH_SIZE), start=1):
        print(f"Downloading batch {batch_number}: {len(batch)} tickers")
        try:
            download = _download_batch(batch, start, end, threads=True)
        except Exception as exc:
            print(f"Batch failed: {exc}")
            failed.update(batch)
            continue

        _save_batch_prices(batch, download, successful, failed)

    if failed:
        retry_candidates = sorted(failed)
        failed.clear()
        print(f"Retrying {len(retry_candidates):,} tickers in smaller batches")
        for batch_number, batch in enumerate(_batched(retry_candidates, RETRY_BATCH_SIZE), start=1):
            print(f"Retry batch {batch_number}: {len(batch)} tickers")
            try:
                download = _download_batch(batch, start, end, threads=False)
            except Exception as exc:
                print(f"Retry batch failed: {exc}")
                failed.update(batch)
                time.sleep(RETRY_SLEEP_SECONDS)
                continue

            _save_batch_prices(batch, download, successful, failed)
            time.sleep(RETRY_SLEEP_SECONDS)

    for ticker in sorted(failed):
        if _has_saved_price_file(ticker):
            print(f"Keeping existing saved price data for {ticker}")
            successful.add(ticker)
        else:
            print(f"No price data for {ticker}")

    final_failed = sorted(ticker for ticker in universe if ticker not in successful)
    final_successful = sorted(successful)

    print(f"Successful tickers: {len(final_successful):,}")
    print(f"Failed tickers: {len(final_failed):,}")
    if final_failed:
        print(f"Failed ticker list: {', '.join(final_failed)}")

    return final_successful, final_failed


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
