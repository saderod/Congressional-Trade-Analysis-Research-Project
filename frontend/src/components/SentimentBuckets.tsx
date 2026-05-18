import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fetchSentimentBuckets } from "../lib/api";
import { formatInteger, formatPercent } from "../lib/format";
import { useApi } from "../lib/useApi";
import { ErrorBlock, LoadingBlock } from "./StateBlock";

export function SentimentBuckets() {
  const { data, loading, error } = useApi(fetchSentimentBuckets);

  if (loading) return <LoadingBlock label="sentiment buckets" />;
  if (error || !data) return <ErrorBlock label="sentiment buckets" />;

  const chartData = data.map((row) => ({
    bucket: row.sentiment_bucket.toUpperCase(),
    excessReturn: row.mean_excess_return_21d ?? 0,
    n: row.n,
  }));

  return (
    <section className="rounded-md border border-slate-200 bg-white p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-950">Sentiment Buckets</h2>
          <p className="mt-1 text-sm text-slate-500">Mean 21d excess return by sentiment quintile</p>
        </div>
      </div>
      <div className="mt-5 h-72">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 12, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#e2e8f0" vertical={false} />
            <XAxis dataKey="bucket" tickLine={false} axisLine={false} />
            <YAxis tickFormatter={(value) => formatPercent(Number(value), 0)} tickLine={false} axisLine={false} width={56} />
            <Tooltip
              formatter={(value, name) => [formatPercent(Number(value), 2), name === "excessReturn" ? "Excess return" : name]}
              labelFormatter={(label) => `${label} (${formatInteger(chartData.find((row) => row.bucket === label)?.n)} trades)`}
            />
            <Bar dataKey="excessReturn" fill="#2563eb" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
