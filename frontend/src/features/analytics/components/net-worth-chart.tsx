import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { LineChart, Table as TableIcon, ShieldAlert } from "lucide-react";
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

  const { data, isLoading, isError } = useQuery<NetWorthHistoryResponse>({
    queryKey: ["analytics", "net-worth-history", granularity, currency],
    queryFn: () => fetchNetWorthHistory({ granularity, currency }),
    initialData,
  });

  if (isError) {
    return (
      <div className="rounded-xl border border-[var(--negative-border)] bg-[var(--negative-bg)] p-6 text-[var(--negative)]">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-5 h-5" />
          <span className="font-semibold text-sm">Failed to load net worth trend</span>
        </div>
      </div>
    );
  }

  const series = data?.series || [];
  const tableData = data?.table || [];
  const displayCurrency = data?.currency || currency || "USD";

  const values = series.map((s) => parseFloat(s.net_worth) || 0);
  const maxVal = Math.max(...values, 100);
  const minVal = Math.min(...values, 0);
  const range = maxVal - minVal || 1;

  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 shadow-sm">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[var(--border)] pb-4 mb-5">
        <div>
          <h3 className="text-sm font-semibold text-main tracking-tight flex items-center gap-2">
            <LineChart className="w-4 h-4 text-gold" />
            Net Worth Trend
          </h3>
          <p className="text-xs text-muted mt-0.5">
            Historical balance curve across accounting periods
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Granularity Selector */}
          <div className="flex items-center rounded-lg border border-[var(--border)] bg-[var(--surface-raised)] p-0.5 text-xs">
            {(["month", "week", "day"] as const).map((g) => (
              <button
                key={g}
                type="button"
                onClick={() => setGranularity(g)}
                className={`px-2.5 py-1 rounded font-medium capitalize transition-colors cursor-pointer ${
                  granularity === g
                    ? "bg-gold shadow-xs"
                    : "text-muted hover:text-main"
                }`}
              >
                {g}
              </button>
            ))}
          </div>

          {/* Chart / Table View Mode Switcher */}
          <div className="flex items-center rounded-lg border border-[var(--border)] bg-[var(--surface-raised)] p-0.5 text-xs">
            <button
              type="button"
              onClick={() => setViewMode("chart")}
              aria-label="View trend chart"
              className={`p-1.5 rounded transition-colors cursor-pointer ${
                viewMode === "chart"
                  ? "bg-gold shadow-xs"
                  : "text-muted hover:text-main"
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
                  ? "bg-gold shadow-xs"
                  : "text-muted hover:text-main"
              }`}
            >
              <TableIcon className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {isLoading && !data ? (
        <div className="h-48 flex items-center justify-center text-muted text-xs animate-pulse">
          Loading historical curve...
        </div>
      ) : series.length === 0 ? (
        <div className="h-48 flex items-center justify-center text-muted text-xs">
          No historical net worth snapshots available yet.
        </div>
      ) : viewMode === "chart" ? (
        /* Visual Chart View */
        <div className="space-y-4">
          <div className="h-48 flex items-end gap-2 pt-6 pb-2 px-1 border-b border-[var(--border)] overflow-x-auto">
            {series.map((point) => {
              const val = parseFloat(point.net_worth) || 0;
              const heightPct = Math.max(8, Math.min(100, ((val - minVal) / range) * 100));
              const isNeg = val < 0;

              return (
                <div
                  key={point.date}
                  className="flex-1 min-w-[28px] flex flex-col items-center gap-1 group relative h-full justify-end"
                >
                  {/* Tooltip */}
                  <div className="absolute -top-10 opacity-0 group-hover:opacity-100 transition-opacity bg-[var(--surface-raised)] border border-[var(--border)] rounded px-2 py-1 text-[11px] font-mono text-main pointer-events-none whitespace-nowrap z-10 shadow-lg">
                    {point.date}: {point.net_worth} {displayCurrency}
                  </div>

                  {/* Bar */}
                  <div
                    style={{ height: `${heightPct}%` }}
                    className={`w-full max-w-[32px] rounded-t transition-all ${
                      isNeg
                        ? "bg-[var(--negative)] opacity-70 hover:opacity-100"
                        : "bg-[var(--accent)] opacity-85 hover:opacity-100"
                    }`}
                  />
                  <span className="text-[10px] text-muted font-mono truncate max-w-[40px]">
                    {point.date.slice(5)}
                  </span>
                </div>
              );
            })}
          </div>
          <div className="flex justify-between text-[11px] text-muted">
            <span>Historical series ({series.length} data points)</span>
            <span>All values in {displayCurrency}</span>
          </div>
        </div>
      ) : (
        /* Accessible Fallback Data Table */
        <div className="overflow-x-auto">
          <table
            className="w-full text-left text-xs min-w-[500px]"
            aria-label="Net Worth History Data Table"
          >
            <thead>
              <tr className="border-b border-[var(--border)] text-muted uppercase tracking-wider text-[10px] bg-[var(--surface-raised)]">
                <th className="py-2.5 px-3 font-semibold">Date</th>
                <th className="py-2.5 px-3 font-semibold text-right">Assets</th>
                <th className="py-2.5 px-3 font-semibold text-right">Liabilities</th>
                <th className="py-2.5 px-3 font-semibold text-right">Net Worth</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)]">
              {tableData.map((row) => (
                <tr key={row.date} className="hover:bg-[var(--surface-raised)] transition-colors">
                  <td className="py-2 px-3 font-mono text-main">{row.date}</td>
                  <td className="py-2 px-3 font-mono text-right text-[var(--positive)]">
                    {row.assets}
                  </td>
                  <td className="py-2 px-3 font-mono text-right text-[var(--negative)]">
                    {row.liabilities}
                  </td>
                  <td className="py-2 px-3 font-mono text-right font-medium text-main">
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
