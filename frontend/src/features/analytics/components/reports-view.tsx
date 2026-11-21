import React, { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  FileText,
  Calendar,
  ArrowUpRight,
  ArrowDownRight,
  DollarSign,
  CheckCircle2,
  AlertTriangle,
  Download,
  BarChart2,
  PieChart as PieChartIcon,
  Activity,
} from "lucide-react";
import {
  fetchIncomeReport,
  fetchCashFlowReport,
  fetchCategoryReport,
} from "../api/analytics-api";
import { ReportResponse } from "../types";
import { formatDualAmount, useCurrency } from "@/lib/currency-context";

interface ReportsViewProps {
  initialData?: ReportResponse;
  currency?: string;
}

const CHART_PALETTE = [
  "#F0B90B",
  "#10B981",
  "#38BDF8",
  "#A78BFA",
  "#F43F5E",
  "#FB923C",
  "#14B8A6",
  "#E879F9",
];

function escapeCsvCell(val: unknown): string {
  const s = String(val ?? "");
  if (/[",\n]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
  return s;
}

export const ReportsView: React.FC<ReportsViewProps> = ({
  initialData,
  currency,
}) => {
  const { mode, usdToKhrRate, isProviderMounted } = useCurrency();
  const [reportType, setReportType] = useState<"income_expense" | "cashflow" | "category">(
    "income_expense"
  );
  const [hoveredPeriodIdx, setHoveredPeriodIdx] = useState<number | null>(null);
  const [hoveredCategoryIdx, setHoveredCategoryIdx] = useState<number | null>(null);

  const now = new Date();
  const defaultEnd = now.toISOString().slice(0, 10);
  const dStart = new Date();
  dStart.setDate(dStart.getDate() - 90);
  const defaultStart = dStart.toISOString().slice(0, 10);

  const [startDate, setStartDate] = useState(defaultStart);
  const [endDate, setEndDate] = useState(defaultEnd);

  const { data, isLoading } = useQuery<ReportResponse>({
    queryKey: ["analytics", "reports", reportType, startDate, endDate, currency],
    queryFn: () => {
      if (reportType === "income_expense") {
        return fetchIncomeReport({ start: startDate, end: endDate, currency });
      }
      if (reportType === "cashflow") {
        return fetchCashFlowReport({ start: startDate, end: endDate, currency });
      }
      return fetchCategoryReport({ start: startDate, end: endDate, currency });
    },
    initialData,
  });

  const totals = data?.totals || {};
  const tableData = data?.table || [];
  const recon = data?.reconciliation;
  const isReconciled = recon?.difference === "0.00";
  const displayCurrency = data?.currency || currency || "USD";

  const kpiDuals = {
    income: formatDualAmount(String(totals.income || "0.00"), displayCurrency, mode, usdToKhrRate),
    expense: formatDualAmount(String(totals.expense || "0.00"), displayCurrency, mode, usdToKhrRate),
    net: formatDualAmount(String(totals.net || "0.00"), displayCurrency, mode, usdToKhrRate),
    inflows: formatDualAmount(String(totals.inflows || "0.00"), displayCurrency, mode, usdToKhrRate),
    outflows: formatDualAmount(String(totals.outflows || "0.00"), displayCurrency, mode, usdToKhrRate),
    netCashFlow: formatDualAmount(String(totals.net_cash_flow || "0.00"), displayCurrency, mode, usdToKhrRate),
    totalSpending: formatDualAmount(String(totals.total_spending || "0.00"), displayCurrency, mode, usdToKhrRate),
  };

  const handleExportCsv = () => {
    if (tableData.length === 0) return;

    let headers: string[] = [];
    let rows: string[][] = [];

    if (reportType === "income_expense") {
      headers = ["Period", `Income (${displayCurrency})`, `Expense (${displayCurrency})`, `Net (${displayCurrency})`];
      rows = tableData.map((r) => [String(r.period ?? ""), String(r.income ?? "0.00"), String(r.expense ?? "0.00"), String(r.net ?? "0.00")]);
    } else if (reportType === "cashflow") {
      headers = ["Cash Flow Item", `Amount (${displayCurrency})`];
      rows = tableData.map((r) => [String(r.item ?? ""), String(r.amount ?? "0.00")]);
    } else {
      headers = ["Category", "Share (%)", `Amount (${displayCurrency})`];
      rows = tableData.map((r) => [String(r.category_name ?? ""), String(r.percentage ?? "0"), String(r.amount ?? "0.00")]);
    }

    const csvContent = [headers, ...rows].map((row) => row.map(escapeCsvCell).join(",")).join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `xakufinance-${reportType}-${startDate}-to-${endDate}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // Income vs Expense grouped bar geometry
  const incomeSeries = useMemo(() => {
    const raw = (data?.series && data.series.length > 0 ? data.series : tableData) || [];
    return raw.map((row) => ({
      period: String(row.period || ""),
      income: Math.max(0, parseFloat(String(row.income || "0")) || 0),
      expense: Math.abs(parseFloat(String(row.expense || "0")) || 0),
      net: parseFloat(String(row.net || "0")) || 0,
      incomeStr: String(row.income || "0.00"),
      expenseStr: String(row.expense || "0.00"),
      netStr: String(row.net || "0.00"),
    }));
  }, [data?.series, tableData]);

  // Donut segments for Category report
  const categorySegments = useMemo(() => {
    const R = 70;
    const C = 2 * Math.PI * R;
    let cumulative = 0;
    return tableData.slice(0, 8).map((row, idx) => {
      const pct = Math.max(0, Math.min(100, parseFloat(String(row.percentage || "0")) || 0));
      const dashLen = (pct / 100) * C;
      const offset = -((cumulative / 100) * C);
      cumulative += pct;
      return {
        idx,
        name: String(row.category_name || "Other"),
        amount: String(row.amount || "0.00"),
        pct,
        color: CHART_PALETTE[idx % CHART_PALETTE.length],
        dashArray: `${dashLen} ${C - dashLen}`,
        dashOffset: offset,
      };
    });
  }, [tableData]);

  // Cash flow waterfall numbers
  const cashFlowStats = useMemo(() => {
    const inflows = Math.max(0, parseFloat(String(totals.inflows || "0")) || 0);
    const outflows = Math.abs(parseFloat(String(totals.outflows || "0")) || 0);
    const net = parseFloat(String(totals.net_cash_flow || "0")) || 0;
    const maxMag = Math.max(inflows, outflows, Math.abs(net), 1);
    const retentionRate = inflows > 0 ? (net / inflows) * 100 : 0;
    return { inflows, outflows, net, maxMag, retentionRate };
  }, [totals]);

  return (
    <div className="space-y-6">
      {/* Control bar */}
      <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        {/* Report Kind Tabs */}
        <div className="flex items-center gap-1 rounded-lg border border-[var(--border)] bg-[var(--surface-raised)] p-1 text-xs overflow-x-auto">
          <button
            type="button"
            onClick={() => setReportType("income_expense")}
            className={`px-3 py-1.5 rounded font-medium transition-colors cursor-pointer whitespace-nowrap ${
              reportType === "income_expense" ? "bg-gold shadow-xs" : "text-muted hover:text-main"
            }`}
          >
            Income vs Expense
          </button>
          <button
            type="button"
            onClick={() => setReportType("cashflow")}
            className={`px-3 py-1.5 rounded font-medium transition-colors cursor-pointer whitespace-nowrap ${
              reportType === "cashflow" ? "bg-gold shadow-xs" : "text-muted hover:text-main"
            }`}
          >
            Cash Flow Statement
          </button>
          <button
            type="button"
            onClick={() => setReportType("category")}
            className={`px-3 py-1.5 rounded font-medium transition-colors cursor-pointer whitespace-nowrap ${
              reportType === "category" ? "bg-gold shadow-xs" : "text-muted hover:text-main"
            }`}
          >
            Category Breakdown
          </button>
        </div>

        {/* Date Filters + CSV Export */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <div className="flex items-center gap-1.5 bg-[var(--surface-raised)] border border-[var(--border)] rounded-lg px-2.5 py-1.5 text-main">
            <Calendar className="w-3.5 h-3.5 text-muted" />
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="bg-transparent text-main focus:outline-none text-xs"
              aria-label="Report start date"
            />
            <span className="text-muted">to</span>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="bg-transparent text-main focus:outline-none text-xs"
              aria-label="Report end date"
            />
          </div>

          <button
            type="button"
            onClick={handleExportCsv}
            disabled={tableData.length === 0}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface-raised)] hover:bg-[var(--surface-hover)] text-main font-medium transition-colors cursor-pointer disabled:opacity-40"
          >
            <Download className="w-3.5 h-3.5 text-gold" />
            Export CSV
          </button>
        </div>
      </div>

      {/* Ledger Reconciliation Verification Banner */}
      {recon && (
        <div
          className={`rounded-xl border p-4 text-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 ${
            isReconciled
              ? "border-[var(--positive-border)] bg-[var(--positive-bg)] text-[var(--positive)]"
              : "border-[var(--negative-border)] bg-[var(--negative-bg)] text-[var(--negative)]"
          }`}
        >
          <div className="flex items-center gap-2">
            {isReconciled ? (
              <CheckCircle2 className="w-4 h-4 text-[var(--positive)] shrink-0" />
            ) : (
              <AlertTriangle className="w-4 h-4 text-[var(--negative)] shrink-0" />
            )}
            <span>
              <strong>Double-Entry Ledger Integrity:</strong>{" "}
              {isReconciled
                ? `Report verified against ledger postings (difference: ${recon.difference} ${displayCurrency})`
                : `Discrepancy detected: ledger differs from reported transactions by ${recon.difference} ${displayCurrency}`}
            </span>
          </div>
          <span className="font-mono text-[10px] text-faint shrink-0">
            Checked: {recon.checked_at.slice(0, 19)}
          </span>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {reportType === "income_expense" && (
          <>
            <div className="rounded-xl border border-[var(--positive-border)] bg-[var(--positive-bg)] p-4">
              <div className="flex items-center justify-between text-xs text-muted mb-1">
                <span>Total Income</span>
                <ArrowUpRight className="w-4 h-4 text-[var(--positive)]" />
              </div>
              <div className="font-mono text-2xl font-bold text-[var(--positive)]">
                {isProviderMounted ? (
                  kpiDuals.income.primary
                ) : (
                  <>
                    {totals.income || "0.00"}{" "}
                    <span className="text-xs text-muted font-sans">{displayCurrency}</span>
                  </>
                )}
              </div>
              {isProviderMounted && kpiDuals.income.secondary && (
                <div className="text-[11px] font-mono text-muted mt-0.5">
                  {kpiDuals.income.secondary}
                </div>
              )}
            </div>
            <div className="rounded-xl border border-[var(--negative-border)] bg-[var(--negative-bg)] p-4">
              <div className="flex items-center justify-between text-xs text-muted mb-1">
                <span>Total Expenses</span>
                <ArrowDownRight className="w-4 h-4 text-[var(--negative)]" />
              </div>
              <div className="font-mono text-2xl font-bold text-[var(--negative)]">
                {isProviderMounted ? (
                  kpiDuals.expense.primary
                ) : (
                  <>
                    {totals.expense || "0.00"}{" "}
                    <span className="text-xs text-muted font-sans">{displayCurrency}</span>
                  </>
                )}
              </div>
              {isProviderMounted && kpiDuals.expense.secondary && (
                <div className="text-[11px] font-mono text-muted mt-0.5">
                  {kpiDuals.expense.secondary}
                </div>
              )}
            </div>
            <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
              <div className="flex items-center justify-between text-xs text-muted mb-1">
                <span>Net Savings</span>
                <DollarSign className="w-4 h-4 text-gold" />
              </div>
              <div className="font-mono text-2xl font-bold text-main">
                {isProviderMounted ? (
                  kpiDuals.net.primary
                ) : (
                  <>
                    {totals.net || "0.00"}{" "}
                    <span className="text-xs text-muted font-sans">{displayCurrency}</span>
                  </>
                )}
              </div>
              {isProviderMounted && kpiDuals.net.secondary && (
                <div className="text-[11px] font-mono text-muted mt-0.5">
                  {kpiDuals.net.secondary}
                </div>
              )}
            </div>
          </>
        )}

        {reportType === "cashflow" && (
          <>
            <div className="rounded-xl border border-[var(--positive-border)] bg-[var(--positive-bg)] p-4">
              <div className="text-xs text-muted mb-1">Operating Inflows</div>
              <div className="font-mono text-2xl font-bold text-[var(--positive)]">
                {isProviderMounted ? (
                  kpiDuals.inflows.primary
                ) : (
                  <>
                    {totals.inflows || "0.00"}{" "}
                    <span className="text-xs text-muted font-sans">{displayCurrency}</span>
                  </>
                )}
              </div>
              {isProviderMounted && kpiDuals.inflows.secondary && (
                <div className="text-[11px] font-mono text-muted mt-0.5">
                  {kpiDuals.inflows.secondary}
                </div>
              )}
            </div>
            <div className="rounded-xl border border-[var(--negative-border)] bg-[var(--negative-bg)] p-4">
              <div className="text-xs text-muted mb-1">Operating Outflows</div>
              <div className="font-mono text-2xl font-bold text-[var(--negative)]">
                {isProviderMounted ? (
                  kpiDuals.outflows.primary
                ) : (
                  <>
                    {totals.outflows || "0.00"}{" "}
                    <span className="text-xs text-muted font-sans">{displayCurrency}</span>
                  </>
                )}
              </div>
              {isProviderMounted && kpiDuals.outflows.secondary && (
                <div className="text-[11px] font-mono text-muted mt-0.5">
                  {kpiDuals.outflows.secondary}
                </div>
              )}
            </div>
            <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
              <div className="text-xs text-muted mb-1">Net Cash Movement</div>
              <div className="font-mono text-2xl font-bold text-main">
                {isProviderMounted ? (
                  kpiDuals.netCashFlow.primary
                ) : (
                  <>
                    {totals.net_cash_flow || "0.00"}{" "}
                    <span className="text-xs text-muted font-sans">{displayCurrency}</span>
                  </>
                )}
              </div>
              {isProviderMounted && kpiDuals.netCashFlow.secondary && (
                <div className="text-[11px] font-mono text-muted mt-0.5">
                  {kpiDuals.netCashFlow.secondary}
                </div>
              )}
            </div>
          </>
        )}

        {reportType === "category" && (
          <div className="sm:col-span-3 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
            <div className="text-xs text-muted mb-1">Total Category Spending</div>
            <div className="font-mono text-2xl font-bold text-main">
              {isProviderMounted ? (
                kpiDuals.totalSpending.primary
              ) : (
                <>
                  {totals.total_spending || "0.00"}{" "}
                  <span className="text-xs text-muted font-sans">{displayCurrency}</span>
                </>
              )}
            </div>
            {isProviderMounted && kpiDuals.totalSpending.secondary && (
              <div className="text-[11px] font-mono text-muted mt-0.5">
                {kpiDuals.totalSpending.secondary}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Interactive Visual Statement Graph */}
      {!isLoading && tableData.length > 0 && (
        <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 shadow-sm">
          {reportType === "income_expense" && incomeSeries.length > 0 && (() => {
            const SVG_W = 700;
            const SVG_H = 210;
            const PAD_L = 56;
            const PAD_R = 16;
            const PAD_T = 18;
            const PAD_B = 30;
            const PLOT_W = SVG_W - PAD_L - PAD_R;
            const PLOT_H = SVG_H - PAD_T - PAD_B;
            const maxVal = Math.max(
              ...incomeSeries.flatMap((s) => [s.income, s.expense, Math.abs(s.net)]),
              100
            );
            const groupW = PLOT_W / incomeSeries.length;
            const barW = Math.min(26, Math.max(10, groupW * 0.28));
            const hovered = hoveredPeriodIdx !== null ? incomeSeries[hoveredPeriodIdx] : null;

            const netLinePts = incomeSeries
              .map((s, i) => {
                const cx = PAD_L + groupW * i + groupW / 2;
                const cy = PAD_T + PLOT_H - (Math.max(0, s.net) / maxVal) * PLOT_H;
                return `${cx.toFixed(1)},${cy.toFixed(1)}`;
              })
              .join(" ");

            return (
              <div className="space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <BarChart2 className="w-4 h-4 text-gold" />
                    <h3 className="text-sm font-semibold text-main">Income vs. Expense Trajectory</h3>
                  </div>
                  <div className="flex flex-wrap items-center gap-4 text-[11px] text-muted">
                    <span className="inline-flex items-center gap-1.5">
                      <span className="w-2.5 h-2.5 rounded-xs bg-[var(--positive)]" />
                      Income
                    </span>
                    <span className="inline-flex items-center gap-1.5">
                      <span className="w-2.5 h-2.5 rounded-xs bg-[var(--negative)]" />
                      Expense
                    </span>
                    <span className="inline-flex items-center gap-1.5">
                      <span className="w-2.5 h-0.5 bg-[var(--accent)]" />
                      Net Savings
                    </span>
                  </div>
                </div>

                {hovered && (
                  <div className="flex flex-wrap items-center gap-4 px-3 py-2 rounded-lg bg-[var(--surface-raised)] border border-[var(--border)] text-xs font-mono">
                    <span className="font-semibold text-main">{hovered.period}</span>
                    <span className="text-[var(--positive)]">
                      In: {hovered.incomeStr} {displayCurrency}
                    </span>
                    <span className="text-[var(--negative)]">
                      Out: {hovered.expenseStr} {displayCurrency}
                    </span>
                    <span className="text-gold font-semibold">
                      Net: {hovered.netStr} {displayCurrency}
                    </span>
                  </div>
                )}

                <svg
                  viewBox={`0 0 ${SVG_W} ${SVG_H}`}
                  className="w-full h-52 overflow-visible select-none"
                  role="img"
                  aria-label="Income vs Expense Bar Chart"
                  onMouseLeave={() => setHoveredPeriodIdx(null)}
                >
                  {[0, 0.33, 0.66, 1].map((t, idx) => {
                    const y = PAD_T + PLOT_H * t;
                    const v = maxVal * (1 - t);
                    return (
                      <g key={idx}>
                        <line
                          x1={PAD_L}
                          x2={SVG_W - PAD_R}
                          y1={y}
                          y2={y}
                          stroke="var(--border)"
                          strokeDasharray="3 3"
                        />
                        <text
                          x={PAD_L - 8}
                          y={y + 3.5}
                          textAnchor="end"
                          fill="var(--text-faint)"
                          fontSize="10"
                          fontFamily="var(--font-mono)"
                        >
                          {v >= 1000 ? `${(v / 1000).toFixed(1)}k` : v.toFixed(0)}
                        </text>
                      </g>
                    );
                  })}

                  {incomeSeries.map((item, i) => {
                    const center = PAD_L + groupW * i + groupW / 2;
                    const incH = (item.income / maxVal) * PLOT_H;
                    const expH = (item.expense / maxVal) * PLOT_H;
                    const isHov = hoveredPeriodIdx === i;

                    return (
                      <g
                        key={item.period}
                        className="cursor-pointer"
                        onMouseEnter={() => setHoveredPeriodIdx(i)}
                      >
                        <rect
                          x={PAD_L + groupW * i}
                          y={PAD_T}
                          width={groupW}
                          height={PLOT_H}
                          fill={isHov ? "var(--surface-raised)" : "transparent"}
                          opacity="0.5"
                          rx="4"
                        />
                        <rect
                          x={center - barW - 2}
                          y={PAD_T + PLOT_H - incH}
                          width={barW}
                          height={Math.max(2, incH)}
                          rx="4"
                          fill="var(--positive)"
                          opacity={isHov ? 1 : 0.85}
                          className="animate-xaku-bar transition-all duration-300"
                        />
                        <rect
                          x={center + 2}
                          y={PAD_T + PLOT_H - expH}
                          width={barW}
                          height={Math.max(2, expH)}
                          rx="4"
                          fill="var(--negative)"
                          opacity={isHov ? 1 : 0.85}
                          className="animate-xaku-bar transition-all duration-300"
                        />
                        <text
                          x={center}
                          y={SVG_H - 8}
                          textAnchor="middle"
                          fill={isHov ? "var(--text)" : "var(--text-faint)"}
                          fontSize="10"
                          fontFamily="var(--font-mono)"
                        >
                          {item.period}
                        </text>
                      </g>
                    );
                  })}

                  {incomeSeries.length > 1 && (
                    <polyline
                      points={netLinePts}
                      fill="none"
                      stroke="var(--accent)"
                      strokeWidth="2.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      className="animate-xaku-line"
                    />
                  )}

                  {incomeSeries.map((item, i) => {
                    const center = PAD_L + groupW * i + groupW / 2;
                    const cy = PAD_T + PLOT_H - (Math.max(0, item.net) / maxVal) * PLOT_H;
                    return (
                      <circle
                        key={`net-${item.period}`}
                        cx={center}
                        cy={cy}
                        r={hoveredPeriodIdx === i ? 5 : 3.5}
                        fill="var(--surface)"
                        stroke="var(--accent)"
                        strokeWidth="2"
                      />
                    );
                  })}
                </svg>
              </div>
            );
          })()}

          {reportType === "category" && categorySegments.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <PieChartIcon className="w-4 h-4 text-gold" />
                <h3 className="text-sm font-semibold text-main">Category Distribution</h3>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-[220px_1fr] gap-6 items-center">
                <div className="relative flex items-center justify-center">
                  <svg
                    viewBox="0 0 200 200"
                    className="w-44 h-44 -rotate-90"
                    role="img"
                    aria-label="Category Distribution Donut Chart"
                  >
                    <circle
                      cx="100"
                      cy="100"
                      r="70"
                      fill="none"
                      stroke="var(--surface-raised)"
                      strokeWidth="24"
                    />
                    {categorySegments.map((seg) => (
                      <circle
                        key={seg.name}
                        cx="100"
                        cy="100"
                        r="70"
                        fill="none"
                        stroke={seg.color}
                        strokeWidth={hoveredCategoryIdx === seg.idx ? 28 : 24}
                        strokeDasharray={seg.dashArray}
                        strokeDashoffset={seg.dashOffset}
                        className="animate-xaku-ring transition-all duration-300 cursor-pointer"
                        onMouseEnter={() => setHoveredCategoryIdx(seg.idx)}
                        onMouseLeave={() => setHoveredCategoryIdx(null)}
                      />
                    ))}
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-center text-center pointer-events-none px-4">
                    <span className="text-[10px] text-faint font-medium">
                      {hoveredCategoryIdx !== null && categorySegments[hoveredCategoryIdx]
                        ? categorySegments[hoveredCategoryIdx].name
                        : "Total Spending"}
                    </span>
                    <span className="font-mono text-sm font-bold text-main mt-0.5">
                      {hoveredCategoryIdx !== null && categorySegments[hoveredCategoryIdx]
                        ? `${categorySegments[hoveredCategoryIdx].pct.toFixed(1)}%`
                        : totals.total_spending || "0.00"}
                    </span>
                    <span className="text-[10px] text-muted">{displayCurrency}</span>
                  </div>
                </div>

                <div className="space-y-3">
                  {categorySegments.map((seg) => (
                    <div
                      key={seg.name}
                      className={`space-y-1 p-1.5 rounded-lg transition-colors cursor-pointer ${
                        hoveredCategoryIdx === seg.idx ? "bg-[var(--surface-raised)]" : ""
                      }`}
                      onMouseEnter={() => setHoveredCategoryIdx(seg.idx)}
                      onMouseLeave={() => setHoveredCategoryIdx(null)}
                    >
                      <div className="flex items-center justify-between text-xs">
                        <span className="flex items-center gap-2 font-medium text-main">
                          <span
                            className="w-2.5 h-2.5 rounded-full shrink-0"
                            style={{ backgroundColor: seg.color }}
                          />
                          {seg.name}
                        </span>
                        <span className="font-mono text-muted">
                          {seg.amount} {displayCurrency} ({seg.pct}%)
                        </span>
                      </div>
                      <div className="h-1.5 w-full rounded-full bg-[var(--surface-raised)] overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all animate-xaku-bar"
                          style={{ width: `${seg.pct}%`, backgroundColor: seg.color }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {reportType === "cashflow" && (
            <div className="space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <Activity className="w-4 h-4 text-gold" />
                  <h3 className="text-sm font-semibold text-main">Cash Flow Efficiency &amp; Retention</h3>
                </div>
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-semibold bg-[var(--surface-raised)] border border-[var(--border)] text-main">
                  Savings Rate:{" "}
                  <span
                    className={
                      cashFlowStats.retentionRate >= 0
                        ? "text-[var(--positive)]"
                        : "text-[var(--negative)]"
                    }
                  >
                    {cashFlowStats.retentionRate.toFixed(1)}%
                  </span>
                </span>
              </div>

              <div className="space-y-3">
                <div className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="font-medium text-main">Operating Inflows</span>
                    <span className="font-mono text-[var(--positive)] font-semibold">
                      +{totals.inflows || "0.00"} {displayCurrency}
                    </span>
                  </div>
                  <div className="h-3 w-full rounded-lg bg-[var(--surface-raised)] overflow-hidden">
                    <div
                      className="h-full rounded-lg bg-[var(--positive)] transition-all duration-500"
                      style={{
                        width: `${Math.min(100, (cashFlowStats.inflows / cashFlowStats.maxMag) * 100)}%`,
                      }}
                    />
                  </div>
                </div>

                <div className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="font-medium text-main">Operating Outflows</span>
                    <span className="font-mono text-[var(--negative)] font-semibold">
                      {totals.outflows || "0.00"} {displayCurrency}
                    </span>
                  </div>
                  <div className="h-3 w-full rounded-lg bg-[var(--surface-raised)] overflow-hidden">
                    <div
                      className="h-full rounded-lg bg-[var(--negative)] transition-all duration-500"
                      style={{
                        width: `${Math.min(100, (cashFlowStats.outflows / cashFlowStats.maxMag) * 100)}%`,
                      }}
                    />
                  </div>
                </div>

                <div className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="font-medium text-main">Net Cash Retained</span>
                    <span className="font-mono text-gold font-semibold">
                      {totals.net_cash_flow || "0.00"} {displayCurrency}
                    </span>
                  </div>
                  <div className="h-3 w-full rounded-lg bg-[var(--surface-raised)] overflow-hidden">
                    <div
                      className={`h-full rounded-lg transition-all duration-500 ${
                        cashFlowStats.net >= 0 ? "bg-[var(--accent)]" : "bg-[var(--negative)]"
                      }`}
                      style={{
                        width: `${Math.min(100, (Math.abs(cashFlowStats.net) / cashFlowStats.maxMag) * 100)}%`,
                      }}
                    />
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Main Statement Data Table */}
      <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 shadow-sm">
        <h3 className="text-sm font-semibold text-main tracking-tight mb-4 flex items-center gap-2">
          <FileText className="w-4 h-4 text-gold" />
          Statement Breakdown
        </h3>

        {isLoading ? (
          <div className="h-40 flex items-center justify-center text-muted text-xs animate-pulse">
            Loading statement data...
          </div>
        ) : tableData.length === 0 ? (
          <div className="h-40 flex items-center justify-center text-muted text-xs">
            No transactions found for the selected period.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs min-w-[500px]" aria-label="Statement Table">
              <thead>
                <tr className="border-b border-[var(--border)] text-muted uppercase tracking-wider text-[10px] bg-[var(--surface-raised)]">
                  {reportType === "income_expense" && (
                    <>
                      <th className="py-2.5 px-3 font-semibold">Period</th>
                      <th className="py-2.5 px-3 font-semibold text-right">Income</th>
                      <th className="py-2.5 px-3 font-semibold text-right">Expense</th>
                      <th className="py-2.5 px-3 font-semibold text-right">Net</th>
                    </>
                  )}
                  {reportType === "cashflow" && (
                    <>
                      <th className="py-2.5 px-3 font-semibold">Cash Flow Item</th>
                      <th className="py-2.5 px-3 font-semibold text-right">Amount</th>
                    </>
                  )}
                  {reportType === "category" && (
                    <>
                      <th className="py-2.5 px-3 font-semibold">Category</th>
                      <th className="py-2.5 px-3 font-semibold text-right">Share (%)</th>
                      <th className="py-2.5 px-3 font-semibold text-right">Amount</th>
                    </>
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]">
                {tableData.map((row, idx) => (
                  <tr key={idx} className="hover:bg-[var(--surface-raised)] transition-colors">
                    {reportType === "income_expense" && (
                      <>
                        <td className="py-2.5 px-3 font-mono text-main">{row.period}</td>
                        <td className="py-2.5 px-3 font-mono text-right text-[var(--positive)]">
                          {row.income}
                        </td>
                        <td className="py-2.5 px-3 font-mono text-right text-[var(--negative)]">
                          {row.expense}
                        </td>
                        <td className="py-2.5 px-3 font-mono text-right font-medium text-main">
                          {row.net} {displayCurrency}
                        </td>
                      </>
                    )}
                    {reportType === "cashflow" && (
                      <>
                        <td className="py-2.5 px-3 font-medium text-main">{row.item}</td>
                        <td className="py-2.5 px-3 font-mono text-right font-medium text-main">
                          {row.amount} {displayCurrency}
                        </td>
                      </>
                    )}
                    {reportType === "category" && (
                      <>
                        <td className="py-2.5 px-3 font-medium text-main">
                          {row.category_name}
                        </td>
                        <td className="py-2.5 px-3 font-mono text-right text-muted">
                          {row.percentage}%
                        </td>
                        <td className="py-2.5 px-3 font-mono text-right font-medium text-main">
                          {row.amount} {displayCurrency}
                        </td>
                      </>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
