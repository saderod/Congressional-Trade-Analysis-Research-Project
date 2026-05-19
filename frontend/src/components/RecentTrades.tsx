import { useState } from "react";
import { fetchRecentTrades } from "../lib/api";
import { formatCurrency, formatPercent } from "../lib/format";
import { useApi } from "../lib/useApi";
import { ErrorBlock, LoadingBlock } from "./StateBlock";

export function RecentTrades() {
  const { data, loading, error } = useApi(() => fetchRecentTrades(20));
  const [expanded, setExpanded] = useState(false);

  if (loading) return <LoadingBlock label="recent trades" />;
  if (error || !data) return <ErrorBlock label="recent trades" />;

  return (
    <section className="rounded-md border border-slate-200 bg-white p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-950">Recent Trades</h2>
          <p className="mt-1 text-sm leading-6 text-slate-500">
            The newest reported trades in the current research set.
          </p>
        </div>
        <button
          className="rounded-md border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:border-blue-300 hover:text-blue-700"
          onClick={() => setExpanded((current) => !current)}
          type="button"
        >
          {expanded ? "Collapse" : "Expand"}
        </button>
      </div>
      <div className={`mt-5 divide-y divide-slate-100 overflow-y-auto pr-2 ${expanded ? "max-h-[42rem]" : "max-h-80"}`}>
        {data.map((trade) => (
          <article key={trade.trade_id} className="grid gap-3 py-4 first:pt-0 last:pb-0 md:grid-cols-[1fr_1.6fr]">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-semibold text-slate-950">{trade.ticker}</span>
                <span className={trade.type === "buy" ? "text-sm font-medium text-emerald-700" : "text-sm font-medium text-slate-600"}>
                  {trade.type.toUpperCase()}
                </span>
                <span className="text-sm text-slate-500">{trade.disclosure_date}</span>
              </div>
              <p className="mt-1 truncate text-sm text-slate-600">{trade.senator}</p>
              <p className="mt-2 text-sm text-slate-500">
                Entry {formatCurrency(trade.entry_price)} - 21d excess {formatPercent(trade.excess_return_21d, 2)}
              </p>
            </div>
            <div>
              <p className="line-clamp-2 text-sm font-medium text-slate-800">{trade.top_news_headline ?? "No matched pre-disclosure headline"}</p>
              <p className="mt-2 text-sm text-slate-500">
                Sentiment {formatPercent(trade.top_news_sentiment, 1)} - similarity {trade.top_news_similarity?.toFixed(2) ?? "NA"}
              </p>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
