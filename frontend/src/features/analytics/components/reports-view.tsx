import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  FileText,
  Calendar,
  ArrowUpRight,
  ArrowDownRight,
  DollarSign,
  CheckCircle2,
  AlertTriangle,
} from "lucide-react";
import {
  fetchIncomeReport,
  fetchCashFlowReport,
  fetchCategoryReport,
} from "../api/analytics-api";
import { ReportResponse } from "../types";

interface ReportsViewProps {
  initialData?: ReportResponse;
  currency?: string;
}

export const ReportsView: React.FC<ReportsViewProps> = ({
  initialData,
  currency,
}) => {
  const [reportType, setReportType] = useState<"income_expense" | "cashflow" | "category">(
    "income_expense"
  );

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

  return (
    <div className="space-y-6">
      {/* Control bar */}
      <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* Report Kind Tabs */}
        <div className="flex items-center gap-1 rounded-lg border border-[var(--border)] bg-[var(--surface-raised)] p-1 text-xs overflow-x-auto">
          <button
            type="button"
            onClick={() => setReportType("income_expense")}
            className={`px-3 py-1.5 rounded font-medium transition-colors cursor-pointer whitespace-nowrap ${
              reportType === "income_expense"
                ? "bg-gold shadow-xs"
                : "text-muted hover:text-main"
            }`}
          >
            Income vs Expense
          </button>
          <button
            type="button"
            onClick={() => setReportType("cashflow")}
            className={`px-3 py-1.5 rounded font-medium transition-colors cursor-pointer whitespace-nowrap ${
              reportType === "cashflow"
                ? "bg-gold shadow-xs"
                : "text-muted hover:text-main"
            }`}
          >
            Cash Flow Statement
          </button>
          <button
            type="button"
            onClick={() => setReportType("category")}
            className={`px-3 py-1.5 rounded font-medium transition-colors cursor-pointer whitespace-nowrap ${
              reportType === "category"
                ? "bg-gold shadow-xs"
                : "text-muted hover:text-main"
            }`}
          >
            Category Breakdown
          </button>
        </div>

        {/* Date Filters */}
        <div className="flex items-center gap-2 text-xs">
          <div className="flex items-center gap-1.5 bg-[var(--surface-raised)] border border-[var(--border)] rounded-lg px-2.5 py-1 text-main">
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
                {totals.income || "0.00"}{" "}
                <span className="text-xs text-muted font-sans">{displayCurrency}</span>
              </div>
            </div>
            <div className="rounded-xl border border-[var(--negative-border)] bg-[var(--negative-bg)] p-4">
              <div className="flex items-center justify-between text-xs text-muted mb-1">
                <span>Total Expenses</span>
                <ArrowDownRight className="w-4 h-4 text-[var(--negative)]" />
              </div>
              <div className="font-mono text-2xl font-bold text-[var(--negative)]">
                {totals.expense || "0.00"}{" "}
                <span className="text-xs text-muted font-sans">{displayCurrency}</span>
              </div>
            </div>
            <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
              <div className="flex items-center justify-between text-xs text-muted mb-1">
                <span>Net Savings</span>
                <DollarSign className="w-4 h-4 text-gold" />
              </div>
              <div className="font-mono text-2xl font-bold text-main">
                {totals.net || "0.00"}{" "}
                <span className="text-xs text-muted font-sans">{displayCurrency}</span>
              </div>
            </div>
          </>
        )}

        {reportType === "cashflow" && (
          <>
            <div className="rounded-xl border border-[var(--positive-border)] bg-[var(--positive-bg)] p-4">
              <div className="text-xs text-muted mb-1">Operating Inflows</div>
              <div className="font-mono text-2xl font-bold text-[var(--positive)]">
                {totals.inflows || "0.00"}{" "}
                <span className="text-xs text-muted font-sans">{displayCurrency}</span>
              </div>
            </div>
            <div className="rounded-xl border border-[var(--negative-border)] bg-[var(--negative-bg)] p-4">
              <div className="text-xs text-muted mb-1">Operating Outflows</div>
              <div className="font-mono text-2xl font-bold text-[var(--negative)]">
                {totals.outflows || "0.00"}{" "}
                <span className="text-xs text-muted font-sans">{displayCurrency}</span>
              </div>
            </div>
            <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
              <div className="text-xs text-muted mb-1">Net Cash Movement</div>
              <div className="font-mono text-2xl font-bold text-main">
                {totals.net_cash_flow || "0.00"}{" "}
                <span className="text-xs text-muted font-sans">{displayCurrency}</span>
              </div>
            </div>
          </>
        )}

        {reportType === "category" && (
          <div className="sm:col-span-3 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
            <div className="text-xs text-muted mb-1">Total Category Spending</div>
            <div className="font-mono text-2xl font-bold text-main">
              {totals.total_spending || "0.00"}{" "}
              <span className="text-xs text-muted font-sans">{displayCurrency}</span>
            </div>
          </div>
        )}
      </div>

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
