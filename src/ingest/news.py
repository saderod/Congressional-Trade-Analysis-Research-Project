"""Download recent Yahoo Finance headlines for the Senate ticker universe."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yfinance as yf

from src.config import RAW_DIR
from src.ingest.prices import YAHOO_TICKER_ALIASES


TRADES_PATH = RAW_DIR / "senate_trades" / "trades.parquet"
NEWS_DIR = RAW_DIR / "news"
NEWS_SCHEMA = ["ticker", "headline", "summary", "publisher", "published_at", "url", "source"]
FRESH_NEWS_GRACE_DAYS = 14


def _ticker_output_path(ticker: str) -> Path:
    """Return the parquet path for a ticker's news headlines."""
    return NEWS_DIR / f"{ticker}.parquet"


def _saved_news_max_published_at(ticker: str) -> pd.Timestamp | None:
    """Return the latest saved news timestamp for a ticker, if readable."""
    path = _ticker_output_path(ticker)
    if not path.exists() or path.stat().st_size == 0:
        return None

    try:
        published_at = pd.read_parquet(path, columns=["published_at"])["published_at"]
    except (OSError, ValueError, KeyError, FileNotFoundError):
        return None

    if published_at.empty:
        return None
    return pd.to_datetime(published_at, utc=True, errors="coerce", format="ISO8601").max()


def _has_fresh_saved_news_file(ticker: str) -> bool:
    """Return True when a ticker has a recent saved Yahoo news file."""
    max_published_at = _saved_news_max_published_at(ticker)
    if pd.isna(max_published_at):
        return False

    cutoff = pd.Timestamp.now(tz=UTC) - pd.Timedelta(days=FRESH_NEWS_GRACE_DAYS)
    return bool(max_published_at >= cutoff)


def _yahoo_ticker(ticker: str) -> str:
    """Map source tickers to the Yahoo symbols needed for news downloads."""
    return YAHOO_TICKER_ALIASES.get(ticker, ticker)


def _nested_get(data: dict[str, Any], path: list[str]) -> Any:
    """Return a nested dictionary value or None."""
    current: Any = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _published_at(raw_value: Any) -> str | None:
    """Normalize Yahoo publish timestamps to UTC ISO strings."""
    if raw_value is None:
        return None
    if isinstance(raw_value, int | float):
        return datetime.fromtimestamp(raw_value, tz=UTC).isoformat()
    if isinstance(raw_value, str):
        parsed = pd.to_datetime(raw_value, utc=True, errors="coerce")
        if pd.notna(parsed):
            return parsed.isoformat()
    return None


def _normalize_news_item(item: dict[str, Any], ticker: str) -> dict[str, Any] | None:
    """Normalize old and new yfinance news schemas to the project schema."""
    content = item.get("content") if isinstance(item.get("content"), dict) else {}

    headline = item.get("title") or content.get("title")
    if not isinstance(headline, str) or not headline.strip():
        return None

    publisher = (
        item.get("publisher")
        or content.get("providerDisplayName")
        or _nested_get(content, ["provider", "displayName"])
    )
    url = item.get("link") or item.get("url") or _nested_get(content, ["canonicalUrl", "url"])
    raw_published_at = (
        item.get("providerPublishTime") or content.get("pubDate") or item.get("pubDate")
    )

    return {
        "ticker": ticker,
        "headline": headline.strip(),
        "summary": item.get("summary") or content.get("summary") or "",
        "publisher": publisher or "",
        "published_at": _published_at(raw_published_at),
        "url": url or "",
        "source": "yfinance",
    }


def fetch_news_for_tickers(tickers: list[str]) -> None:
    """Fetch recent Yahoo Finance news and save one parquet per covered ticker."""
    NEWS_DIR.mkdir(parents=True, exist_ok=True)
    universe = sorted({ticker.strip().upper() for ticker in tickers if ticker and ticker.strip()})
    fresh_saved = {ticker for ticker in universe if _has_fresh_saved_news_file(ticker)}
    download_universe = [ticker for ticker in universe if ticker not in fresh_saved]
    if fresh_saved:
        print(f"Using fresh saved news files for {len(fresh_saved):,} tickers")

    total_headlines = 0
    covered_tickers: set[str] = set(fresh_saved)
    published_dates: list[pd.Timestamp] = []

    for index, ticker in enumerate(download_universe, start=1):
        yahoo_ticker = _yahoo_ticker(ticker)
        try:
            raw_items = yf.Ticker(yahoo_ticker).get_news(count=10)
        except Exception as exc:
            print(f"[{index}/{len(download_universe)}] Failed news for {ticker}: {exc}")
            time.sleep(0.5)
            continue

        rows = [
            row
            for item in raw_items
            if isinstance(item, dict)
            for row in [_normalize_news_item(item, ticker)]
            if row is not None
        ]
        if not rows:
            print(f"[{index}/{len(download_universe)}] No news for {ticker}")
            time.sleep(0.5)
            continue

        frame = pd.DataFrame(rows, columns=NEWS_SCHEMA).drop_duplicates(subset=["ticker", "url"])
        frame.to_parquet(_ticker_output_path(ticker), index=False)

        total_headlines += len(frame)
        covered_tickers.add(ticker)
        published = pd.to_datetime(
            frame["published_at"],
            utc=True,
            errors="coerce",
            format="ISO8601",
        ).dropna()
        published_dates.extend(published.to_list())
        print(f"[{index}/{len(download_universe)}] Saved {len(frame):,} headlines for {ticker}")
        time.sleep(0.5)

    print(f"Total headlines: {total_headlines:,}")
    print(f"Unique tickers covered: {len(covered_tickers):,}")
    if published_dates:
        print(f"News date range: {min(published_dates).date()} to {max(published_dates).date()}")
    else:
        print("News date range: unavailable")


def load_ticker_universe() -> list[str]:
    """Load distinct tickers from Phase 2a's Senate trade parquet."""
    if not TRADES_PATH.exists():
        raise FileNotFoundError(f"Missing Phase 2a trades parquet: {TRADES_PATH}")

    trades = pd.read_parquet(TRADES_PATH, columns=["ticker"])
    return trades["ticker"].dropna().astype(str).tolist()


def main() -> None:
    """Run Yahoo Finance news ingestion from the command line."""
    fetch_news_for_tickers(load_ticker_universe())


if __name__ == "__main__":
    main()
