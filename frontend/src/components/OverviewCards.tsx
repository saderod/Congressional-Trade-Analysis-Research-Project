import { fetchOverview } from "../lib/api";
import { formatInteger, formatNumber, formatPercent } from "../lib/format";
import { useApi } from "../lib/useApi";
import { ErrorBlock, LoadingBlock } from "./StateBlock";

export function OverviewCards() {
  const { data, loading, error } = useApi(fetchOverview);

  if (loading) return <LoadingBlock label="overview" />;
  if (error || !data) return <ErrorBlock label="overview" />;

  const cards = [
    {
      label: "Trades",
      value: formatInteger(data.total_trades),
      detail: tradeCoverageText(data.total_trades, data.trades_with_21d_return),
    },
    {
      label: "Mean Buy Excess",
      value: formatPercent(data.buys.mean_excess_return_21d, 2),
      detail: performanceText(data.buys.count, data.buys.mean_excess_return_21d, "buys"),
    },
    {
      label: "Mean Sell Excess",
      value: formatPercent(data.sells.mean_excess_return_21d, 2),
      detail: performanceText(data.sells.count, data.sells.mean_excess_return_21d, "sells"),
    },
    {
      label: "Buy vs Sell p-value",
      value: formatNumber(data.buy_vs_sell_ttest.p_value, 3),
      detail: significanceText(
        data.buy_vs_sell_ttest.p_value,
        data.buys.mean_excess_return_21d,
        data.sells.mean_excess_return_21d,
      ),
    },
  ];

  return (
    <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {cards.map((card) => (
        <div key={card.label} className="rounded-md border border-slate-200 bg-white p-5">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{card.label}</p>
          <p className="mt-3 text-3xl font-semibold text-slate-950">{card.value}</p>
          <p className="mt-2 text-sm text-slate-500">{card.detail}</p>
        </div>
      ))}
    </section>
  );
}

function tradeCoverageText(totalTrades: number, tradesWithReturn: number): string {
  if (totalTrades === 0) {
    return "No congressional stock trades were found for the current study period.";
  }

  const coverage = tradesWithReturn / totalTrades;
  const coverageText =
    coverage >= 0.9
      ? "Most"
      : coverage >= 0.5
        ? "Some"
        : "Only a small share of";
  return `Congressional stock trades reported since January 2025. ${coverageText} could be checked one month later (${formatInteger(tradesWithReturn)} of ${formatInteger(totalTrades)}).`;
}

function performanceText(count: number, value: number | null, label: "buys" | "sells"): string {
  if (count === 0 || value === null) {
    return `No ${label} had enough data to compare with the market one month later.`;
  }

  if (Math.abs(value) < 0.001) {
    return `${formatInteger(count)} ${label} performed about the same as the market one month after they were reported.`;
  }

  const direction = value > 0 ? "beat" : "trailed";
  return `${formatInteger(count)} ${label} ${direction} the market by ${formatPercent(Math.abs(value), 2)} on average one month after they were reported.`;
}

function significanceText(
  pValue: number | null,
  buyReturn: number | null,
  sellReturn: number | null,
): string {
  if (pValue === null || buyReturn === null || sellReturn === null) {
    return "There is not enough data to compare buys and sells.";
  }

  const strongerSide =
    Math.abs(buyReturn - sellReturn) < 0.001 ? "similar" : buyReturn > sellReturn ? "buys" : "sells";
  const confidence =
    pValue < 0.05
      ? "strong evidence"
      : pValue < 0.1
        ? "some evidence"
        : "not strong enough evidence";

  if (strongerSide === "similar") {
    return `Buys and sells performed about the same. The test found ${confidence} of a real difference.`;
  }
  return `${capitalize(strongerSide)} looked better in this sample, but the test found ${confidence} that the difference is real.`;
}

function capitalize(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}
