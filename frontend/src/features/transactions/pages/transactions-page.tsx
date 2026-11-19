import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Plus, Search, Filter } from "lucide-react";
import { getTransactions } from "../api";
import { Transaction } from "../types";
import { TransactionsTable } from "../components/transactions-table";
import { CreateTransactionDrawer } from "../components/create-transaction-drawer";
import { TransactionAuditDrawer } from "../components/transaction-audit-drawer";
import { getAccounts } from "@/features/accounts/api";
import { queryKeys } from "@/lib/query-keys";

export const TransactionsPage: React.FC = () => {
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [selectedTx, setSelectedTx] = useState<Transaction | null>(null);
  const [accountId, setAccountId] = useState("");
  const [status, setStatus] = useState("");
  const [searchQuery, setSearchQuery] = useState("");

  const { data: accounts = [] } = useQuery({
    queryKey: queryKeys.accounts.list(false),
    queryFn: () => getAccounts(false),
  });

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.transactions.list({
      account_id: accountId || undefined,
      status: status || undefined,
      q: searchQuery.trim() || undefined,
    }),
    queryFn: () =>
      getTransactions({
        account_id: accountId || undefined,
        status: status || undefined,
        q: searchQuery.trim() || undefined,
      }),
  });

  const transactions = data?.results || [];

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

        <button
          onClick={() => setIsCreateOpen(true)}
          className="flex items-center gap-2 rounded bg-gold px-3.5 py-2 text-xs font-semibold cursor-pointer shadow-sm"
        >
          <Plus className="w-4 h-4" />
          Record Transaction
        </button>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center gap-3 bg-[var(--surface)] border border-[var(--border)] p-3 rounded-lg text-xs">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="w-3.5 h-3.5 text-muted absolute left-2.5 top-2.5" />
          <input
            type="text"
            placeholder="Search by title, merchant, or notes..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded bg-[var(--surface-raised)] border border-[var(--border)] pl-8 pr-3 py-1.5 text-xs text-main focus:border-[var(--accent)] focus:outline-none"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
          <Filter className="w-3.5 h-3.5 text-muted" />
          <select
            value={accountId}
            onChange={(e) => setAccountId(e.target.value)}
            className="rounded bg-[var(--surface-raised)] border border-[var(--border)] px-2.5 py-1.5 text-xs text-main focus:border-[var(--accent)] focus:outline-none"
          >
            <option value="">All Accounts</option>
            {accounts.map((acc) => (
              <option key={acc.id} value={acc.id}>
                {acc.name} ({acc.currency})
              </option>
            ))}
          </select>

          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="rounded bg-[var(--surface-raised)] border border-[var(--border)] px-2.5 py-1.5 text-xs text-main focus:border-[var(--accent)] focus:outline-none"
          >
            <option value="">All Statuses</option>
            <option value="completed">Completed</option>
            <option value="pending">Pending</option>
            <option value="cancelled">Cancelled</option>
          </select>
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
      />
    </div>
  );
};
