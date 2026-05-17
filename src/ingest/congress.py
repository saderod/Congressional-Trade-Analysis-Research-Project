"""Download and normalize Senate Stock Watcher trade disclosures."""

from __future__ import annotations

import re
from typing import Any

import pandas as pd
import requests

from src.config import RAW_DIR


TRADE_URLS = [
    "https://senatestockwatcher.com/aggregate/all_transactions.json",
    "https://raw.githubusercontent.com/jeremiak/senate-stock-watcher-data/master/aggregate/all_transactions.json",
    "https://raw.githubusercontent.com/timothycarambat/senate-stock-watcher-data/master/aggregate/all_transactions.json",
]
SUMMARY_URLS = [
    "https://senatestockwatcher.com/aggregate/all_daily_summaries.json",
    "https://raw.githubusercontent.com/jeremiak/senate-stock-watcher-data/master/aggregate/all_daily_summaries.json",
    "https://raw.githubusercontent.com/timothycarambat/senate-stock-watcher-data/master/aggregate/all_daily_summaries.json",
]
OUTPUT_PATH = RAW_DIR / "senate_trades" / "trades.parquet"


def _download_json(urls: list[str]) -> list[dict[str, Any]]:
    """Download JSON from the first reachable URL in priority order."""
    last_error: Exception | None = None
    for url in urls:
        try:
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            print(f"Downloaded {url}")
            data = response.json()
            if not isinstance(data, list):
                raise ValueError(f"Expected a JSON list from {url}")
            return data
        except (requests.RequestException, ValueError) as exc:
            print(f"Failed {url}: {exc}")
            last_error = exc
    raise RuntimeError("All Senate Stock Watcher data sources failed") from last_error


def _parse_amount_range(amount: object) -> tuple[float | None, float | None]:
    """Convert STOCK Act amount buckets into numeric low/high bounds."""
    if not isinstance(amount, str):
        return None, None

    values = [int(match.replace(",", "")) for match in re.findall(r"\$?([\d,]+)", amount)]
    if len(values) >= 2:
        return float(values[0]), float(values[1])
    if len(values) == 1:
        return float(values[0]), float(values[0])
    return None, None


def _normalize_trade_type(trade_type: object) -> str | None:
    """Map source transaction descriptions to buy/sell labels."""
    if not isinstance(trade_type, str):
        return None

    lowered = trade_type.lower()
    if "purchase" in lowered:
        return "buy"
    if "sale" in lowered:
        return "sell"
    return None


def _looks_like_public_stock_ticker(ticker: object) -> bool:
    """Return False for fund, option, preferred, and when-issued ticker shapes."""
    if not isinstance(ticker, str):
        return False
    if re.fullmatch(r"[A-Z]{4}X", ticker):
        return False
    if re.fullmatch(r"[A-Z]{1,6}\d{6}[CP]\d{8}", ticker):
        return False
    return not any(suffix in ticker for suffix in ["-P", "-R", "-WI"])


def _build_disclosure_lookup(summaries: list[dict[str, Any]]) -> dict[str, str]:
    """Return a filing-link to received-date lookup from daily summary records."""
    lookup: dict[str, str] = {}
    for filing in summaries:
        ptr_link = filing.get("ptr_link")
        disclosure_date = filing.get("date_recieved") or filing.get("date_received")
        if isinstance(ptr_link, str) and isinstance(disclosure_date, str):
            lookup[ptr_link] = disclosure_date
    return lookup


def fetch_senate_trades() -> pd.DataFrame:
    """Fetch Senate trades, normalize required columns, and save raw parquet."""
    trades = _download_json(TRADE_URLS)
    summaries = _download_json(SUMMARY_URLS)
    disclosure_lookup = _build_disclosure_lookup(summaries)

    frame = pd.DataFrame(trades)
    if frame.empty:
        raise RuntimeError("Senate Stock Watcher returned no transactions")

    frame["disclosure_date"] = frame["ptr_link"].map(disclosure_lookup)
    amount_bounds = frame["amount"].apply(_parse_amount_range)
    frame["amount_range_low"] = amount_bounds.apply(lambda value: value[0])
    frame["amount_range_high"] = amount_bounds.apply(lambda value: value[1])
    frame["type"] = frame["type"].apply(_normalize_trade_type)

    frame["transaction_date"] = pd.to_datetime(frame["transaction_date"], errors="coerce")
    frame["disclosure_date"] = pd.to_datetime(frame["disclosure_date"], errors="coerce")
    frame["ticker"] = frame["ticker"].replace("--", pd.NA).astype("string").str.upper().str.strip()

    stock_mask = frame["asset_type"].astype("string").str.strip().str.lower().eq("stock")
    action_mask = frame["type"].isin(["buy", "sell"])
    ticker_mask = frame["ticker"].notna() & frame["ticker"].ne("")
    public_stock_mask = frame["ticker"].apply(_looks_like_public_stock_ticker)
    output = frame.loc[stock_mask & action_mask & ticker_mask & public_stock_mask].copy()

    required_columns = [
        "senator",
        "ticker",
        "transaction_date",
        "disclosure_date",
        "type",
        "amount_range_low",
        "amount_range_high",
        "asset_type",
    ]
    output = output[required_columns].sort_values(["disclosure_date", "transaction_date", "senator"])

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    output.to_parquet(OUTPUT_PATH, index=False)

    date_min = output["transaction_date"].min().date()
    date_max = output["transaction_date"].max().date()
    missing_disclosures = int(output["disclosure_date"].isna().sum())
    print(f"Saved {len(output):,} stock trades to {OUTPUT_PATH}")
    print(f"Transaction date range: {date_min} to {date_max}")
    print(f"Unique senators: {output['senator'].nunique():,}")
    print(f"Unique tickers: {output['ticker'].nunique():,}")
    print(f"Rows missing disclosure_date: {missing_disclosures:,}")
    return output


def main() -> None:
    """Run Senate trade ingestion from the command line."""
    fetch_senate_trades()


if __name__ == "__main__":
    main()
