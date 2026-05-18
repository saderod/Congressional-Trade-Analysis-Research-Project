import { fetchBacktest } from "../lib/api";
import { formatInteger, formatNumber, formatPercent } from "../lib/format";
import { useApi } from "../lib/useApi";
import { ErrorBlock, LoadingBlock } from "./StateBlock";

export function MetricsTable() {
  const { data, loading, error } = useApi(fetchBacktest);

  if (loading) return <LoadingBlock label="backtest metrics" />;
  if (error || !data) return <ErrorBlock label="backtest metrics" />;

  const rows = [
    ["Baseline", data.baseline.metrics],
    ["NLP filtered", data.nlp_filtered.metrics],
    ["SPY", data.spy.metrics],
  ] as const;

  return (
    <section className="rounded-md border border-slate-200 bg-white p-6">
      <h2 className="text-lg font-semibold text-slate-950">Backtest Metrics</h2>
      <div className="mt-5 overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="py-3 pr-5 font-medium">Strategy</th>
              <th className="py-3 pr-5 font-medium">Total</th>
              <th className="py-3 pr-5 font-medium">Annual</th>
              <th className="py-3 pr-5 font-medium">Vol</th>
              <th className="py-3 pr-5 font-medium">Sharpe</th>
              <th className="py-3 pr-5 font-medium">Max DD</th>
              <th className="py-3 pr-5 font-medium">Hit</th>
              <th className="py-3 font-medium">Trades</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map(([label, metrics]) => (
              <tr key={label}>
                <td className="py-3 pr-5 font-medium text-slate-950">{label}</td>
                <td className="py-3 pr-5 text-slate-700">{formatPercent(metrics.total_return, 2)}</td>
                <td className="py-3 pr-5 text-slate-700">{formatPercent(metrics.annualized_return, 2)}</td>
                <td className="py-3 pr-5 text-slate-700">{formatPercent(metrics.volatility, 2)}</td>
                <td className="py-3 pr-5 text-slate-700">{formatNumber(metrics.sharpe, 2)}</td>
                <td className="py-3 pr-5 text-slate-700">{formatPercent(metrics.max_drawdown, 2)}</td>
                <td className="py-3 pr-5 text-slate-700">{formatPercent(metrics.hit_rate, 1)}</td>
                <td className="py-3 text-slate-700">{formatInteger(metrics.trade_count)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
