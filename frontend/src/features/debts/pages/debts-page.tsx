import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { CreditCard, Plus, ShieldCheck } from "lucide-react";
import { fetchLiabilities, Liability } from "../api/debts-api";
import { DebtCard } from "../components/debt-card";
import { CreateDebtDialog } from "../components/create-debt-dialog";
import { RepaymentDialog } from "../components/repayment-dialog";
import { DebtProjectionModal } from "../components/debt-projection-card";
import { getAccounts } from "@/features/accounts/api";
import { queryKeys } from "@/lib/query-keys";

export const DebtsPage: React.FC = () => {
  const [includeArchived, setIncludeArchived] = useState(false);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [selectedLiability, setSelectedLiability] = useState<Liability | null>(null);
  const [repaymentOpen, setRepaymentOpen] = useState(false);
  const [projectionLiability, setProjectionLiability] = useState<Liability | null>(null);
  const [projectionOpen, setProjectionOpen] = useState(false);

  const { data: liabilities = [], isLoading } = useQuery({
    queryKey: ["debts", includeArchived],
    queryFn: () => fetchLiabilities(includeArchived),
  });

  const { data: accounts = [] } = useQuery({
    queryKey: queryKeys.accounts.list(false),
    queryFn: () => getAccounts(false),
  });

  // Metrics
  const totalOutstandingMinor = liabilities.reduce(
    (sum, l) => sum + l.outstanding_principal_minor,
    0
  );
  const totalOriginalMinor = liabilities.reduce(
    (sum, l) => sum + l.original_principal_minor,
    0
  );
  const totalPaidMinor = liabilities.reduce(
    (sum, l) => sum + l.paid_principal_minor,
    0
  );
  const activeCount = liabilities.filter(
    (l) => l.status === "active" && l.outstanding_principal_minor > 0
  ).length;

  const handleRepay = (liability: Liability) => {
    setSelectedLiability(liability);
    setRepaymentOpen(true);
  };

  const handleViewProjection = (liability: Liability) => {
    setProjectionLiability(liability);
    setProjectionOpen(true);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto p-4 md:p-6 animate-fade-in">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-main flex items-center gap-2">
            <CreditCard className="w-6 h-6 text-gold" />
            Debts & Liabilities
          </h1>
          <p className="text-sm text-muted">
            Track outstanding principal derived from double-entry ledger postings with repayment split analytics.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          <label className="flex items-center gap-2 text-xs text-muted cursor-pointer select-none">
            <input
              type="checkbox"
              checked={includeArchived}
              onChange={(e) => setIncludeArchived(e.target.checked)}
              className="rounded-sm border-[var(--border)] text-gold focus:ring-gold"
            />
            Show archived
          </label>
          <button
            onClick={() => setCreateDialogOpen(true)}
            data-testid="create-debt-btn"
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gold font-semibold shadow-xs text-sm hover:brightness-110 shadow-sm cursor-pointer transition-all"
          >
            <Plus className="w-4 h-4" />
            Add Liability
          </button>
        </div>
      </div>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl border border-[var(--border)] bg-[var(--surface)]">
          <div className="text-xs text-muted font-medium mb-1">Total Outstanding</div>
          <div className="text-2xl font-bold text-[var(--negative)] font-mono">
            ${(totalOutstandingMinor / 100).toLocaleString(undefined, { minimumFractionDigits: 2 })}
          </div>
        </div>
        <div className="p-4 rounded-xl border border-[var(--border)] bg-[var(--surface)]">
          <div className="text-xs text-muted font-medium mb-1">Total Principal Borrowed</div>
          <div className="text-2xl font-bold text-main font-mono">
            ${(totalOriginalMinor / 100).toLocaleString(undefined, { minimumFractionDigits: 2 })}
          </div>
        </div>
        <div className="p-4 rounded-xl border border-[var(--border)] bg-[var(--surface)]">
          <div className="text-xs text-muted font-medium mb-1">Total Repaid</div>
          <div className="text-2xl font-bold text-[var(--positive)] font-mono">
            ${(totalPaidMinor / 100).toLocaleString(undefined, { minimumFractionDigits: 2 })}
          </div>
        </div>
        <div className="p-4 rounded-xl border border-[var(--border)] bg-[var(--surface)]">
          <div className="text-xs text-muted font-medium mb-1">Active Loans</div>
          <div className="text-2xl font-bold text-main">{activeCount}</div>
        </div>
      </div>

      {/* Liabilities Grid */}
      {isLoading ? (
        <div className="py-12 text-center text-muted">Loading debts...</div>
      ) : liabilities.length === 0 ? (
        <div className="py-16 text-center border border-dashed border-[var(--border)] rounded-2xl p-8">
          <div className="p-3 w-fit mx-auto rounded-full bg-[var(--positive-bg)] border border-[var(--positive-border)] text-[var(--positive)] mb-3">
            <ShieldCheck className="w-8 h-8" />
          </div>
          <h3 className="font-semibold text-lg text-main mb-1">Debt-Free!</h3>
          <p className="text-sm text-muted max-w-sm mx-auto mb-4">
            You currently have no active liabilities recorded in this workspace.
          </p>
          <button
            onClick={() => setCreateDialogOpen(true)}
            className="px-4 py-2 rounded-xl bg-gold font-semibold shadow-xs text-sm hover:brightness-110 cursor-pointer"
          >
            Add Liability
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {liabilities.map((liability) => (
            <DebtCard
              key={liability.id}
              liability={liability}
              onRepay={handleRepay}
              onViewProjection={handleViewProjection}
            />
          ))}
        </div>
      )}

      {/* Dialogs */}
      <CreateDebtDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        accounts={accounts}
      />
      <RepaymentDialog
        liability={selectedLiability}
        open={repaymentOpen}
        onOpenChange={setRepaymentOpen}
        accounts={accounts}
      />
      <DebtProjectionModal
        liability={projectionLiability}
        open={projectionOpen}
        onOpenChange={setProjectionOpen}
      />
    </div>
  );
};
