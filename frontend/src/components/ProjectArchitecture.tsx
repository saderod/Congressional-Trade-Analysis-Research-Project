import { useState } from "react";

const phases = [
  {
    title: "Collect trades",
    detail: "Pull Senate trade disclosures from GovTrades, with legacy sources only as a fallback.",
    accent: "border-blue-300",
  },
  {
    title: "Clean trades",
    detail: "Keep usable stock buys and sells, standardize dates, tickers, and trade IDs.",
    accent: "border-cyan-300",
  },
  {
    title: "Pull prices",
    detail: "Download stock and S&P 500 price history for the tickers in the trade set.",
    accent: "border-emerald-300",
  },
  {
    title: "Pull headlines",
    detail: "Download recent Yahoo Finance headlines for the same ticker universe.",
    accent: "border-teal-300",
  },
  {
    title: "Match news",
    detail: "Attach only headlines published before the trade became public.",
    accent: "border-amber-300",
  },
  {
    title: "Score tone",
    detail: "Use Naive Bayes, FinBERT, and Ollama to rate matched headline tone.",
    accent: "border-violet-300",
  },
  {
    title: "Build features",
    detail: "Combine trades, prices, returns, matched news, and sentiment into one table.",
    accent: "border-fuchsia-300",
  },
  {
    title: "Summarize findings",
    detail: "Create the overview cards, senator table, and news-tone answer.",
    accent: "border-rose-300",
  },
  {
    title: "Run backtest",
    detail: "Simulate the baseline strategy, news-filtered strategy, and S&P 500 comparison.",
    accent: "border-orange-300",
  },
  {
    title: "Show dashboard",
    detail: "Serve the results through FastAPI and display them in the React dashboard.",
    accent: "border-slate-300",
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
        <div className="relative z-20 mt-4 rounded-md border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h2 className="text-lg font-semibold text-slate-950">Project Architecture</h2>
              <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-500">
                The project moves from raw disclosures and market data into cleaned research tables, then turns those results into the dashboard you are viewing.
              </p>
            </div>
            <p className="text-sm font-medium text-blue-700">10 phases</p>
          </div>

          <div className="mt-6 overflow-x-auto overflow-y-visible pb-36">
            <div className="min-w-[1120px] pb-8 pt-6">
              <div className="flex items-center">
                {phases.map((phase, index) => (
                  <div key={phase.title} className="group relative flex items-center">
                    <button
                      className={`flex h-16 w-16 shrink-0 items-center justify-center rounded-full border-2 bg-white text-base font-semibold text-blue-800 shadow-sm transition group-hover:scale-110 group-hover:shadow-md group-focus-within:scale-110 group-focus-within:shadow-md ${phase.accent}`}
                      type="button"
                    >
                      {index + 1}
                    </button>

                    <div className="pointer-events-none absolute left-1/2 top-20 z-50 w-64 -translate-x-1/2 rounded-md border border-slate-200 bg-white p-4 text-left opacity-0 shadow-lg transition group-hover:opacity-100 group-focus-within:opacity-100">
                      <p className="text-xs font-medium uppercase tracking-wide text-blue-700">Phase {index + 1}</p>
                      <h3 className="mt-1 text-sm font-semibold text-slate-950">{phase.title}</h3>
                      <p className="mt-2 text-sm leading-6 text-slate-600">{phase.detail}</p>
                    </div>

                    <div className="absolute left-1/2 top-[4.75rem] w-24 -translate-x-1/2 text-center">
                      <h3 className="text-xs font-semibold leading-5 text-slate-700">{phase.title}</h3>
                    </div>

                    {index < phases.length - 1 && (
                      <div className="h-px w-12 shrink-0 bg-blue-300" />
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
