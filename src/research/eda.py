"""Exploratory research summaries for congressional-alpha."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from statsmodels.stats.weightstats import DescrStatsW, ttest_ind

from src.config import PROCESSED_DIR, RESULTS_DIR


FEATURES_PATH = PROCESSED_DIR / "features.parquet"
NLP_ROUTING_PATH = RESULTS_DIR / "nlp_routing.json"
EDA_DIR = RESULTS_DIR / "eda"
RETURN_COLUMN = "excess_return_21d"


def _json_default(value: Any) -> Any:
    """Convert numpy/pandas scalars for JSON serialization."""
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        if np.isnan(value):
            return None
        return float(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if pd.isna(value):
        return None
    return value


def _write_json(path: Path, payload: Any) -> None:
    """Write JSON with stable formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=_json_default), encoding="utf-8")


def _mean_ci(series: pd.Series) -> dict[str, float | None]:
    """Return mean and a 95% t confidence interval."""
    clean = series.dropna().astype(float)
    if clean.empty:
        return {"mean": None, "ci_low": None, "ci_high": None}
    stats = DescrStatsW(clean)
    ci_low, ci_high = stats.tconfint_mean()
    return {"mean": float(clean.mean()), "ci_low": float(ci_low), "ci_high": float(ci_high)}


def _ttest_by_side(features: pd.DataFrame) -> dict[str, float | None]:
    """Return buy-vs-sell t-test for 21d excess returns."""
    buys = features.loc[features["is_buy"], RETURN_COLUMN].dropna()
    sells = features.loc[~features["is_buy"], RETURN_COLUMN].dropna()
    if len(buys) < 2 or len(sells) < 2:
        return {"t_stat": None, "p_value": None}
    t_stat, p_value, _ = ttest_ind(buys, sells, usevar="unequal")
    return {"t_stat": float(t_stat), "p_value": float(p_value)}


def overview(features: pd.DataFrame) -> dict[str, Any]:
    """Build the overview output."""
    buys = features.loc[features["is_buy"]]
    sells = features.loc[~features["is_buy"]]
    return {
        "total_trades": len(features),
        "trades_with_21d_return": int(features[RETURN_COLUMN].notna().sum()),
        "buys": {
            "count": int(len(buys)),
            "mean_excess_return_21d": _mean_ci(buys[RETURN_COLUMN])["mean"],
        },
        "sells": {
            "count": int(len(sells)),
            "mean_excess_return_21d": _mean_ci(sells[RETURN_COLUMN])["mean"],
        },
        "buy_vs_sell_ttest": _ttest_by_side(features),
        "nlp_coverage": {
            "top_retrieved_count": int(features["top_news_similarity"].notna().sum()),
            "top_retrieved_pct": float(features["top_news_similarity"].notna().mean()),
            "sentiment_30d_count": int(features["sentiment_score_30d"].notna().sum()),
            "sentiment_30d_pct": float(features["sentiment_score_30d"].notna().mean()),
        },
    }


def by_senator(features: pd.DataFrame) -> list[dict[str, Any]]:
    """Top senators by mean excess return on buys, requiring n >= 10."""
    buys = features.loc[features["is_buy"] & features[RETURN_COLUMN].notna()].copy()
    rows: list[dict[str, Any]] = []
    for senator, group in buys.groupby("senator"):
        if len(group) < 10:
            continue
        ci = _mean_ci(group[RETURN_COLUMN])
        rows.append(
            {
                "senator": senator,
                "n": int(len(group)),
                "mean_excess_return_21d": ci["mean"],
                "ci_low": ci["ci_low"],
                "ci_high": ci["ci_high"],
            }
        )
    return sorted(rows, key=lambda row: row["mean_excess_return_21d"] or -999, reverse=True)[:20]


def by_lag(features: pd.DataFrame) -> list[dict[str, Any]]:
    """Bucket 21d excess returns by disclosure lag."""
    frame = features.loc[features[RETURN_COLUMN].notna()].copy()
    frame["lag_bucket"] = pd.cut(
        frame["disclosure_lag_days"],
        bins=[-np.inf, 7, 14, 30, 60, 120, np.inf],
        labels=["0-7", "8-14", "15-30", "31-60", "61-120", "121+"],
    )
    rows: list[dict[str, Any]] = []
    for bucket, group in frame.groupby("lag_bucket", observed=True):
        ci = _mean_ci(group[RETURN_COLUMN])
        rows.append(
            {
                "lag_bucket": str(bucket),
                "n": int(len(group)),
                "mean_excess_return_21d": ci["mean"],
                "ci_low": ci["ci_low"],
                "ci_high": ci["ci_high"],
            }
        )
    return rows


def by_sentiment(features: pd.DataFrame) -> list[dict[str, Any]]:
    """Mean 21d excess return on buys by sentiment quintile."""
    buys = features.loc[
        features["is_buy"]
        & features["sentiment_score_30d"].notna()
        & features[RETURN_COLUMN].notna()
    ].copy()
    if buys.empty:
        return []

    unique_scores = buys["sentiment_score_30d"].nunique()
    quantiles = min(5, unique_scores, len(buys))
    if quantiles < 2:
        buys["sentiment_quintile"] = "all"
    else:
        buys["sentiment_quintile"] = pd.qcut(
            buys["sentiment_score_30d"],
            q=quantiles,
            labels=False,
            duplicates="drop",
        ).map(lambda bucket: f"q{int(bucket) + 1}" if pd.notna(bucket) else None)

    rows: list[dict[str, Any]] = []
    for bucket, group in buys.groupby("sentiment_quintile", observed=True):
        ci = _mean_ci(group[RETURN_COLUMN])
        rows.append(
            {
                "sentiment_bucket": str(bucket),
                "n": int(len(group)),
                "mean_sentiment_score_30d": float(group["sentiment_score_30d"].mean()),
                "mean_excess_return_21d": ci["mean"],
                "ci_low": ci["ci_low"],
                "ci_high": ci["ci_high"],
            }
        )
    return rows


def run_eda() -> dict[str, Any]:
    """Generate all Phase 7 EDA JSON outputs."""
    if not FEATURES_PATH.exists():
        raise FileNotFoundError(f"Missing features parquet: {FEATURES_PATH}")
    features = pd.read_parquet(FEATURES_PATH)

    outputs = {
        "overview": overview(features),
        "by_senator": by_senator(features),
        "by_lag": by_lag(features),
        "by_sentiment": by_sentiment(features),
    }
    _write_json(EDA_DIR / "overview.json", outputs["overview"])
    _write_json(EDA_DIR / "by_senator.json", outputs["by_senator"])
    _write_json(EDA_DIR / "by_lag.json", outputs["by_lag"])
    _write_json(EDA_DIR / "by_sentiment.json", outputs["by_sentiment"])

    if NLP_ROUTING_PATH.exists():
        routing = json.loads(NLP_ROUTING_PATH.read_text(encoding="utf-8"))
        _write_json(EDA_DIR / "nlp_routing.json", routing)

    return outputs


def main() -> None:
    """Run exploratory research outputs."""
    outputs = run_eda()
    print("Overview:")
    print(json.dumps(outputs["overview"], indent=2, default=_json_default))
    print("By sentiment:")
    print(json.dumps(outputs["by_sentiment"], indent=2, default=_json_default))


if __name__ == "__main__":
    main()
