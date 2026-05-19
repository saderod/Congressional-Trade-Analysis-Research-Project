import { useMemo, useState } from "react";
import { fetchSenators, SenatorRow } from "../lib/api";
import { formatInteger, formatPercent } from "../lib/format";
import { useApi } from "../lib/useApi";
import { ErrorBlock, LoadingBlock } from "./StateBlock";

type SortKey = "mean_excess_return_21d" | "n" | "senator";

const columnAccents = {
  senator: "text-slate-700",
  trades: "text-blue-700",
  mean: "text-emerald-700",
  uncertainty: "text-amber-700",
};

export function SenatorTable() {
  const { data, loading, error } = useApi(fetchSenators);
  const [sortKey, setSortKey] = useState<SortKey>("mean_excess_return_21d");
  const [descending, setDescending] = useState(true);
  const [expanded, setExpanded] = useState(false);

  const sortedRows = useMemo(() => {
    return [...(data ?? [])].sort((a, b) => compareRows(a, b, sortKey, descending));
  }, [data, sortKey, descending]);

  if (loading) return <LoadingBlock label="senator table" />;
  if (error || !data) return <ErrorBlock label="senator table" />;

  const setSort = (key: SortKey) => {
    if (key === sortKey) {
      setDescending((current) => !current);
    } else {
      setSortKey(key);
      setDescending(key !== "senator");
    }
  };

  return (
    <section className="rounded-md border border-slate-200 bg-white p-6">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <h2 className="text-lg font-semibold text-slate-950">Top Senators</h2>
          <p className="mt-1 text-sm leading-6 text-slate-500">
            This summarizes how each senator's reported trades performed compared with the market about one month later.
          </p>
        </div>
        <button
          className="ml-auto shrink-0 rounded-md border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:border-blue-300 hover:text-blue-700"
          onClick={() => setExpanded((current) => !current)}
          type="button"
        >
          {expanded ? "Collapse" : "Expand"}
        </button>
      </div>

      <div className={`mt-5 overflow-auto rounded-md border border-slate-100 ${expanded ? "max-h-[34rem]" : "max-h-56"}`}>
        <table className="min-w-full text-left text-sm">
          <thead className="sticky top-0 z-10 border-b border-slate-200 bg-white text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <SortableHeader label="Senator" accent={columnAccents.senator} active={sortKey === "senator"} descending={descending} onClick={() => setSort("senator")} />
              <SortableHeader label="Trades" accent={columnAccents.trades} active={sortKey === "n"} descending={descending} onClick={() => setSort("n")} />
              <SortableHeader label="Mean excess" accent={columnAccents.mean} active={sortKey === "mean_excess_return_21d"} descending={descending} onClick={() => setSort("mean_excess_return_21d")} />
              <th className={`py-3 font-medium ${columnAccents.uncertainty}`}>Uncertainty range</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {sortedRows.map((row) => {
              const uncertainty = classifyUncertainty(row);
              return (
                <tr key={row.senator}>
                  <td className="max-w-[24rem] truncate py-3 pr-5 font-medium text-slate-950">{row.senator}</td>
                  <td className={`py-3 pr-5 font-medium ${columnAccents.trades}`}>{formatInteger(row.n)}</td>
                  <td className={`py-3 pr-5 font-medium ${columnAccents.mean}`}>{formatPercent(row.mean_excess_return_21d, 2)}</td>
                  <td className="py-3 text-slate-700">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={`font-medium ${columnAccents.uncertainty}`}>
                        {formatPercent(row.ci_low, 2)} to {formatPercent(row.ci_high, 2)}
                      </span>
                      <span className={`rounded-sm px-2 py-0.5 text-xs font-medium ${uncertainty.className}`}>
                        {uncertainty.label}
                      </span>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="mt-5 grid gap-3 border-t border-slate-100 pt-4 text-sm leading-6 text-slate-600 md:grid-cols-2">
        <p>
          <span className={`font-medium ${columnAccents.trades}`}>Trades:</span> how many reported trades are included for that senator.
        </p>
        <p>
          <span className={`font-medium ${columnAccents.mean}`}>Mean excess:</span> how much those trades beat or trailed the market on average.
        </p>
        <p>
          <span className={`font-medium ${columnAccents.uncertainty}`}>Uncertainty range:</span> reliable means the range is tighter; uncertain means the range is wider.
        </p>
        <p>
          <span className={`font-medium ${columnAccents.uncertainty}`}>Reliable or uncertain:</span> uncertain usually means there are fewer trades or more uneven results.
        </p>
      </div>
    </section>
  );
}

function SortableHeader({
  label,
  accent,
  active,
  descending,
  onClick,
}: {
  label: string;
  accent: string;
  active: boolean;
  descending: boolean;
  onClick: () => void;
}) {
  return (
    <th className="py-3 pr-5 font-medium">
      <button className={`inline-flex items-center gap-1 text-left hover:text-slate-900 ${accent}`} onClick={onClick} type="button">
        {label}
        <span className="text-slate-400">{active ? (descending ? "v" : "^") : "-"}</span>
      </button>
    </th>
  );
}

function classifyUncertainty(row: SenatorRow): { label: string; className: string } {
  if (row.ci_low === null || row.ci_high === null) {
    return { label: "Unknown", className: "bg-slate-100 text-slate-600" };
  }

  const width = row.ci_high - row.ci_low;
  if (width <= 0.08) {
    return { label: "Reliable", className: "bg-emerald-50 text-emerald-700" };
  }
  return { label: "Uncertain", className: "bg-amber-50 text-amber-700" };
}

function compareRows(a: SenatorRow, b: SenatorRow, key: SortKey, descending: boolean): number {
  const direction = descending ? -1 : 1;
  if (key === "senator") {
    return a.senator.localeCompare(b.senator) * direction;
  }
  const av = a[key] ?? Number.NEGATIVE_INFINITY;
  const bv = b[key] ?? Number.NEGATIVE_INFINITY;
  return (av - bv) * direction;
}
