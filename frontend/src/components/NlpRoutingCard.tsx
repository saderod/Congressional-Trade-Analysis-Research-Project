import { fetchNlpRouting } from "../lib/api";
import { formatInteger, formatNumber } from "../lib/format";
import { useApi } from "../lib/useApi";
import { ErrorBlock, LoadingBlock } from "./StateBlock";

export function NlpRoutingCard() {
  const { data, loading, error } = useApi(fetchNlpRouting);

  if (loading) return <LoadingBlock label="NLP routing" />;
  if (error || !data) return <ErrorBlock label="NLP routing" />;

  const allModelCount = data.counts.ensemble_all_models ?? 0;
  const fallbackCount = data.counts.ensemble_fallback ?? 0;

  return (
    <section className="rounded-md border border-slate-200 bg-white p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-950">
            Related Congressional News Headline Sentiment Analysis
          </h2>
          <p className="mt-1 text-sm text-slate-500">{formatInteger(data.checked_news)} headlines analyzed.</p>
        </div>
        <div className="text-right">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Processing time</p>
          <p className="mt-1 text-2xl font-semibold text-slate-950">{formatNumber(data.llm_elapsed_seconds, 1)}s</p>
        </div>
      </div>

      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        <div className="rounded-md border border-slate-200 bg-slate-50 p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Normal process</p>
          <p className="mt-2 text-sm font-medium text-slate-950">{formatInteger(allModelCount)} headlines</p>
        </div>
        <div className="rounded-md border border-slate-200 bg-slate-50 p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Fallbacks</p>
          <p className="mt-2 text-sm font-medium text-slate-950">{formatInteger(fallbackCount)} headlines</p>
        </div>
      </div>
    </section>
  );
}
