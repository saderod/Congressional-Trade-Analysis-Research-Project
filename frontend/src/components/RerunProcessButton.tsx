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

    const interval = window.setInterval(() => {
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
    }, 2500);

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
  const statusText = error ?? status?.message ?? "Refreshes the local analysis files used by this dashboard.";

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
      <p className={error ? "max-w-xl text-sm text-red-700" : "max-w-xl text-sm text-slate-500"}>
        {isRunning && status?.step ? `${status.step}: ` : ""}
        {statusText}
      </p>
    </section>
  );
}
