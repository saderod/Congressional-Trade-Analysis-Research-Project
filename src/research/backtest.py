"""Simple event-driven backtests for baseline and NLP-filtered Senate buys."""

from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd

from src.config import PROCESSED_DIR, RESULTS_DIR


FEATURES_PATH = PROCESSED_DIR / "features.parquet"
PRICES_PATH = PROCESSED_DIR / "prices.parquet"
BACKTEST_PATH = RESULTS_DIR / "backtest.json"
INITIAL_CAPITAL = 100_000.0
MAX_CONCURRENT_POSITIONS = 20
HOLD_DAYS = 21
ROUND_TRIP_COST = 0.001
TEST_START = pd.Timestamp("2023-01-01")


def _json_default(value: Any) -> Any:
    """Convert numpy/pandas values for JSON serialization."""
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        if np.isnan(value):
            return None
        return float(value)
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    if pd.isna(value):
        return None
    return value


def _daily_calendar(prices: pd.DataFrame) -> pd.DatetimeIndex:
    """Return the SPY trading calendar covering the backtest period."""
    spy = prices.loc[prices["ticker"].eq("SPY")].copy()
    spy["date"] = pd.to_datetime(spy["date"])
    return pd.DatetimeIndex(spy.loc[spy["date"] >= TEST_START, "date"].sort_values())


def _eligible_buys(features: pd.DataFrame) -> pd.DataFrame:
    """Return buy trades with complete 21-day return data in the test period."""
    frame = features.copy()
    frame["signal_date"] = pd.to_datetime(frame["signal_date"])
    return frame.loc[
        frame["is_buy"]
        & frame["signal_date"].ge(TEST_START)
        & frame["entry_price"].notna()
        & frame["fwd_return_21d"].notna()
    ].copy()


def _select_entries(candidates: pd.DataFrame, open_positions: pd.DataFrame) -> pd.DataFrame:
    """Select entries with max-concurrent cap and lag tie-break."""
    slots = MAX_CONCURRENT_POSITIONS - len(open_positions)
    if slots <= 0 or candidates.empty:
        return candidates.iloc[0:0].copy()
    return candidates.sort_values(["disclosure_lag_days", "trade_id"]).head(slots).copy()


def run_strategy(
    features: pd.DataFrame,
    *,
    nlp_filtered: bool,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
) -> dict[str, Any]:
    """Run a 21-day hold event backtest over senator buys."""
    candidates = _eligible_buys(features)
    if nlp_filtered:
        candidates = candidates.loc[candidates["sentiment_score_30d"].gt(0)].copy()

    candidates["exit_date"] = candidates["signal_date"] + pd.offsets.BDay(HOLD_DAYS)
    all_dates = pd.bdate_range(start_date, end_date)

    cash = INITIAL_CAPITAL
    open_positions: list[dict[str, Any]] = []
    equity_rows: list[dict[str, Any]] = []
    trade_rows: list[dict[str, Any]] = []

    for current_date in all_dates:
        exiting = [position for position in open_positions if position["exit_date"] == current_date]
        if exiting:
            for trade in exiting:
                cash += trade["position_value"] * (1.0 + trade["net_return"])
                trade_rows.append(
                    {
                        "trade_id": int(trade["trade_id"]),
                        "ticker": trade["ticker"],
                        "entry_date": trade["signal_date"].date().isoformat(),
                        "exit_date": trade["exit_date"].date().isoformat(),
                        "entry_price": float(trade["entry_price"]),
                        "net_return": float(trade["net_return"]),
                        "sentiment_score_30d": _json_default(trade["sentiment_score_30d"]),
                    }
                )
            exiting_ids = {position["trade_id"] for position in exiting}
            open_positions = [
                position for position in open_positions if position["trade_id"] not in exiting_ids
            ]

        todays_candidates = candidates.loc[candidates["signal_date"].eq(current_date)].copy()
        todays_entries = _select_entries(todays_candidates, pd.DataFrame(open_positions))
        if not todays_entries.empty:
            allocation = cash / (len(open_positions) + len(todays_entries))
            for position in open_positions:
                cash += position["position_value"] - allocation
                position["position_value"] = allocation

            for entry in todays_entries.itertuples(index=False):
                net_return = float(entry.fwd_return_21d - ROUND_TRIP_COST)
                position = entry._asdict()
                position["position_value"] = allocation
                position["net_return"] = net_return
                open_positions.append(position)
                cash -= allocation

        equity = cash + sum(float(position["position_value"]) for position in open_positions)
        equity_rows.append(
            {
                "date": current_date.date().isoformat(),
                "equity": equity,
                "cash": cash,
                "open_positions": int(len(open_positions)),
            }
        )

    equity_curve = pd.DataFrame(equity_rows)
    trades = pd.DataFrame(trade_rows)
    return {
        "equity_curve": equity_curve.to_dict(orient="records"),
        "metrics": _metrics(equity_curve, trades),
        "trades": trades.to_dict(orient="records"),
    }


def run_spy(prices: pd.DataFrame, *, start_date: pd.Timestamp, end_date: pd.Timestamp) -> dict[str, Any]:
    """Run a buy-and-hold SPY benchmark over the same test calendar."""
    spy = prices.loc[prices["ticker"].eq("SPY")].copy()
    spy["date"] = pd.to_datetime(spy["date"])
    spy = spy.loc[spy["date"].ge(start_date) & spy["date"].le(end_date)].sort_values("date")
    if spy.empty:
        equity_curve = pd.DataFrame(
            [{"date": start_date.date().isoformat(), "equity": INITIAL_CAPITAL}]
        )
        return {"equity_curve": equity_curve.to_dict(orient="records"), "metrics": _metrics(equity_curve)}

    first_close = float(spy.iloc[0]["close"])
    spy["equity"] = INITIAL_CAPITAL * spy["close"].astype(float) / first_close
    equity_curve = spy[["date", "equity"]].copy()
    equity_curve["date"] = equity_curve["date"].dt.date.astype(str)
    return {"equity_curve": equity_curve.to_dict(orient="records"), "metrics": _metrics(equity_curve)}


def _metrics(equity_curve: pd.DataFrame, trades: pd.DataFrame | None = None) -> dict[str, Any]:
    """Calculate standard backtest metrics."""
    curve = equity_curve.copy()
    curve["equity"] = curve["equity"].astype(float)
    if len(curve) < 2:
        total_return = curve["equity"].iloc[-1] / INITIAL_CAPITAL - 1.0
        return {
            "total_return": float(total_return),
            "annualized_return": None,
            "volatility": None,
            "sharpe": None,
            "max_drawdown": 0.0,
            "hit_rate": None,
            "trade_count": int(0 if trades is None else len(trades)),
        }

    returns = curve["equity"].pct_change().dropna()
    total_return = curve["equity"].iloc[-1] / curve["equity"].iloc[0] - 1.0
    annualized_return = (1.0 + total_return) ** (252 / max(len(returns), 1)) - 1.0
    volatility = returns.std(ddof=1) * np.sqrt(252) if len(returns) > 1 else 0.0
    sharpe = annualized_return / volatility if volatility and volatility > 0 else None
    drawdown = curve["equity"] / curve["equity"].cummax() - 1.0

    if trades is not None and not trades.empty:
        hit_rate = float((trades["net_return"] > 0).mean())
        trade_count = int(len(trades))
    else:
        hit_rate = None
        trade_count = int(0 if trades is None else len(trades))

    return {
        "total_return": float(total_return),
        "annualized_return": float(annualized_return),
        "volatility": float(volatility),
        "sharpe": float(sharpe) if sharpe is not None else None,
        "max_drawdown": float(drawdown.min()),
        "hit_rate": hit_rate,
        "trade_count": trade_count,
    }


def run_backtests() -> dict[str, Any]:
    """Run baseline, NLP-filtered, and SPY benchmark backtests."""
    if not FEATURES_PATH.exists():
        raise FileNotFoundError(f"Missing features parquet: {FEATURES_PATH}")
    if not PRICES_PATH.exists():
        raise FileNotFoundError(f"Missing processed prices parquet: {PRICES_PATH}")

    features = pd.read_parquet(FEATURES_PATH)
    prices = pd.read_parquet(PRICES_PATH)
    baseline_candidates = _eligible_buys(features)
    if baseline_candidates.empty:
        start_date = TEST_START
        end_date = TEST_START
    else:
        start_date = baseline_candidates["signal_date"].min()
        end_date = (baseline_candidates["signal_date"] + pd.offsets.BDay(HOLD_DAYS)).max()

    result = {
        "baseline": run_strategy(
            features,
            nlp_filtered=False,
            start_date=start_date,
            end_date=end_date,
        ),
        "nlp_filtered": run_strategy(
            features,
            nlp_filtered=True,
            start_date=start_date,
            end_date=end_date,
        ),
        "spy": run_spy(prices, start_date=start_date, end_date=end_date),
    }

    BACKTEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    BACKTEST_PATH.write_text(json.dumps(result, indent=2, default=_json_default), encoding="utf-8")
    return result


def _metrics_table(result: dict[str, Any]) -> pd.DataFrame:
    """Return a compact metrics comparison table."""
    rows = []
    for name in ["baseline", "nlp_filtered", "spy"]:
        row = {"strategy": name}
        row.update(result[name]["metrics"])
        rows.append(row)
    return pd.DataFrame(rows)


def main() -> None:
    """Run baseline and NLP-filtered backtests."""
    result = run_backtests()
    print(f"Backtest results -> {BACKTEST_PATH}")
    print(_metrics_table(result).to_string(index=False))


if __name__ == "__main__":
    main()
