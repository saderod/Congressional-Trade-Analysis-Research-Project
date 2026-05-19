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

          <div className="mt-6 overflow-x-auto pb-2">
            <div className="grid min-w-[1120px] grid-cols-[repeat(10,minmax(0,1fr))] items-stretch gap-0">
            {phases.map((phase, index) => (
              <div key={phase.title} className="flex items-center">
                <div className={`min-h-44 w-full rounded-md border-2 bg-white p-3 shadow-sm ${phase.accent}`}>
                  <div className="flex items-center gap-2">
                    <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-sm bg-blue-700 text-xs font-semibold text-white">
                      {index + 1}
                    </span>
                    <h3 className="text-sm font-semibold text-slate-950">{phase.title}</h3>
                  </div>
                  <p className="mt-3 text-xs leading-5 text-slate-600">{phase.detail}</p>
                </div>
                {index < phases.length - 1 && (
                  <div className="flex h-px w-8 shrink-0 items-center bg-blue-300">
                    <span className="ml-auto h-2 w-2 rotate-45 border-r-2 border-t-2 border-blue-500 bg-white" />
                  </div>
                )}
              </div>
            ))}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
