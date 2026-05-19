import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
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

function ordinalDay(day: number): string {
  if (day >= 11 && day <= 13) {
    return `${day}th`;
  }
  const suffix = day % 10 === 1 ? "st" : day % 10 === 2 ? "nd" : day % 10 === 3 ? "rd" : "th";
  return `${day}${suffix}`;
}

function formatAxisDate(value: string): string {
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  const month = date.toLocaleString("en-US", { month: "short" });
  return `${month} ${ordinalDay(date.getDate())} ${date.getFullYear()}`;
}

export function EquityCurveChart() {
  const { data, loading, error } = useApi(fetchBacktest);

  if (loading) return <LoadingBlock label="equity curve" />;
  if (error || !data) return <ErrorBlock label="equity curve" />;

  const chartData = buildEquityRows(data);

  return (
    <section className="rounded-md border border-slate-200 bg-white p-6">
      <div>
        <h2 className="text-lg font-semibold text-slate-950">Simulated Portfolio Value</h2>
        <p className="mt-1 text-sm text-slate-500">
          What a $100k account would have done by following each approach over time.
        </p>
      </div>
      <div className="mt-4 grid gap-3 text-sm text-slate-600 md:grid-cols-3">
        <p>
          <span className="font-medium text-blue-700">Blue:</span> buys or sells after a congressional trade is reported, then tracks how that strategy would grow.
        </p>
        <p>
          <span className="font-medium text-emerald-700">Green:</span> does the same thing, but only buys when related news for that stock had a positive tone.
        </p>
        <p>
          <span className="font-medium text-slate-700">Gray:</span> shows buying and holding the S&amp;P 500 ETF.
        </p>
      </div>
      <div className="mt-5 h-80">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 12, right: 18, left: 4, bottom: 22 }}>
            <CartesianGrid stroke="#e2e8f0" vertical={false} />
            <ReferenceLine x="2025-01-06" stroke="#e2e8f0" />
            <ReferenceLine x="2025-05-05" stroke="#e2e8f0" />
            <ReferenceLine x="2025-09-01" stroke="#e2e8f0" />
            <ReferenceLine x="2026-01-20" stroke="#e2e8f0" />
            <XAxis
              dataKey="date"
              minTickGap={80}
              tickFormatter={formatAxisDate}
              tickLine={false}
              axisLine={false}
              tickMargin={18}
              tick={{ fontSize: 13, fill: "#475569" }}
              padding={{ left: 0, right: 0 }}
              interval="preserveStartEnd"
            />
            <YAxis
              domain={["dataMin - 8000", "dataMax + 8000"]}
              tickFormatter={(value) => `$${Math.round(Number(value) / 1000)}k`}
              tickLine={false}
              axisLine={false}
              tick={{ fontSize: 13, fill: "#475569" }}
              width={72}
            />
            <Tooltip formatter={(value) => formatCurrency(Number(value))} />
            <Line type="monotone" dataKey="baseline" name="Baseline" stroke="#2563eb" strokeWidth={2} dot={false} connectNulls />
            <Line type="monotone" dataKey="nlpFiltered" name="NLP filtered" stroke="#059669" strokeWidth={2} dot={false} connectNulls />
            <Line type="monotone" dataKey="spy" name="S&P 500 ETF" stroke="#64748b" strokeWidth={2} dot={false} connectNulls />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
