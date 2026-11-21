import React, { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { Plus, Search, Filter, Download, Calendar, ArrowDownRight, ArrowUpRight, Layers } from "lucide-react";
import { getTransactions } from "../api";
import { Transaction } from "../types";
import { TransactionsTable } from "../components/transactions-table";
import { CreateTransactionDrawer } from "../components/create-transaction-drawer";
import { TransactionAuditDrawer } from "../components/transaction-audit-drawer";
import { getAccounts } from "@/features/accounts/api";
import { fetchCategories } from "@/features/categories/api";
import { queryKeys } from "@/lib/query-keys";
import { formatMoney } from "@/lib/money";

function escapeCsvCell(val: unknown): string {
  const s = String(val ?? "");
  if (/[",\n]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
  return s;
}

export const TransactionsPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [selectedTx, setSelectedTx] = useState<Transaction | null>(null);
  const [accountId, setAccountId] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [status, setStatus] = useState("");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [includeArchived, setIncludeArchived] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    if (searchParams.get("action") === "new") {
      setIsCreateOpen(true);
      const next = new URLSearchParams(searchParams);
      next.delete("action");
      setSearchParams(next, { replace: true });
    }
  }, [searchParams, setSearchParams]);

  const { data: accounts = [] } = useQuery({
    queryKey: queryKeys.accounts.list(false),
    queryFn: () => getAccounts(false),
  });

  const { data: categories = [] } = useQuery({
    queryKey: ["categories"],
    queryFn: fetchCategories,
  });

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.transactions.list({
      account_id: accountId || undefined,
      category_id: categoryId || undefined,
      status: status || undefined,
      from: fromDate || undefined,
      to: toDate || undefined,
      include_archived: includeArchived || undefined,
      q: searchQuery.trim() || undefined,
    }),
    queryFn: () =>
      getTransactions({
        account_id: accountId || undefined,
        category_id: categoryId || undefined,
        status: status || undefined,
        from: fromDate || undefined,
        to: toDate || undefined,
        include_archived: includeArchived || undefined,
        q: searchQuery.trim() || undefined,
      }),
  });

  const transactions = data?.results || [];

  const summary = useMemo(() => {
    let inflowsMinor = 0;
    let outflowsMinor = 0;
    const currencies = new Set<string>();

    for (const tx of transactions) {
      if (tx.is_archived) continue;
      currencies.add(tx.currency);
      if (tx.type === "income") {
        inflowsMinor += Math.abs(tx.amount_minor);
      } else if (tx.type === "expense") {
        outflowsMinor += Math.abs(tx.amount_minor);
      }
    }

    const primaryCurrency = currencies.size === 1 ? Array.from(currencies)[0] : "USD";
    const isMultiCurrency = currencies.size > 1;
    const netMinor = inflowsMinor - outflowsMinor;

    return {
      count: transactions.length,
      inflowsMinor,
      outflowsMinor,
      netMinor,
      currency: primaryCurrency,
      isMultiCurrency,
    };
  }, [transactions]);

  const handleExportCsv = () => {
    if (transactions.length === 0) return;
    const headers = [
      "Date",
      "Title",
      "Merchant",
      "Account",
      "Category",
      "Type",
      "Status",
      "Amount",
      "Currency",
      "Version",
    ];
    const rows = transactions.map((tx) => [
      tx.occurred_on,
      tx.title,
      tx.merchant || "",
      tx.account_name,
      tx.is_split ? `${tx.splits.length} splits` : tx.category_name || "Uncategorized",
      tx.type,
      tx.status,
      tx.amount,
      tx.currency,
      `v${tx.version}`,
    ]);
    const csv = [headers, ...rows].map((row) => row.map(escapeCsvCell).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", "xakufinance-transactions.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-[var(--border)] pb-4">
        <div>
          <h1 className="font-display text-2xl font-semibold text-main tracking-tight">
            Transactions Register
          </h1>
          <p className="text-xs text-muted mt-1">
            Immutable journal entries with versioned audit trails and multi-category splits.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={handleExportCsv}
            disabled={transactions.length === 0}
            className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] hover:bg-[var(--surface-raised)] px-3 py-2 text-xs font-medium text-main cursor-pointer transition-colors disabled:opacity-40"
          >
            <Download className="w-3.5 h-3.5 text-gold" />
            Export CSV
          </button>

          <button
            onClick={() => setIsCreateOpen(true)}
            className="flex items-center gap-2 rounded-lg bg-gold px-3.5 py-2 text-xs font-semibold cursor-pointer shadow-sm"
          >
            <Plus className="w-4 h-4" />
            Record Transaction
          </button>
        </div>
      </div>

      {/* Summary Metrics Bar */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
          <div className="flex items-center justify-between text-xs text-muted mb-1">
            <span>Visible Entries</span>
            <Layers className="w-3.5 h-3.5 text-gold" />
          </div>
          <div className="font-mono text-xl font-bold text-main">
            {summary.count}
            {data?.has_more && (
              <span className="text-[11px] font-normal text-faint ml-1.5">+ more</span>
            )}
          </div>
        </div>

        <div className="rounded-xl border border-[var(--positive-border)] bg-[var(--positive-bg)] p-4">
          <div className="flex items-center justify-between text-xs text-muted mb-1">
            <span>Total Inflows</span>
            <ArrowDownRight className="w-3.5 h-3.5 text-[var(--positive)]" />
          </div>
          <div className="font-mono text-xl font-bold text-[var(--positive)]">
            {formatMoney(summary.inflowsMinor, summary.currency)}
          </div>
          {summary.isMultiCurrency && (
            <div className="text-[10px] text-faint mt-0.5">Mixed currencies</div>
          )}
        </div>

        <div className="rounded-xl border border-[var(--negative-border)] bg-[var(--negative-bg)] p-4">
          <div className="flex items-center justify-between text-xs text-muted mb-1">
            <span>Total Outflows</span>
            <ArrowUpRight className="w-3.5 h-3.5 text-[var(--negative)]" />
          </div>
          <div className="font-mono text-xl font-bold text-[var(--negative)]">
            {formatMoney(summary.outflowsMinor, summary.currency)}
          </div>
          {summary.isMultiCurrency && (
            <div className="text-[10px] text-faint mt-0.5">Mixed currencies</div>
          )}
        </div>

        <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
          <div className="text-xs text-muted mb-1">Net Register Flow</div>
          <div
            className={`font-mono text-xl font-bold ${
              summary.netMinor >= 0 ? "text-[var(--positive)]" : "text-[var(--negative)]"
            }`}
          >
            {summary.netMinor >= 0 ? "+" : ""}
            {formatMoney(summary.netMinor, summary.currency)}
          </div>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center gap-3 bg-[var(--surface)] border border-[var(--border)] p-3 rounded-xl text-xs">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="w-3.5 h-3.5 text-muted absolute left-2.5 top-2.5" />
          <input
            type="text"
            placeholder="Search by title, merchant, or notes..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-lg bg-[var(--surface-raised)] border border-[var(--border)] pl-8 pr-3 py-1.5 text-xs text-main focus:border-[var(--accent)] focus:outline-none"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2 w-full lg:w-auto">
          <Filter className="w-3.5 h-3.5 text-muted shrink-0" />
          <select
            value={accountId}
            onChange={(e) => setAccountId(e.target.value)}
            aria-label="Filter by account"
            className="rounded-lg bg-[var(--surface-raised)] border border-[var(--border)] px-2.5 py-1.5 text-xs text-main focus:border-[var(--accent)] focus:outline-none"
          >
            <option value="">All Accounts</option>
            {accounts.map((acc) => (
              <option key={acc.id} value={acc.id}>
                {acc.name} ({acc.currency})
              </option>
            ))}
          </select>

          <select
            value={categoryId}
            onChange={(e) => setCategoryId(e.target.value)}
            aria-label="Filter by category"
            className="rounded-lg bg-[var(--surface-raised)] border border-[var(--border)] px-2.5 py-1.5 text-xs text-main focus:border-[var(--accent)] focus:outline-none"
          >
            <option value="">All Categories</option>
            {categories.map((cat) => (
              <option key={cat.id} value={cat.id}>
                {cat.name}
              </option>
            ))}
          </select>

          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            aria-label="Filter by status"
            className="rounded-lg bg-[var(--surface-raised)] border border-[var(--border)] px-2.5 py-1.5 text-xs text-main focus:border-[var(--accent)] focus:outline-none"
          >
            <option value="">All Statuses</option>
            <option value="completed">Completed</option>
            <option value="pending">Pending</option>
            <option value="cancelled">Cancelled</option>
          </select>

          <div className="flex items-center gap-1.5 rounded-lg bg-[var(--surface-raised)] border border-[var(--border)] px-2 py-1">
            <Calendar className="w-3.5 h-3.5 text-muted shrink-0" />
            <input
              type="date"
              value={fromDate}
              onChange={(e) => setFromDate(e.target.value)}
              aria-label="From date"
              className="bg-transparent text-xs text-main focus:outline-none"
            />
            <span className="text-muted">to</span>
            <input
              type="date"
              value={toDate}
              onChange={(e) => setToDate(e.target.value)}
              aria-label="To date"
              className="bg-transparent text-xs text-main focus:outline-none"
            />
          </div>

          <label className="flex items-center gap-1.5 text-xs text-muted cursor-pointer select-none px-1.5">
            <input
              type="checkbox"
              checked={includeArchived}
              onChange={(e) => setIncludeArchived(e.target.checked)}
              className="rounded border-[var(--border)] bg-[var(--surface)] accent-[var(--accent)]"
            />
            Show Archived
          </label>
        </div>
      </div>

      {/* Transactions Table */}
      <TransactionsTable
        transactions={transactions}
        isLoading={isLoading}
        onSelectTransaction={(tx) => setSelectedTx(tx)}
      />

      <CreateTransactionDrawer
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
      />

      <TransactionAuditDrawer
        transaction={selectedTx}
        isOpen={!!selectedTx}
        onClose={() => setSelectedTx(null)}
        onTransactionUpdated={(updated) => {
          if (updated.is_archived && !includeArchived) {
            setSelectedTx(null);
          } else {
            setSelectedTx(updated);
          }
        }}
      />
    </div>
  );
};
