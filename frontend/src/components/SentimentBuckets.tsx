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
  const totalTrades = chartData.reduce((sum, row) => sum + row.n, 0);
  const averageReturn =
    totalTrades > 0
      ? chartData.reduce((sum, row) => sum + row.excessReturn * row.n, 0) / totalTrades
      : 0;
  const helped = averageReturn > 0;
  const answer = helped ? "Yes, but the evidence is thin" : "No clear evidence";

  return (
    <section className="rounded-md border border-slate-200 bg-white p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-950">Did News Tone Help Explain Returns?</h2>
          <p className="mt-1 text-sm text-slate-500">
            Simple answer based on the trades that had matched news.
          </p>
        </div>
      </div>

      <div className="mt-5 rounded-md border border-slate-200 bg-slate-50 p-5">
        <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Answer</p>
        <p className={helped ? "mt-2 text-3xl font-semibold text-emerald-700" : "mt-2 text-3xl font-semibold text-slate-950"}>
          {answer}
        </p>
        <p className="mt-4 text-sm leading-6 text-slate-600">
          Only {formatInteger(totalTrades)} trades had enough matched news to check. Those trades performed{" "}
          {formatPercent(Math.abs(averageReturn), 2)} {helped ? "better" : "worse"} than the market about one month later.
        </p>
        <p className="mt-3 text-sm leading-6 text-slate-600">
          That is too little data to say the news tone reliably helped predict returns.
        </p>
      </div>
    </section>
  );
}
