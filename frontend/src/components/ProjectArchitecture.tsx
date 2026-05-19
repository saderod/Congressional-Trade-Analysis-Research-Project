import { useState } from "react";

const phases = [
  {
    title: "Collect trades",
    detail: "The pipeline starts by pulling Senate stock-trade disclosures from GovTrades. Each record includes who reported the trade, the ticker, the transaction date, the disclosure date, the trade type, and the reported dollar range. The older Senate Stock Watcher sources stay in the code only as a fallback because they are stale.",
    accent: "border-blue-300",
  },
  {
    title: "Clean trades",
    detail: "The raw disclosures are cleaned into one consistent table. The project keeps usable public stock buys and sells, standardizes ticker symbols, converts transaction and disclosure dates into real date fields, and assigns each trade a stable trade ID so later tables can point back to the same trade.",
    accent: "border-cyan-300",
  },
  {
    title: "Pull prices",
    detail: "For every ticker in the trade universe, the app downloads daily market prices from Yahoo Finance. It also downloads the S&P 500 ETF as the market comparison. These prices let the project measure what happened after each trade became public.",
    accent: "border-emerald-300",
  },
  {
    title: "Pull headlines",
    detail: "The news step downloads recent Yahoo Finance headlines for the same tickers. This is where coverage becomes limited, because Yahoo Finance only provides a recent news window. The project keeps the headline, publisher, link, source, and published time for each item.",
    accent: "border-teal-300",
  },
  {
    title: "Match news",
    detail: "The matching step connects trades to related headlines for the same ticker. It only allows headlines that were published before the congressional disclosure date, so the analysis does not accidentally use future information that investors could not have seen yet.",
    accent: "border-amber-300",
  },
  {
    title: "Score tone",
    detail: "Only the matched headline set is scored, not the entire news table. Three local models contribute: Naive Bayes, FinBERT, and Ollama. Their results are combined into a weighted sentiment score that estimates whether the related news tone was positive, negative, or neutral.",
    accent: "border-violet-300",
  },
  {
    title: "Build features",
    detail: "This phase combines the cleaned trades, price returns, matched headlines, and sentiment scores into the main research table. It calculates post-disclosure returns and excess returns, then stores the final features that power the cards, tables, charts, and backtest.",
    accent: "border-fuchsia-300",
  },
  {
    title: "Summarize findings",
    detail: "The research summaries turn the feature table into plain dashboard numbers. This creates the trade count, buy and sell averages, buy-versus-sell comparison, top senators table, news coverage summary, and the simple yes-or-no style answer for whether news tone helped explain returns.",
    accent: "border-rose-300",
  },
  {
    title: "Run backtest",
    detail: "The backtest simulates what would have happened if the strategy acted after trades became public. It compares a baseline congressional-trade strategy, a news-filtered version that only buys when matched news is positive, and a simple S&P 500 ETF benchmark.",
    accent: "border-orange-300",
  },
  {
    title: "Show dashboard",
    detail: "The final phase serves the saved research outputs through the FastAPI backend and displays them in the React dashboard. The dashboard does not recalculate everything on every page load; it reads the latest generated files and lets you rerun the process when you want fresh results.",
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

          <div className="mt-6 overflow-x-auto">
            <div className="min-w-[1520px] px-8 py-56">
              <div className="flex items-center">
                {phases.map((phase, index) => (
                  <div key={phase.title} className="group relative flex items-center">
                    <button
                      className={`flex h-16 w-16 shrink-0 items-center justify-center rounded-full border-2 bg-white text-base font-semibold text-blue-800 shadow-sm transition group-hover:scale-110 group-hover:shadow-md group-focus-within:scale-110 group-focus-within:shadow-md ${phase.accent}`}
                      type="button"
                    >
                      {index + 1}
                    </button>

                    <div className="absolute left-1/2 top-20 w-28 -translate-x-1/2 text-center">
                      <h3 className="text-xs font-semibold leading-5 text-slate-700">{phase.title}</h3>
                    </div>

                    <article className={`pointer-events-none absolute z-50 w-[38rem] rounded-md border bg-white p-6 text-left opacity-0 shadow-xl transition group-hover:opacity-100 group-focus-within:opacity-100 ${phase.accent} ${panelPlacement(index)}`}>
                      <p className="text-xs font-medium uppercase tracking-wide text-blue-700">Phase {index + 1}</p>
                      <h3 className="mt-1 text-lg font-semibold text-slate-950">{phase.title}</h3>
                      <p className="mt-3 text-sm leading-6 text-slate-600">{phase.detail}</p>
                    </article>

                    {index < phases.length - 1 && (
                      <div className="h-px w-24 shrink-0 bg-blue-300" />
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

function panelPlacement(index: number): string {
  const vertical = index % 2 === 0 ? "bottom-24" : "top-32";
  if (index === 0) {
    return `${vertical} left-0`;
  }
  if (index === phases.length - 1) {
    return `${vertical} right-0`;
  }
  return `${vertical} left-1/2 -translate-x-1/2`;
}
