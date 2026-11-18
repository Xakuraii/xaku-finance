import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { LineChart, Table as TableIcon } from "lucide-react";
import { fetchNetWorthHistory } from "../api/analytics-api";
import { NetWorthHistoryResponse } from "../types";

interface NetWorthChartProps {
  initialData?: NetWorthHistoryResponse;
  currency?: string;
}

export const NetWorthChart: React.FC<NetWorthChartProps> = ({
  initialData,
  currency,
}) => {
  const [granularity, setGranularity] = useState<"month" | "week" | "day">("month");
  const [viewMode, setViewMode] = useState<"chart" | "table">("chart");

  const { data, isLoading } = useQuery<NetWorthHistoryResponse>({
    queryKey: ["analytics", "net-worth-history", granularity, currency],
    queryFn: () => fetchNetWorthHistory({ granularity, currency }),
    initialData,
  });

  const series = data?.series || [];
  const tableData = data?.table || [];
  const displayCurrency = data?.currency || currency || "USD";

  // Compute max value for bar scaling
  const values = series.map((s) => parseFloat(s.net_worth) || 0);
  const maxVal = Math.max(...values, 100);
  const minVal = Math.min(...values, 0);
  const range = maxVal - minVal || 1;

  return (
    <div className="rounded-xl border border-[#2b313a] bg-[#181a20] p-6 shadow-sm">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#2b313a] pb-4 mb-5">
        <div>
          <h3 className="text-sm font-semibold text-white tracking-tight flex items-center gap-2">
            <LineChart className="w-4 h-4 text-amber-400" />
            Net Worth Trend
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Historical balance curve across accounting periods
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Granularity Selector */}
          <div className="flex items-center rounded-lg border border-[#2b313a] bg-slate-900/60 p-0.5 text-xs">
            {(["month", "week", "day"] as const).map((g) => (
              <button
                key={g}
                type="button"
                onClick={() => setGranularity(g)}
                className={`px-2.5 py-1 rounded font-medium capitalize transition-colors cursor-pointer ${
                  granularity === g
                    ? "bg-amber-400 text-black font-semibold"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                {g}
              </button>
            ))}
          </div>

          {/* Chart / Table View Mode Switcher */}
          <div className="flex items-center rounded-lg border border-[#2b313a] bg-slate-900/60 p-0.5 text-xs">
            <button
              type="button"
              onClick={() => setViewMode("chart")}
              aria-label="View trend chart"
              className={`p-1.5 rounded transition-colors cursor-pointer ${
                viewMode === "chart"
                  ? "bg-slate-800 text-amber-400"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              <LineChart className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={() => setViewMode("table")}
              aria-label="View accessible data table"
              className={`p-1.5 rounded transition-colors cursor-pointer ${
                viewMode === "table"
                  ? "bg-slate-800 text-amber-400"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              <TableIcon className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {isLoading && !data ? (
        <div className="h-48 flex items-center justify-center text-slate-500 text-xs animate-pulse">
          Loading historical curve...
        </div>
      ) : series.length === 0 ? (
        <div className="h-48 flex items-center justify-center text-slate-500 text-xs">
          No historical net worth snapshots available yet.
        </div>
      ) : viewMode === "chart" ? (
        /* Visual Chart View */
        <div className="space-y-4">
          <div className="h-48 flex items-end gap-2 pt-6 pb-2 px-1 border-b border-slate-800">
            {series.map((point) => {
              const val = parseFloat(point.net_worth) || 0;
              const heightPct = Math.max(8, Math.min(100, ((val - minVal) / range) * 100));
              const isNeg = val < 0;

              return (
                <div
                  key={point.date}
                  className="flex-1 flex flex-col items-center gap-1 group relative h-full justify-end"
                >
                  {/* Tooltip */}
                  <div className="absolute -top-10 opacity-0 group-hover:opacity-100 transition-opacity bg-slate-950 border border-slate-700 rounded px-2 py-1 text-[11px] font-mono text-white pointer-events-none whitespace-nowrap z-10 shadow-lg">
                    {point.date}: {point.net_worth} {displayCurrency}
                  </div>

                  {/* Bar */}
                  <div
                    style={{ height: `${heightPct}%` }}
                    className={`w-full max-w-[32px] rounded-t transition-all ${
                      isNeg
                        ? "bg-rose-500/60 hover:bg-rose-400"
                        : "bg-amber-400/80 hover:bg-amber-300"
                    }`}
                  />
                  <span className="text-[10px] text-slate-400 font-mono truncate max-w-[40px]">
                    {point.date.slice(5)}
                  </span>
                </div>
              );
            })}
          </div>
          <div className="flex justify-between text-[11px] text-slate-500">
            <span>Historical series ({series.length} data points)</span>
            <span>All values in {displayCurrency}</span>
          </div>
        </div>
      ) : (
        /* Accessible Fallback Data Table */
        <div className="overflow-x-auto">
          <table
            className="w-full text-left text-xs"
            aria-label="Net Worth History Data Table"
          >
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 uppercase tracking-wider text-[10px]">
                <th className="py-2 px-3 font-semibold">Date</th>
                <th className="py-2 px-3 font-semibold text-right">Assets</th>
                <th className="py-2 px-3 font-semibold text-right">Liabilities</th>
                <th className="py-2 px-3 font-semibold text-right">Net Worth</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {tableData.map((row) => (
                <tr key={row.date} className="hover:bg-slate-900/40">
                  <td className="py-2 px-3 font-mono text-slate-300">{row.date}</td>
                  <td className="py-2 px-3 font-mono text-right text-emerald-400">
                    {row.assets}
                  </td>
                  <td className="py-2 px-3 font-mono text-right text-rose-400">
                    {row.liabilities}
                  </td>
                  <td className="py-2 px-3 font-mono text-right font-medium text-white">
                    {row.net_worth} {displayCurrency}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
