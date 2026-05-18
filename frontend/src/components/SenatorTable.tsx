import { useMemo, useState } from "react";
import { fetchSenators, SenatorRow } from "../lib/api";
import { formatInteger, formatPercent } from "../lib/format";
import { useApi } from "../lib/useApi";
import { ErrorBlock, LoadingBlock } from "./StateBlock";

type SortKey = "mean_excess_return_21d" | "n" | "senator";

export function SenatorTable() {
  const { data, loading, error } = useApi(fetchSenators);
  const [sortKey, setSortKey] = useState<SortKey>("mean_excess_return_21d");
  const [descending, setDescending] = useState(true);

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
      <h2 className="text-lg font-semibold text-slate-950">Top Senators</h2>
      <div className="mt-5 overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <SortableHeader label="Senator" active={sortKey === "senator"} descending={descending} onClick={() => setSort("senator")} />
              <SortableHeader label="Trades" active={sortKey === "n"} descending={descending} onClick={() => setSort("n")} />
              <SortableHeader label="Mean excess" active={sortKey === "mean_excess_return_21d"} descending={descending} onClick={() => setSort("mean_excess_return_21d")} />
              <th className="py-3 font-medium">95% CI</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {sortedRows.map((row) => (
              <tr key={row.senator}>
                <td className="max-w-[24rem] truncate py-3 pr-5 font-medium text-slate-950">{row.senator}</td>
                <td className="py-3 pr-5 text-slate-700">{formatInteger(row.n)}</td>
                <td className="py-3 pr-5 text-slate-700">{formatPercent(row.mean_excess_return_21d, 2)}</td>
                <td className="py-3 text-slate-700">
                  {formatPercent(row.ci_low, 2)} to {formatPercent(row.ci_high, 2)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function SortableHeader({
  label,
  active,
  descending,
  onClick,
}: {
  label: string;
  active: boolean;
  descending: boolean;
  onClick: () => void;
}) {
  return (
    <th className="py-3 pr-5 font-medium">
      <button className="inline-flex items-center gap-1 text-left hover:text-slate-900" onClick={onClick} type="button">
        {label}
        <span className="text-slate-400">{active ? (descending ? "↓" : "↑") : "↕"}</span>
      </button>
    </th>
  );
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
