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
  const metricAccents: Record<string, string> = {
    Total: "text-blue-700",
    Annual: "text-emerald-700",
    Vol: "text-amber-700",
    Sharpe: "text-indigo-700",
    "Max DD": "text-red-700",
    Hit: "text-teal-700",
    Trades: "text-slate-700",
  };

  return (
    <section className="rounded-md border border-slate-200 bg-white p-6">
      <h2 className="text-lg font-semibold text-slate-950">Backtest Metrics</h2>
      <p className="mt-1 text-sm leading-6 text-slate-500">
        These are the numbers behind the simulated portfolio chart above. They summarize how each line performed over the full test period.
      </p>
      <div className="mt-5 overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="py-3 pr-5 font-medium">Strategy</th>
              <th className={`py-3 pr-5 font-medium ${metricAccents.Total}`}>Total</th>
              <th className={`py-3 pr-5 font-medium ${metricAccents.Annual}`}>Annual</th>
              <th className={`py-3 pr-5 font-medium ${metricAccents.Vol}`}>Vol</th>
              <th className={`py-3 pr-5 font-medium ${metricAccents.Sharpe}`}>Sharpe</th>
              <th className={`py-3 pr-5 font-medium ${metricAccents["Max DD"]}`}>Max DD</th>
              <th className={`py-3 pr-5 font-medium ${metricAccents.Hit}`}>Hit</th>
              <th className={`py-3 font-medium ${metricAccents.Trades}`}>Trades</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map(([label, metrics]) => (
              <tr key={label}>
                <td className="py-3 pr-5 font-medium text-slate-950">{label}</td>
                <td className={`py-3 pr-5 font-medium ${metricAccents.Total}`}>{formatPercent(metrics.total_return, 2)}</td>
                <td className={`py-3 pr-5 font-medium ${metricAccents.Annual}`}>{formatPercent(metrics.annualized_return, 2)}</td>
                <td className={`py-3 pr-5 font-medium ${metricAccents.Vol}`}>{formatPercent(metrics.volatility, 2)}</td>
                <td className={`py-3 pr-5 font-medium ${metricAccents.Sharpe}`}>{formatNumber(metrics.sharpe, 2)}</td>
                <td className={`py-3 pr-5 font-medium ${metricAccents["Max DD"]}`}>{formatPercent(metrics.max_drawdown, 2)}</td>
                <td className={`py-3 pr-5 font-medium ${metricAccents.Hit}`}>{formatPercent(metrics.hit_rate, 1)}</td>
                <td className={`py-3 font-medium ${metricAccents.Trades}`}>{formatInteger(metrics.trade_count)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mt-5 grid gap-3 border-t border-slate-100 pt-4 text-sm leading-6 text-slate-600 md:grid-cols-2 xl:grid-cols-4">
        <p>
          <span className={`font-medium ${metricAccents.Total}`}>Total:</span> how much the account gained or lost overall.
        </p>
        <p>
          <span className={`font-medium ${metricAccents.Annual}`}>Annual:</span> the result converted into a yearly rate.
        </p>
        <p>
          <span className={`font-medium ${metricAccents.Vol}`}>Vol:</span> how bumpy the ride was. Lower is smoother.
        </p>
        <p>
          <span className={`font-medium ${metricAccents.Sharpe}`}>Sharpe:</span> return compared with risk. Higher is better.
        </p>
        <p>
          <span className={`font-medium ${metricAccents["Max DD"]}`}>Max DD:</span> the worst drop from a high point.
        </p>
        <p>
          <span className={`font-medium ${metricAccents.Hit}`}>Hit:</span> the share of trades that made money.
        </p>
        <p>
          <span className={`font-medium ${metricAccents.Trades}`}>Trades:</span> how many trades the strategy made.
        </p>
      </div>
    </section>
  );
}
