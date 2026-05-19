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
      detail: `Congressional stock trades reported since January 2025. ${formatInteger(data.trades_with_21d_return)} could be checked one month later.`,
    },
    {
      label: "Mean Buy Excess",
      value: formatPercent(data.buys.mean_excess_return_21d, 2),
      detail: `${formatInteger(data.buys.count)} buys beat the market by this much on average one month after they were reported.`,
    },
    {
      label: "Mean Sell Excess",
      value: formatPercent(data.sells.mean_excess_return_21d, 2),
      detail: `${formatInteger(data.sells.count)} sells beat the market by this much on average one month after they were reported.`,
    },
    {
      label: "Buy vs Sell p-value",
      value: formatNumber(data.buy_vs_sell_ttest.p_value, 3),
      detail: "This is not strong enough to prove that buys and sells performed differently.",
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
