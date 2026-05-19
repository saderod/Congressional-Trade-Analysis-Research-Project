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
  const answer = newsToneAnswer(totalTrades, averageReturn);
  const evidenceText = evidenceStrengthText(totalTrades, averageReturn);

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
        <p
          className={
            helped
              ? "mt-2 text-3xl font-semibold text-emerald-700"
              : "mt-2 text-3xl font-semibold text-slate-950"
          }
        >
          {answer}
        </p>
        <p className="mt-4 text-sm leading-6 text-slate-600">
          {evidenceText}
        </p>
        <p className="mt-3 text-sm leading-6 text-slate-600">
          {conclusionText(totalTrades, helped)}
        </p>
      </div>
    </section>
  );
}

function newsToneAnswer(totalTrades: number, averageReturn: number): string {
  if (totalTrades === 0) {
    return "No matched news to test";
  }
  if (totalTrades < 10) {
    return averageReturn > 0 ? "Maybe, but too little data" : "No clear evidence";
  }
  return averageReturn > 0 ? "Yes, in this sample" : "No, in this sample";
}

function evidenceStrengthText(totalTrades: number, averageReturn: number): string {
  if (totalTrades === 0) {
    return "No trades had enough matched news to compare with the market.";
  }

  const countLabel = totalTrades < 10 ? `Only ${formatInteger(totalTrades)}` : formatInteger(totalTrades);
  const direction =
    Math.abs(averageReturn) < 0.001 ? "about the same as" : averageReturn > 0 ? "better than" : "worse than";
  const amount =
    Math.abs(averageReturn) < 0.001 ? "" : ` by ${formatPercent(Math.abs(averageReturn), 2)}`;

  return `${countLabel} trades had enough matched news to check. Those trades performed ${direction} the market${amount} about one month later.`;
}

function conclusionText(totalTrades: number, helped: boolean): string {
  if (totalTrades === 0) {
    return "The news data needs to be expanded before this question can be answered.";
  }
  if (totalTrades < 10) {
    return "That is too little data to say the news tone reliably helped predict returns.";
  }
  return helped
    ? "With more matched trades, this would be stronger evidence that news tone helped."
    : "In this sample, news tone did not improve the result.";
}
