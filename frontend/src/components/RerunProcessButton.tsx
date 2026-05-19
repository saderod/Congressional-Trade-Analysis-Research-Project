import { useEffect, useState } from "react";
import { fetchRerunStatus, RerunStatus, startRerun } from "../lib/api";

export function RerunProcessButton() {
  const [status, setStatus] = useState<RerunStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    if (!status?.running) {
      return undefined;
    }

    const pollStatus = () => {
      fetchRerunStatus()
        .then((nextStatus) => {
          if (active) {
            setStatus(nextStatus);
          }
        })
        .catch((requestError: unknown) => {
          if (active) {
            setError(requestError instanceof Error ? requestError.message : "Could not check rerun status");
          }
        });
    };
    pollStatus();
    const interval = window.setInterval(pollStatus, 1000);

    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, [status?.running]);

  const handleRerun = async () => {
    setError(null);
    try {
      const nextStatus = await startRerun();
      setStatus(nextStatus);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Could not start rerun");
    }
  };

  const isRunning = status?.running ?? false;
  const progress = getProgress(status);
  const statusText = error ?? status?.activity ?? status?.message ?? "Refreshes the local analysis files used by this dashboard.";

  return (
    <section className="flex flex-col items-center gap-3 py-4 text-center">
      <button
        className="rounded-md bg-blue-700 px-5 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-blue-800 disabled:cursor-not-allowed disabled:bg-slate-400"
        disabled={isRunning}
        onClick={handleRerun}
        type="button"
      >
        {isRunning ? "Re-running process..." : "Re-run process"}
      </button>
      {(isRunning || status?.success !== null) && (
        <div className="w-full max-w-xl">
          <div className="mb-1 flex items-center justify-between text-xs font-medium text-slate-500">
            <span>{status?.step ?? "Ready"}</span>
            <span>{progress}%</span>
          </div>
          <div className="h-2 overflow-hidden rounded-sm bg-slate-200">
            <div className="h-full rounded-sm bg-blue-700 transition-all" style={{ width: `${progress}%` }} />
          </div>
        </div>
      )}
      <p className={error ? "max-w-xl text-sm text-red-700" : "max-w-xl text-sm text-slate-500"}>
        {statusText}
      </p>
    </section>
  );
}

function getProgress(status: RerunStatus | null): number {
  const explicitProgress = Number(status?.progress);
  if (Number.isFinite(explicitProgress)) {
    return Math.max(0, Math.min(100, Math.round(explicitProgress)));
  }

  if (!status) {
    return 0;
  }

  const step = status.step.toLowerCase();
  if (status.success === true || step.includes("complete")) return 100;
  if (status.success === false || step.includes("failed")) return 0;
  if (step.includes("queued") || step.includes("waiting")) return 5;
  if (step.includes("reading") || step.includes("pulling")) return 10;
  if (step.includes("scoring") || step.includes("analyzing") || step.includes("news")) return 30;
  if (step.includes("feature") || step.includes("matching")) return 55;
  if (step.includes("summar") || step.includes("dashboard")) return 75;
  if (step.includes("portfolio") || step.includes("backtest")) return 90;
  return status.running ? 5 : 0;
}
