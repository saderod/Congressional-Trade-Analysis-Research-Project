import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Backtest, fetchBacktest } from "../lib/api";
import { formatCurrency } from "../lib/format";
import { useApi } from "../lib/useApi";
import { ErrorBlock, LoadingBlock } from "./StateBlock";

function buildEquityRows(backtest: Backtest) {
  const rows = new Map<string, { date: string; baseline?: number; nlpFiltered?: number; spy?: number }>();
  for (const [key, curve] of [
    ["baseline", backtest.baseline.equity_curve],
    ["nlpFiltered", backtest.nlp_filtered.equity_curve],
    ["spy", backtest.spy.equity_curve],
  ] as const) {
    for (const point of curve) {
      const row = rows.get(point.date) ?? { date: point.date };
      row[key] = point.equity;
      rows.set(point.date, row);
    }
  }
  return [...rows.values()].sort((a, b) => a.date.localeCompare(b.date));
}

export function EquityCurveChart() {
  const { data, loading, error } = useApi(fetchBacktest);

  if (loading) return <LoadingBlock label="equity curve" />;
  if (error || !data) return <ErrorBlock label="equity curve" />;

  const chartData = buildEquityRows(data);

  return (
    <section className="rounded-md border border-slate-200 bg-white p-6">
      <div>
        <h2 className="text-lg font-semibold text-slate-950">Equity Curve</h2>
        <p className="mt-1 text-sm text-slate-500">Baseline trades, NLP-filtered trades, and SPY benchmark</p>
      </div>
      <div className="mt-5 h-80">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 12, right: 12, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#e2e8f0" vertical={false} />
            <XAxis dataKey="date" minTickGap={32} tickLine={false} axisLine={false} />
            <YAxis tickFormatter={(value) => `$${Math.round(Number(value) / 1000)}k`} tickLine={false} axisLine={false} width={56} />
            <Tooltip formatter={(value) => formatCurrency(Number(value))} />
            <Line type="monotone" dataKey="baseline" name="Baseline" stroke="#2563eb" strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="nlpFiltered" name="NLP filtered" stroke="#059669" strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="spy" name="SPY" stroke="#64748b" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
