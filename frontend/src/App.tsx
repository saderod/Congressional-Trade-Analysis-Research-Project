import { EquityCurveChart } from "./components/EquityCurveChart";
import { MethodologyNotes } from "./components/MethodologyNotes";
import { MetricsTable } from "./components/MetricsTable";
import { NlpRoutingCard } from "./components/NlpRoutingCard";
import { OverviewCards } from "./components/OverviewCards";
import { RecentTrades } from "./components/RecentTrades";
import { SenatorTable } from "./components/SenatorTable";
import { SentimentBuckets } from "./components/SentimentBuckets";

export default function App() {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-7xl px-5 py-8 sm:px-8 lg:py-10">
        <header className="flex flex-col gap-5 border-b border-slate-200 pb-8 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-sm font-medium uppercase tracking-wide text-blue-700">congressional-alpha</p>
            <h1 className="mt-3 max-w-4xl text-4xl font-semibold tracking-normal text-slate-950 md:text-5xl">
              Congressional Trading Signal Dashboard
            </h1>
            <p className="mt-4 max-w-3xl text-base leading-7 text-slate-600">
              A local research view of post-disclosure trade signals, headline retrieval, NLP ensemble routing, and realized 21-day excess returns.
            </p>
          </div>
          <a
            className="inline-flex w-fit items-center justify-center rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:border-blue-500 hover:text-blue-700"
            href="https://github.com/"
            rel="noreferrer"
            target="_blank"
          >
            GitHub
          </a>
        </header>

        <div className="mt-8 space-y-6">
          <OverviewCards />
          <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
            <NlpRoutingCard />
            <SentimentBuckets />
          </div>
          <EquityCurveChart />
          <MetricsTable />
          <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
            <SenatorTable />
            <RecentTrades />
          </div>
          <MethodologyNotes />
        </div>
      </div>
    </main>
  );
}
