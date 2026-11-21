import React, { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { LineChart, Table as TableIcon, ShieldAlert, TrendingUp, TrendingDown } from "lucide-react";
import { fetchNetWorthHistory } from "../api/analytics-api";
import { NetWorthHistoryResponse } from "../types";
import { formatDualAmount, useCurrency } from "@/lib/currency-context";

interface NetWorthChartProps {
  initialData?: NetWorthHistoryResponse;
  currency?: string;
}

function formatCompactAxis(val: number): string {
  const abs = Math.abs(val);
  const sign = val < 0 ? "-" : "";
  if (abs >= 1_000_000) return `${sign}${(abs / 1_000_000).toFixed(1)}M`;
  if (abs >= 1_000) return `${sign}${(abs / 1_000).toFixed(1)}k`;
  return `${sign}${abs.toFixed(0)}`;
}

function buildSmoothCurve(points: Array<{ x: number; y: number }>): string {
  if (points.length === 0) return "";
  if (points.length === 1) return `M ${points[0].x} ${points[0].y}`;
  let d = `M ${points[0].x.toFixed(2)} ${points[0].y.toFixed(2)}`;
  for (let i = 0; i < points.length - 1; i++) {
    const p0 = points[i];
    const p1 = points[i + 1];
    const cx = (p0.x + p1.x) / 2;
    d += ` C ${cx.toFixed(2)} ${p0.y.toFixed(2)}, ${cx.toFixed(2)} ${p1.y.toFixed(2)}, ${p1.x.toFixed(2)} ${p1.y.toFixed(2)}`;
  }
  return d;
}

function buildAreaPath(points: Array<{ x: number; y: number }>, baselineY: number): string {
  if (points.length === 0) return "";
  if (points.length === 1) {
    const p = points[0];
    return `M ${(p.x - 18).toFixed(2)} ${p.y.toFixed(2)} L ${(p.x + 18).toFixed(2)} ${p.y.toFixed(2)} L ${(p.x + 18).toFixed(2)} ${baselineY.toFixed(2)} L ${(p.x - 18).toFixed(2)} ${baselineY.toFixed(2)} Z`;
  }
  const curve = buildSmoothCurve(points);
  const first = points[0];
  const last = points[points.length - 1];
  return `${curve} L ${last.x.toFixed(2)} ${baselineY.toFixed(2)} L ${first.x.toFixed(2)} ${baselineY.toFixed(2)} Z`;
}

export const NetWorthChart: React.FC<NetWorthChartProps> = ({
  initialData,
  currency,
}) => {
  const { mode, usdToKhrRate, isProviderMounted } = useCurrency();
  const [granularity, setGranularity] = useState<"month" | "week" | "day">("month");
  const [viewMode, setViewMode] = useState<"chart" | "table">("chart");
  const [showAssets, setShowAssets] = useState(true);
  const [showLiabilities, setShowLiabilities] = useState(true);
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  const { data, isLoading, isError } = useQuery<NetWorthHistoryResponse>({
    queryKey: ["analytics", "net-worth-history", granularity, currency],
    queryFn: () => fetchNetWorthHistory({ granularity, currency }),
    initialData,
  });

  const series = data?.series || [];
  const tableData = data?.table || [];
  const displayCurrency = data?.currency || currency || "USD";

  const chartStats = useMemo(() => {
    if (series.length === 0) {
      return {
        latest: 0,
        delta: 0,
        deltaPct: 0,
        high: 0,
        low: 0,
        minY: 0,
        maxY: 100,
      };
    }

    const netValues = series.map((s) => parseFloat(s.net_worth) || 0);
    const assetValues = series.map((s) => parseFloat(s.assets) || 0);
    const liabValues = series.map((s) => parseFloat(s.liabilities) || 0);

    const activeValues = [...netValues];
    if (showAssets) activeValues.push(...assetValues);
    if (showLiabilities) activeValues.push(...liabValues);

    const rawMin = Math.min(...activeValues);
    const rawMax = Math.max(...activeValues);
    const span = rawMax - rawMin || Math.max(Math.abs(rawMax) * 0.2, 100);
    const pad = span * 0.12;

    const first = netValues[0];
    const latest = netValues[netValues.length - 1];
    const delta = latest - first;
    const deltaPct = first !== 0 ? (delta / Math.abs(first)) * 100 : 0;

    return {
      latest,
      delta,
      deltaPct,
      high: Math.max(...netValues),
      low: Math.min(...netValues),
      minY: rawMin - pad,
      maxY: rawMax + pad,
    };
  }, [series, showAssets, showLiabilities]);

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

  // SVG Geometry
  const SVG_W = 720;
  const SVG_H = 240;
  const PAD_L = 60;
  const PAD_R = 20;
  const PAD_T = 18;
  const PAD_B = 34;
  const PLOT_W = SVG_W - PAD_L - PAD_R;
  const PLOT_H = SVG_H - PAD_T - PAD_B;
  const ySpan = chartStats.maxY - chartStats.minY || 1;

  const toY = (val: number) => PAD_T + PLOT_H - ((val - chartStats.minY) / ySpan) * PLOT_H;
  const toX = (idx: number) =>
    series.length <= 1 ? PAD_L + PLOT_W / 2 : PAD_L + (idx / (series.length - 1)) * PLOT_W;

  const netPoints = series.map((s, i) => ({ x: toX(i), y: toY(parseFloat(s.net_worth) || 0) }));
  const assetPoints = series.map((s, i) => ({ x: toX(i), y: toY(parseFloat(s.assets) || 0) }));
  const liabPoints = series.map((s, i) => ({ x: toX(i), y: toY(parseFloat(s.liabilities) || 0) }));

  const baselineY = PAD_T + PLOT_H;
  const netCurve = buildSmoothCurve(netPoints);
  const netArea = buildAreaPath(netPoints, baselineY);
  const assetCurve = buildSmoothCurve(assetPoints);
  const liabCurve = buildSmoothCurve(liabPoints);

  const yTicks = [0, 0.333, 0.666, 1].map((t) => {
    const val = chartStats.minY + ySpan * (1 - t);
    return { val, y: PAD_T + PLOT_H * t };
  });

  const activePoint = hoveredIndex !== null && series[hoveredIndex] ? series[hoveredIndex] : null;

  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 shadow-sm">
      {/* Header & Controls */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 border-b border-[var(--border)] pb-4 mb-5">
        <div>
          <h3 className="text-sm font-semibold text-main tracking-tight flex items-center gap-2">
            <LineChart className="w-4 h-4 text-gold" />
            Net Worth Trend
          </h3>
          <p className="text-xs text-muted mt-0.5">
            Historical asset, liability, and equity curve across accounting periods
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Overlay Series Toggles */}
          {viewMode === "chart" && (
            <div className="flex items-center gap-1 rounded-lg border border-[var(--border)] bg-[var(--surface-raised)] p-0.5 text-[11px]">
              <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded font-medium text-main">
                <span className="w-2 h-2 rounded-full bg-[var(--accent)]" />
                Net Worth
              </span>
              <button
                type="button"
                onClick={() => setShowAssets((v) => !v)}
                className={`inline-flex items-center gap-1.5 px-2 py-1 rounded font-medium transition-colors cursor-pointer ${
                  showAssets ? "bg-[var(--surface)] text-[var(--positive)] shadow-2xs" : "text-faint hover:text-muted"
                }`}
              >
                <span className="w-2 h-2 rounded-full bg-[var(--positive)]" />
                Assets
              </button>
              <button
                type="button"
                onClick={() => setShowLiabilities((v) => !v)}
                className={`inline-flex items-center gap-1.5 px-2 py-1 rounded font-medium transition-colors cursor-pointer ${
                  showLiabilities ? "bg-[var(--surface)] text-[var(--negative)] shadow-2xs" : "text-faint hover:text-muted"
                }`}
              >
                <span className="w-2 h-2 rounded-full bg-[var(--negative)]" />
                Liabilities
              </button>
            </div>
          )}

          {/* Granularity Selector */}
          <div className="flex items-center rounded-lg border border-[var(--border)] bg-[var(--surface-raised)] p-0.5 text-xs">
            {(["month", "week", "day"] as const).map((g) => (
              <button
                key={g}
                type="button"
                onClick={() => setGranularity(g)}
                className={`px-2.5 py-1 rounded font-medium capitalize transition-colors cursor-pointer ${
                  granularity === g ? "bg-gold shadow-xs" : "text-muted hover:text-main"
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
                viewMode === "chart" ? "bg-gold shadow-xs" : "text-muted hover:text-main"
              }`}
            >
              <LineChart className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={() => setViewMode("table")}
              aria-label="View accessible data table"
              className={`p-1.5 rounded transition-colors cursor-pointer ${
                viewMode === "table" ? "bg-gold shadow-xs" : "text-muted hover:text-main"
              }`}
            >
              <TableIcon className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {isLoading && !data ? (
        <div className="h-56 flex items-center justify-center text-muted text-xs animate-pulse">
          Loading historical curve...
        </div>
      ) : series.length === 0 ? (
        <div className="h-56 flex items-center justify-center text-muted text-xs">
          No historical net worth snapshots available yet.
        </div>
      ) : viewMode === "chart" ? (
        /* Interactive SVG Area & Multi-Line Chart */
        <div className="space-y-4">
          {/* Summary Stats Strip */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-raised)] px-3 py-2">
              <div className="text-[10px] text-faint font-medium">
                {activePoint ? `Selected (${activePoint.date})` : "Latest Net Worth"}
              </div>
              {(() => {
                const rawLatest = activePoint
                  ? activePoint.net_worth
                  : series[series.length - 1].net_worth;
                const dualLatest = formatDualAmount(rawLatest, displayCurrency, mode, usdToKhrRate);
                return (
                  <>
                    <div className="font-mono text-sm font-bold text-main mt-0.5">
                      {isProviderMounted ? (
                        dualLatest.primary
                      ) : (
                        <>
                          {rawLatest}{" "}
                          <span className="text-[10px] font-normal text-muted">
                            {displayCurrency}
                          </span>
                        </>
                      )}
                    </div>
                    {isProviderMounted && dualLatest.secondary && (
                      <div className="text-[10px] font-mono text-muted">
                        {dualLatest.secondary}
                      </div>
                    )}
                  </>
                );
              })()}
            </div>

            <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-raised)] px-3 py-2">
              <div className="text-[10px] text-faint font-medium">
                {activePoint ? "Assets / Liabilities" : "Period Change"}
              </div>
              {activePoint ? (
                <div className="font-mono text-xs font-semibold mt-1 flex items-center gap-2">
                  <span className="text-[var(--positive)]">{activePoint.assets}</span>
                  <span className="text-faint">/</span>
                  <span className="text-[var(--negative)]">{activePoint.liabilities}</span>
                </div>
              ) : (
                <div
                  className={`font-mono text-sm font-bold mt-0.5 flex items-center gap-1 ${
                    chartStats.delta >= 0 ? "text-[var(--positive)]" : "text-[var(--negative)]"
                  }`}
                >
                  {chartStats.delta >= 0 ? (
                    <TrendingUp className="w-3.5 h-3.5" />
                  ) : (
                    <TrendingDown className="w-3.5 h-3.5" />
                  )}
                  <span>
                    {chartStats.delta >= 0 ? "+" : ""}
                    {chartStats.delta.toFixed(2)}
                  </span>
                  {series.length > 1 && (
                    <span className="text-[10px] font-normal opacity-80">
                      ({chartStats.deltaPct >= 0 ? "+" : ""}
                      {chartStats.deltaPct.toFixed(1)}%)
                    </span>
                  )}
                </div>
              )}
            </div>

            <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-raised)] px-3 py-2">
              <div className="text-[10px] text-faint font-medium">Period High</div>
              {(() => {
                const dualHigh = formatDualAmount(chartStats.high, displayCurrency, mode, usdToKhrRate);
                return (
                  <>
                    <div className="font-mono text-sm font-bold text-main mt-0.5">
                      {isProviderMounted ? (
                        dualHigh.primary
                      ) : (
                        <>
                          {chartStats.high.toFixed(2)}{" "}
                          <span className="text-[10px] font-normal text-muted">{displayCurrency}</span>
                        </>
                      )}
                    </div>
                    {isProviderMounted && dualHigh.secondary && (
                      <div className="text-[10px] font-mono text-muted">{dualHigh.secondary}</div>
                    )}
                  </>
                );
              })()}
            </div>

            <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-raised)] px-3 py-2">
              <div className="text-[10px] text-faint font-medium">Period Low</div>
              {(() => {
                const dualLow = formatDualAmount(chartStats.low, displayCurrency, mode, usdToKhrRate);
                return (
                  <>
                    <div className="font-mono text-sm font-bold text-main mt-0.5">
                      {isProviderMounted ? (
                        dualLow.primary
                      ) : (
                        <>
                          {chartStats.low.toFixed(2)}{" "}
                          <span className="text-[10px] font-normal text-muted">{displayCurrency}</span>
                        </>
                      )}
                    </div>
                    {isProviderMounted && dualLow.secondary && (
                      <div className="text-[10px] font-mono text-muted">{dualLow.secondary}</div>
                    )}
                  </>
                );
              })()}
            </div>
          </div>

          {/* Responsive SVG Chart */}
          <div className="relative w-full" onMouseLeave={() => setHoveredIndex(null)}>
            <svg
              viewBox={`0 0 ${SVG_W} ${SVG_H}`}
              className="w-full h-60 overflow-visible select-none"
              role="img"
              aria-label="Net Worth History Interactive Line Chart"
            >
              <defs>
                <linearGradient id="nwGoldGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.32" />
                  <stop offset="100%" stopColor="var(--accent)" stopOpacity="0.01" />
                </linearGradient>
                <filter id="nwGlow" x="-10%" y="-20%" width="120%" height="140%">
                  <feDropShadow dx="0" dy="2" stdDeviation="3" floodColor="var(--accent)" floodOpacity="0.35" />
                </filter>
              </defs>

              {/* Horizontal Gridlines & Y Labels */}
              {yTicks.map((tick, idx) => (
                <g key={idx}>
                  <line
                    x1={PAD_L}
                    x2={SVG_W - PAD_R}
                    y1={tick.y}
                    y2={tick.y}
                    stroke="var(--border)"
                    strokeDasharray="3 3"
                    strokeWidth="1"
                  />
                  <text
                    x={PAD_L - 8}
                    y={tick.y + 3.5}
                    textAnchor="end"
                    fill="var(--text-faint)"
                    fontSize="10"
                    fontFamily="var(--font-mono)"
                  >
                    {formatCompactAxis(tick.val)}
                  </text>
                </g>
              ))}

              {/* Zero reference line if visible inside range */}
              {chartStats.minY < 0 && chartStats.maxY > 0 && (
                <line
                  x1={PAD_L}
                  x2={SVG_W - PAD_R}
                  y1={toY(0)}
                  y2={toY(0)}
                  stroke="var(--border-strong)"
                  strokeWidth="1"
                />
              )}

              {/* Area Fill */}
              <path d={netArea} fill="url(#nwGoldGradient)" className="animate-xaku-fade-up" />

              {/* Overlay: Liabilities */}
              {showLiabilities && (
                <path
                  d={liabCurve}
                  fill="none"
                  stroke="var(--negative)"
                  strokeWidth="1.75"
                  strokeDasharray="4 3"
                  opacity="0.8"
                  className="animate-xaku-fade-up"
                />
              )}

              {/* Overlay: Assets */}
              {showAssets && (
                <path
                  d={assetCurve}
                  fill="none"
                  stroke="var(--positive)"
                  strokeWidth="1.75"
                  strokeDasharray="4 3"
                  opacity="0.85"
                  className="animate-xaku-fade-up"
                />
              )}

              {/* Primary: Net Worth Line */}
              <path
                d={netCurve}
                fill="none"
                stroke="var(--accent)"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                filter="url(#nwGlow)"
                className="animate-xaku-line"
              />

              {/* Hover Crosshair */}
              {hoveredIndex !== null && netPoints[hoveredIndex] && (
                <line
                  x1={netPoints[hoveredIndex].x}
                  x2={netPoints[hoveredIndex].x}
                  y1={PAD_T}
                  y2={baselineY}
                  stroke="var(--border-strong)"
                  strokeDasharray="3 3"
                  strokeWidth="1"
                />
              )}

              {/* Data Points + X Axis Labels + Interactive Hover Hit Targets */}
              {series.map((pt, i) => {
                const np = netPoints[i];
                const isHovered = hoveredIndex === i;
                const colWidth = series.length <= 1 ? PLOT_W : PLOT_W / series.length;
                const showLabel =
                  series.length <= 10 ||
                  i === 0 ||
                  i === series.length - 1 ||
                  i % Math.ceil(series.length / 8) === 0;

                return (
                  <g key={pt.date}>
                    {showAssets && (
                      <circle
                        cx={assetPoints[i].x}
                        cy={assetPoints[i].y}
                        r={isHovered ? 4 : 2.2}
                        fill="var(--positive)"
                      />
                    )}
                    {showLiabilities && (
                      <circle
                        cx={liabPoints[i].x}
                        cy={liabPoints[i].y}
                        r={isHovered ? 4 : 2.2}
                        fill="var(--negative)"
                      />
                    )}
                    {isHovered && (
                      <circle
                        cx={np.x}
                        cy={np.y}
                        r={10}
                        fill="var(--accent)"
                        opacity="0.16"
                      />
                    )}
                    <circle
                      cx={np.x}
                      cy={np.y}
                      r={isHovered ? 5.5 : series.length <= 20 ? 3.5 : 2}
                      fill="var(--surface)"
                      stroke="var(--accent)"
                      strokeWidth={isHovered ? 2.5 : 2}
                      className="transition-all duration-150"
                    />

                    {showLabel && (
                      <text
                        x={np.x}
                        y={SVG_H - 10}
                        textAnchor="middle"
                        fill={isHovered ? "var(--text)" : "var(--text-faint)"}
                        fontSize="10"
                        fontFamily="var(--font-mono)"
                      >
                        {pt.date.length >= 10 ? pt.date.slice(5) : pt.date}
                      </text>
                    )}

                    {/* Invisible hover column */}
                    <rect
                      x={np.x - colWidth / 2}
                      y={PAD_T}
                      width={colWidth}
                      height={PLOT_H + 10}
                      fill="transparent"
                      className="cursor-crosshair"
                      onMouseEnter={() => setHoveredIndex(i)}
                    />
                  </g>
                );
              })}
            </svg>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] text-muted pt-1 border-t border-[var(--border)]">
            <span>
              Historical series ({series.length} snapshot{series.length === 1 ? "" : "s"}) · Hover any point to inspect
            </span>
            <span className="font-mono">Reporting currency: {displayCurrency}</span>
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
