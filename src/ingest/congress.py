"""Download and normalize Senate trade disclosures."""

from __future__ import annotations

import json
import re
import time
from typing import Any

import pandas as pd
import requests
from lxml import html

from src.config import RAW_DIR


GOVTRADES_BASE_URL = "https://www.govtrades.com"
GOVTRADES_SENATE_URL = f"{GOVTRADES_BASE_URL}/senate-stock-tracker"
LEGACY_TRADE_URLS = [
    "https://senatestockwatcher.com/aggregate/all_transactions.json",
    "https://raw.githubusercontent.com/jeremiak/senate-stock-watcher-data/master/aggregate/all_transactions.json",
    "https://raw.githubusercontent.com/timothycarambat/senate-stock-watcher-data/master/aggregate/all_transactions.json",
]
LEGACY_SUMMARY_URLS = [
    "https://senatestockwatcher.com/aggregate/all_daily_summaries.json",
    "https://raw.githubusercontent.com/jeremiak/senate-stock-watcher-data/master/aggregate/all_daily_summaries.json",
    "https://raw.githubusercontent.com/timothycarambat/senate-stock-watcher-data/master/aggregate/all_daily_summaries.json",
]
OUTPUT_PATH = RAW_DIR / "senate_trades" / "trades.parquet"
REQUEST_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; congressional-alpha/0.1)"}
REQUIRED_COLUMNS = [
    "senator",
    "ticker",
    "transaction_date",
    "disclosure_date",
    "type",
    "amount_range_low",
    "amount_range_high",
    "asset_type",
]


def _download_json(urls: list[str]) -> list[dict[str, Any]]:
    """Download JSON from the first reachable legacy URL in priority order."""
    last_error: Exception | None = None
    for url in urls:
        try:
            response = requests.get(url, timeout=60, headers=REQUEST_HEADERS)
            response.raise_for_status()
            print(f"Downloaded {url}")
            data = response.json()
            if not isinstance(data, list):
                raise ValueError(f"Expected a JSON list from {url}")
            return data
        except (requests.RequestException, ValueError) as exc:
            print(f"Failed {url}: {exc}")
            last_error = exc
    raise RuntimeError("All legacy Senate Stock Watcher data sources failed") from last_error


def _get_text(url: str) -> str:
    """Download an HTML page with a consistent user agent."""
    response = requests.get(url, timeout=60, headers=REQUEST_HEADERS)
    response.raise_for_status()
    return response.text


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
    if "purchase" in lowered or lowered == "p":
        return "buy"
    if "sale" in lowered or lowered == "s":
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
    """Return a filing-link to received-date lookup from legacy summary records."""
    lookup: dict[str, str] = {}
    for filing in summaries:
        ptr_link = filing.get("ptr_link")
        disclosure_date = filing.get("date_recieved") or filing.get("date_received")
        if isinstance(ptr_link, str) and isinstance(disclosure_date, str):
            lookup[ptr_link] = disclosure_date
    return lookup


def _govtrades_senator_links() -> list[tuple[str, str]]:
    """Return senator names and GovTrades detail-page URLs."""
    page = _get_text(GOVTRADES_SENATE_URL)
    document = html.fromstring(page)
    links: list[tuple[str, str]] = []
    for anchor in document.xpath('//a[starts-with(@href, "/senate-stock-tracker/")]'):
        href = anchor.get("href")
        name = " ".join(anchor.text_content().split())
        if not href or not name:
            continue
        if href.count("/") != 2:
            continue
        links.append((name, f"{GOVTRADES_BASE_URL}{href}"))

    deduped = list(dict.fromkeys(links))
    if not deduped:
        raise RuntimeError("GovTrades Senate tracker returned no senator links")
    return deduped


def _extract_govtrades_transactions(page: str) -> list[dict[str, Any]]:
    """Extract embedded GovTrades transaction JSON from a senator page."""
    match = re.search(r'\\"transactions\\":\[(.*?)\],\\"', page, flags=re.DOTALL)
    if not match:
        return []

    json_text = "[" + match.group(1) + "]"
    json_text = json_text.replace('\\"', '"').replace("\\u0026", "&").replace("\\/", "/")
    json_text = json_text.replace('\\\\"', '\\"')
    return json.loads(json_text)


def _govtrades_row(senator: str, transaction: dict[str, Any]) -> dict[str, Any]:
    """Map one GovTrades transaction into the project trade schema."""
    filing_id = transaction.get("filing_id") or ""
    ptr_link = (
        f"https://efdsearch.senate.gov/search/view/ptr/{filing_id}/"
        if isinstance(filing_id, str) and filing_id
        else ""
    )
    return {
        "senator": senator,
        "ticker": transaction.get("ticker"),
        "transaction_date": transaction.get("date"),
        "disclosure_date": transaction.get("filing_date") or transaction.get("notification_date"),
        "type": transaction.get("transaction_type_full") or transaction.get("transaction_type"),
        "amount_range_low": transaction.get("amount_min"),
        "amount_range_high": transaction.get("amount_max"),
        "asset_type": transaction.get("asset_type"),
        "ptr_link": ptr_link,
        "source": "govtrades",
    }


def _fetch_govtrades_trades() -> pd.DataFrame:
    """Fetch all Senate trades from GovTrades senator detail pages."""
    rows: list[dict[str, Any]] = []
    senator_links = _govtrades_senator_links()
    print(f"Found {len(senator_links):,} GovTrades senator pages")

    for index, (senator, url) in enumerate(senator_links, start=1):
        page = _get_text(url)
        transactions = _extract_govtrades_transactions(page)
        print(f"[{index}/{len(senator_links)}] {senator}: {len(transactions):,} transactions")
        rows.extend(_govtrades_row(senator, transaction) for transaction in transactions)
        time.sleep(0.1)

    if not rows:
        raise RuntimeError("GovTrades returned no Senate transactions")
    return pd.DataFrame(rows)


def _fetch_legacy_senate_stock_watcher_trades() -> pd.DataFrame:
    """Fetch stale Senate Stock Watcher data as a fallback source."""
    trades = _download_json(LEGACY_TRADE_URLS)
    summaries = _download_json(LEGACY_SUMMARY_URLS)
    disclosure_lookup = _build_disclosure_lookup(summaries)

    frame = pd.DataFrame(trades)
    if frame.empty:
        raise RuntimeError("Senate Stock Watcher returned no transactions")

    frame["disclosure_date"] = frame["ptr_link"].map(disclosure_lookup)
    amount_bounds = frame["amount"].apply(_parse_amount_range)
    frame["amount_range_low"] = amount_bounds.apply(lambda value: value[0])
    frame["amount_range_high"] = amount_bounds.apply(lambda value: value[1])
    frame["source"] = "senate_stock_watcher"
    return frame


def _normalize_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize and filter a raw Senate trade frame."""
    frame = frame.copy()
    if "ptr_link" not in frame.columns:
        frame["ptr_link"] = ""
    if "source" not in frame.columns:
        frame["source"] = ""

    frame["type"] = frame["type"].apply(_normalize_trade_type)
    frame["transaction_date"] = pd.to_datetime(frame["transaction_date"], errors="coerce")
    frame["disclosure_date"] = pd.to_datetime(frame["disclosure_date"], errors="coerce")
    frame["ticker"] = frame["ticker"].replace("--", pd.NA).astype("string").str.upper().str.strip()
    frame["asset_type"] = frame["asset_type"].fillna("").astype("string").str.strip()
    frame["amount_range_low"] = pd.to_numeric(frame["amount_range_low"], errors="coerce")
    frame["amount_range_high"] = pd.to_numeric(frame["amount_range_high"], errors="coerce")

    stock_mask = frame["asset_type"].str.lower().eq("stock")
    action_mask = frame["type"].isin(["buy", "sell"])
    ticker_mask = frame["ticker"].notna() & frame["ticker"].ne("")
    public_stock_mask = frame["ticker"].apply(_looks_like_public_stock_ticker)
    output = frame.loc[stock_mask & action_mask & ticker_mask & public_stock_mask].copy()

    output = output[REQUIRED_COLUMNS + ["ptr_link", "source"]].drop_duplicates()
    return output.sort_values(["disclosure_date", "transaction_date", "senator"]).reset_index(
        drop=True
    )


def fetch_senate_trades() -> pd.DataFrame:
    """Fetch Senate trades, normalize required columns, and save raw parquet."""
    try:
        frame = _fetch_govtrades_trades()
    except Exception as exc:
        print(f"GovTrades fetch failed: {exc}")
        print("Falling back to stale Senate Stock Watcher sources.")
        frame = _fetch_legacy_senate_stock_watcher_trades()

    output = _normalize_frame(frame)
    if output.empty:
        raise RuntimeError("No normalized Senate stock trades were produced")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    output.to_parquet(OUTPUT_PATH, index=False)

    date_min = output["transaction_date"].min().date()
    date_max = output["transaction_date"].max().date()
    disclosure_min = output["disclosure_date"].min().date()
    disclosure_max = output["disclosure_date"].max().date()
    missing_disclosures = int(output["disclosure_date"].isna().sum())
    print(f"Saved {len(output):,} stock trades to {OUTPUT_PATH}")
    print(f"Transaction date range: {date_min} to {date_max}")
    print(f"Disclosure date range: {disclosure_min} to {disclosure_max}")
    print(f"Unique senators: {output['senator'].nunique():,}")
    print(f"Unique tickers: {output['ticker'].nunique():,}")
    print(f"Rows missing disclosure_date: {missing_disclosures:,}")
    return output


def main() -> None:
    """Run Senate trade ingestion from the command line."""
    fetch_senate_trades()


if __name__ == "__main__":
    main()
