import { fetchNlpRouting } from "../lib/api";
import { formatInteger, formatNumber, formatPercentValue } from "../lib/format";
import { useApi } from "../lib/useApi";
import { ErrorBlock, LoadingBlock } from "./StateBlock";

const labels: Record<string, string> = {
  ensemble: "Base ensemble",
  ensemble_ollama: "Ollama assisted",
  ensemble_fallback: "Fallback",
};

const colors: Record<string, string> = {
  ensemble: "bg-blue-600",
  ensemble_ollama: "bg-emerald-600",
  ensemble_fallback: "bg-amber-500",
};

export function NlpRoutingCard() {
  const { data, loading, error } = useApi(fetchNlpRouting);

  if (loading) return <LoadingBlock label="NLP routing" />;
  if (error || !data) return <ErrorBlock label="NLP routing" />;

  const entries = Object.entries(data.percentages).filter(([, value]) => value > 0);

  return (
    <section className="rounded-md border border-slate-200 bg-white p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-950">NLP Ensemble Routing</h2>
          <p className="mt-1 text-sm text-slate-500">
            {formatInteger(data.checked_news)} checked headlines from {formatInteger(data.retrieval_rows)} retrieval rows
          </p>
        </div>
        <div className="text-right">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">LLM time</p>
          <p className="mt-1 text-2xl font-semibold text-slate-950">{formatNumber(data.llm_elapsed_seconds, 1)}s</p>
        </div>
      </div>

      <div className="mt-6 flex h-5 overflow-hidden rounded-sm bg-slate-100">
        {entries.map(([key, value]) => (
          <div
            key={key}
            className={colors[key] ?? "bg-slate-400"}
            style={{ width: `${value}%` }}
            title={`${labels[key] ?? key}: ${formatPercentValue(value, 1)}`}
          />
        ))}
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        {entries.map(([key, value]) => (
          <div key={key} className="flex items-center justify-between gap-3 text-sm">
            <span className="flex min-w-0 items-center gap-2 text-slate-600">
              <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${colors[key] ?? "bg-slate-400"}`} />
              <span className="truncate">{labels[key] ?? key}</span>
            </span>
            <span className="font-medium text-slate-950">
              {formatPercentValue(value, 1)} ({formatInteger(data.counts[key])})
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
