import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  FileText,
  CheckCircle2,
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  DollarSign,
  Calendar,
} from "lucide-react";
import {
  fetchCategoryReport,
  fetchCashFlowReport,
  fetchIncomeReport,
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
      <div className="rounded-xl border border-[#2b313a] bg-[#181a20] p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* Report Kind Tabs */}
        <div className="flex items-center gap-1 rounded-lg border border-[#2b313a] bg-slate-900/60 p-1 text-xs">
          <button
            type="button"
            onClick={() => setReportType("income_expense")}
            className={`px-3 py-1.5 rounded font-medium transition-colors cursor-pointer ${
              reportType === "income_expense"
                ? "bg-amber-400 text-black font-semibold"
                : "text-slate-400 hover:text-white"
            }`}
          >
            Income vs Expense
          </button>
          <button
            type="button"
            onClick={() => setReportType("cashflow")}
            className={`px-3 py-1.5 rounded font-medium transition-colors cursor-pointer ${
              reportType === "cashflow"
                ? "bg-amber-400 text-black font-semibold"
                : "text-slate-400 hover:text-white"
            }`}
          >
            Cash Flow Statement
          </button>
          <button
            type="button"
            onClick={() => setReportType("category")}
            className={`px-3 py-1.5 rounded font-medium transition-colors cursor-pointer ${
              reportType === "category"
                ? "bg-amber-400 text-black font-semibold"
                : "text-slate-400 hover:text-white"
            }`}
          >
            Category Breakdown
          </button>
        </div>

        {/* Date Filters */}
        <div className="flex items-center gap-2 text-xs">
          <div className="flex items-center gap-1.5 bg-slate-900/60 border border-[#2b313a] rounded-lg px-2.5 py-1 text-slate-300">
            <Calendar className="w-3.5 h-3.5 text-slate-400" />
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="bg-transparent text-white focus:outline-none"
              aria-label="Report start date"
            />
            <span className="text-slate-500">to</span>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="bg-transparent text-white focus:outline-none"
              aria-label="Report end date"
            />
          </div>
        </div>
      </div>

      {/* Ledger Reconciliation Verification Banner */}
      {recon && (
        <div
          className={`rounded-xl border p-4 text-xs flex items-center justify-between gap-3 ${
            isReconciled
              ? "border-emerald-500/20 bg-emerald-500/5 text-emerald-400"
              : "border-rose-500/20 bg-rose-500/5 text-rose-400"
          }`}
        >
          <div className="flex items-center gap-2">
            {isReconciled ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            ) : (
              <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
            )}
            <span>
              <strong>Double-Entry Ledger Integrity:</strong>{" "}
              {isReconciled
                ? `Report verified against ledger postings (difference: ${recon.difference} ${displayCurrency})`
                : `Discrepancy detected: ledger differs from reported transactions by ${recon.difference} ${displayCurrency}`}
            </span>
          </div>
          <span className="font-mono text-[10px] text-slate-500 hidden sm:inline">
            Checked: {recon.checked_at.slice(0, 19)}
          </span>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {reportType === "income_expense" && (
          <>
            <div className="rounded-xl border border-emerald-500/20 bg-[#181a20] p-4">
              <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
                <span>Total Income</span>
                <ArrowUpRight className="w-4 h-4 text-emerald-400" />
              </div>
              <div className="font-mono text-2xl font-bold text-emerald-400">
                {totals.income || "0.00"}{" "}
                <span className="text-xs text-slate-500 font-sans">{displayCurrency}</span>
              </div>
            </div>
            <div className="rounded-xl border border-rose-500/20 bg-[#181a20] p-4">
              <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
                <span>Total Expenses</span>
                <ArrowDownRight className="w-4 h-4 text-rose-400" />
              </div>
              <div className="font-mono text-2xl font-bold text-rose-400">
                {totals.expense || "0.00"}{" "}
                <span className="text-xs text-slate-500 font-sans">{displayCurrency}</span>
              </div>
            </div>
            <div className="rounded-xl border border-amber-500/20 bg-[#181a20] p-4">
              <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
                <span>Net Savings</span>
                <DollarSign className="w-4 h-4 text-amber-400" />
              </div>
              <div className="font-mono text-2xl font-bold text-white">
                {totals.net || "0.00"}{" "}
                <span className="text-xs text-slate-500 font-sans">{displayCurrency}</span>
              </div>
            </div>
          </>
        )}

        {reportType === "cashflow" && (
          <>
            <div className="rounded-xl border border-emerald-500/20 bg-[#181a20] p-4">
              <div className="text-xs text-slate-400 mb-1">Operating Inflows</div>
              <div className="font-mono text-2xl font-bold text-emerald-400">
                {totals.inflows || "0.00"}{" "}
                <span className="text-xs text-slate-500 font-sans">{displayCurrency}</span>
              </div>
            </div>
            <div className="rounded-xl border border-rose-500/20 bg-[#181a20] p-4">
              <div className="text-xs text-slate-400 mb-1">Operating Outflows</div>
              <div className="font-mono text-2xl font-bold text-rose-400">
                {totals.outflows || "0.00"}{" "}
                <span className="text-xs text-slate-500 font-sans">{displayCurrency}</span>
              </div>
            </div>
            <div className="rounded-xl border border-amber-500/20 bg-[#181a20] p-4">
              <div className="text-xs text-slate-400 mb-1">Net Cash Movement</div>
              <div className="font-mono text-2xl font-bold text-white">
                {totals.net_cash_flow || "0.00"}{" "}
                <span className="text-xs text-slate-500 font-sans">{displayCurrency}</span>
              </div>
            </div>
          </>
        )}

        {reportType === "category" && (
          <div className="sm:col-span-3 rounded-xl border border-amber-500/20 bg-[#181a20] p-4">
            <div className="text-xs text-slate-400 mb-1">Total Category Spending</div>
            <div className="font-mono text-2xl font-bold text-amber-300">
              {totals.total_spending || "0.00"}{" "}
              <span className="text-xs text-slate-500 font-sans">{displayCurrency}</span>
            </div>
          </div>
        )}
      </div>

      {/* Main Statement Data Table */}
      <div className="rounded-xl border border-[#2b313a] bg-[#181a20] p-6 shadow-sm">
        <h3 className="text-sm font-semibold text-white tracking-tight mb-4 flex items-center gap-2">
          <FileText className="w-4 h-4 text-amber-400" />
          Statement Breakdown
        </h3>

        {isLoading ? (
          <div className="h-40 flex items-center justify-center text-slate-500 text-xs animate-pulse">
            Loading statement data...
          </div>
        ) : tableData.length === 0 ? (
          <div className="h-40 flex items-center justify-center text-slate-500 text-xs">
            No transactions found for the selected period.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs" aria-label="Statement Table">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 uppercase tracking-wider text-[10px]">
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
              <tbody className="divide-y divide-slate-800/60">
                {tableData.map((row, idx) => (
                  <tr key={idx} className="hover:bg-slate-900/40">
                    {reportType === "income_expense" && (
                      <>
                        <td className="py-2.5 px-3 font-mono text-slate-200">{row.period}</td>
                        <td className="py-2.5 px-3 font-mono text-right text-emerald-400">
                          {row.income}
                        </td>
                        <td className="py-2.5 px-3 font-mono text-right text-rose-400">
                          {row.expense}
                        </td>
                        <td className="py-2.5 px-3 font-mono text-right font-medium text-white">
                          {row.net} {displayCurrency}
                        </td>
                      </>
                    )}
                    {reportType === "cashflow" && (
                      <>
                        <td className="py-2.5 px-3 font-medium text-slate-200">{row.item}</td>
                        <td className="py-2.5 px-3 font-mono text-right font-medium text-white">
                          {row.amount} {displayCurrency}
                        </td>
                      </>
                    )}
                    {reportType === "category" && (
                      <>
                        <td className="py-2.5 px-3 font-medium text-slate-200">
                          {row.category_name}
                        </td>
                        <td className="py-2.5 px-3 font-mono text-right text-slate-400">
                          {row.percentage}%
                        </td>
                        <td className="py-2.5 px-3 font-mono text-right font-medium text-amber-300">
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
