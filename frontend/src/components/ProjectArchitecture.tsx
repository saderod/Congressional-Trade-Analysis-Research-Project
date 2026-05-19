import { useState } from "react";

const phases = [
  {
    title: "Collect trades",
    detail: "Pull Senate trade disclosures from GovTrades, with legacy sources only as a fallback.",
    accent: "border-blue-200 bg-blue-50 text-blue-800",
  },
  {
    title: "Clean trades",
    detail: "Keep usable stock buys and sells, standardize dates, tickers, and trade IDs.",
    accent: "border-cyan-200 bg-cyan-50 text-cyan-800",
  },
  {
    title: "Pull prices",
    detail: "Download stock and S&P 500 price history for the tickers in the trade set.",
    accent: "border-emerald-200 bg-emerald-50 text-emerald-800",
  },
  {
    title: "Pull headlines",
    detail: "Download recent Yahoo Finance headlines for the same ticker universe.",
    accent: "border-teal-200 bg-teal-50 text-teal-800",
  },
  {
    title: "Match news",
    detail: "Attach only headlines published before the trade became public.",
    accent: "border-amber-200 bg-amber-50 text-amber-800",
  },
  {
    title: "Score tone",
    detail: "Use Naive Bayes, FinBERT, and Ollama to rate matched headline tone.",
    accent: "border-violet-200 bg-violet-50 text-violet-800",
  },
  {
    title: "Build features",
    detail: "Combine trades, prices, returns, matched news, and sentiment into one table.",
    accent: "border-fuchsia-200 bg-fuchsia-50 text-fuchsia-800",
  },
  {
    title: "Summarize findings",
    detail: "Create the overview cards, senator table, and news-tone answer.",
    accent: "border-rose-200 bg-rose-50 text-rose-800",
  },
  {
    title: "Run backtest",
    detail: "Simulate the baseline strategy, news-filtered strategy, and S&P 500 comparison.",
    accent: "border-orange-200 bg-orange-50 text-orange-800",
  },
  {
    title: "Show dashboard",
    detail: "Serve the results through FastAPI and display them in the React dashboard.",
    accent: "border-slate-200 bg-slate-50 text-slate-800",
  },
];

export function ProjectArchitecture() {
  const [open, setOpen] = useState(false);

  return (
    <section>
      <button
        aria-expanded={open}
        className="inline-flex items-center justify-center rounded-md bg-blue-700 px-5 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-blue-800"
        onClick={() => setOpen((current) => !current)}
        type="button"
      >
        Project Architecture
      </button>

      {open && (
        <div className="mt-4 rounded-md border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h2 className="text-lg font-semibold text-slate-950">Project Architecture</h2>
              <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-500">
                The project moves from raw disclosures and market data into cleaned research tables, then turns those results into the dashboard you are viewing.
              </p>
            </div>
            <p className="text-sm font-medium text-blue-700">10 phases</p>
          </div>

          <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
            {phases.map((phase, index) => (
              <div key={phase.title} className={`relative rounded-md border p-4 ${phase.accent}`}>
                <div className="flex items-center gap-3">
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white text-sm font-semibold shadow-sm">
                    {index + 1}
                  </span>
                  <h3 className="text-sm font-semibold">{phase.title}</h3>
                </div>
                <p className="mt-3 text-sm leading-6 text-slate-700">{phase.detail}</p>
                {index < phases.length - 1 && (
                  <span className="mt-3 hidden text-xs font-semibold uppercase tracking-wide text-slate-400 xl:block">
                    next
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
