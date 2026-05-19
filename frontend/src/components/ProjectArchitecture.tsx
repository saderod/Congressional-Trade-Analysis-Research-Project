import { useState } from "react";

const phases = [
  {
    title: "Collect trades",
    simple: "The app first gathers the congressional stock trades that will be studied.",
    technical: "The ingest step pulls Senate trade disclosures from GovTrades and normalizes the raw fields used later in the pipeline: senator, ticker, transaction date, disclosure date, trade type, amount range, asset type, source, and PTR link. Legacy Senate Stock Watcher URLs remain in the code as a fallback, but the active source is GovTrades because the old snapshots are stale.",
    accent: "border-blue-300",
  },
  {
    title: "Clean trades",
    simple: "Messy disclosure records are turned into one clean trade table.",
    technical: "The cleaning step keeps public stock buy and sell rows, removes unusable ticker shapes, standardizes tickers, converts transaction_date and disclosure_date into date fields, and creates a stable trade_id. That trade_id persists through parquet and DuckDB so retrieval, feature, and dashboard tables can safely reference the same trade.",
    accent: "border-cyan-300",
  },
  {
    title: "Pull prices",
    simple: "The app downloads stock prices so it can see what happened after each trade became public.",
    technical: "For every ticker in the cleaned trade universe, the price ingest downloads daily OHLCV history from Yahoo Finance. It also downloads SPY as the market benchmark. Prices are aligned to the first market session after disclosure, which prevents the backtest from acting before the public disclosure was available.",
    accent: "border-emerald-300",
  },
  {
    title: "Pull headlines",
    simple: "The app collects recent news headlines for the same stocks.",
    technical: "The news ingest queries Yahoo Finance by ticker and stores headline, summary, publisher, URL, source, and published_at in UTC. This source has a limited recent-news window, so the project's effective news coverage is much smaller than the full trade history.",
    accent: "border-teal-300",
  },
  {
    title: "Match news",
    simple: "Each trade is matched only with news that existed before the trade was disclosed.",
    technical: "The retrieval step embeds headlines and links them to trade rows by ticker and similarity. It enforces a strict pre-disclosure cutoff, so a trade can only use headlines with published_at earlier than the disclosure timestamp. That rule is the main lookahead-control guardrail for the NLP features.",
    accent: "border-amber-300",
  },
  {
    title: "Score tone",
    simple: "The app estimates whether matched news sounded positive, negative, or neutral.",
    technical: "The ensemble only scores unique news_ids found in trade_news_retrieval.parquet, not the full news table. Naive Bayes, FinBERT, and Ollama each vote on the scoped headline set. Their weighted output becomes the sentiment label, confidence, and numeric score used by downstream features.",
    accent: "border-violet-300",
  },
  {
    title: "Build features",
    simple: "The cleaned trades, prices, and news scores are combined into one research table.",
    technical: "The feature build joins cleaned trades, adjusted price returns, retrieval rows, sentiment outputs, and benchmark returns. It calculates forward 21-trading-day returns, excess returns versus SPY, headline counts, top matched headline fields, and sentiment aggregates that power the dashboard.",
    accent: "border-fuchsia-300",
  },
  {
    title: "Summarize findings",
    simple: "The app turns the research table into readable dashboard takeaways.",
    technical: "The research scripts aggregate the feature table into JSON artifacts for the API. They compute total trades, coverage, buy and sell averages, t-test values, senator-level confidence ranges, sentiment coverage, and the yes-or-no style news-tone summary.",
    accent: "border-rose-300",
  },
  {
    title: "Run backtest",
    simple: "The app simulates how a simple strategy would have performed after disclosures became public.",
    technical: "The backtest compares three paths: a baseline congressional-trade strategy, an NLP-filtered strategy that only buys when matched news tone is positive, and a buy-and-hold SPY benchmark. It records equity curves, total return, annualized return, volatility, Sharpe, drawdown, hit rate, and trade count.",
    accent: "border-orange-300",
  },
  {
    title: "Show dashboard",
    simple: "The final results are shown in the web dashboard.",
    technical: "FastAPI serves the saved parquet and JSON outputs through dashboard endpoints. React fetches those endpoints and renders the overview cards, NLP summary, news-tone answer, simulated portfolio chart, backtest metrics, senator table, recent trades, rerun control, and this architecture view.",
    accent: "border-slate-300",
  },
];

export function ProjectArchitecture() {
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const activePhase = phases[activeIndex];

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
            <div className="min-w-[1520px] px-8 pb-10 pt-6">
              <div className="flex items-center">
                {phases.map((phase, index) => (
                  <div key={phase.title} className="relative flex items-center">
                    <button
                      className={`flex h-16 w-16 shrink-0 items-center justify-center rounded-full border-2 bg-white text-base font-semibold text-blue-800 shadow-sm transition hover:scale-110 hover:shadow-md focus:scale-110 focus:shadow-md ${phase.accent} ${activeIndex === index ? "ring-4 ring-blue-100" : ""}`}
                      onFocus={() => setActiveIndex(index)}
                      onMouseEnter={() => setActiveIndex(index)}
                      type="button"
                    >
                      {index + 1}
                    </button>

                    <div className="absolute left-1/2 top-20 w-28 -translate-x-1/2 text-center">
                      <h3 className="text-xs font-semibold leading-5 text-slate-700">{phase.title}</h3>
                    </div>

                    {index < phases.length - 1 && (
                      <div className="h-px w-24 shrink-0 bg-blue-300" />
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>

          <article className={`mt-4 rounded-md border bg-white p-6 shadow-sm ${activePhase.accent}`}>
            <div className="flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-blue-700">Phase {activeIndex + 1}</p>
                <h3 className="mt-1 text-xl font-semibold text-slate-950">{activePhase.title}</h3>
              </div>
              <p className="text-sm font-medium text-slate-500">Hover a node to update this panel</p>
            </div>
            <div className="mt-5 grid gap-6 lg:grid-cols-[0.75fr_1.25fr]">
              <div>
                <h4 className="text-sm font-semibold text-slate-950">Simple explanation</h4>
                <p className="mt-2 text-base leading-7 text-slate-700">{activePhase.simple}</p>
              </div>
              <div>
                <h4 className="text-sm font-semibold text-slate-950">Developer explanation</h4>
                <p className="mt-2 text-sm leading-6 text-slate-600">{activePhase.technical}</p>
              </div>
            </div>
          </article>
        </div>
      )}
    </section>
  );
}
