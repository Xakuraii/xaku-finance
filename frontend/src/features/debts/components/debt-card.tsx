import React from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Building2,
  Calendar,
  Sparkles,
  TrendingDown,
  RotateCcw,
  Archive,
  ArrowDownRight,
} from "lucide-react";
import { Liability, archiveLiability, restoreLiability } from "../api/debts-api";

interface DebtCardProps {
  liability: Liability;
  onRepay: (liability: Liability) => void;
  onViewProjection?: (liability: Liability) => void;
}

export const DebtCard: React.FC<DebtCardProps> = ({
  liability,
  onRepay,
  onViewProjection,
}) => {
  const queryClient = useQueryClient();

  const archiveMutation = useMutation({
    mutationFn: () => archiveLiability(liability.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["debts"] });
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
    },
  });

  const restoreMutation = useMutation({
    mutationFn: () => restoreLiability(liability.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["debts"] });
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
    },
  });

  const isPaidOff = liability.status === "paid_off" || liability.outstanding_principal_minor === 0;
  const isArchived = liability.is_archived;

  return (
    <div
      data-testid={`debt-card-${liability.id}`}
      className={`rounded-xl border p-5 text-main shadow-xs relative overflow-hidden transition-all ${
        isArchived
          ? "border-[var(--border)] opacity-60 bg-[var(--surface-muted)]"
          : "border-[var(--border)] bg-[var(--surface)] hover:border-[var(--border-strong)]"
      }`}
    >
      {/* Top Header */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div>
          <div className="flex items-center gap-2">
            <h4 className="font-semibold text-base text-main">{liability.name}</h4>
            {isPaidOff && (
              <span
                data-testid="paid-off-pill"
                className="inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
              >
                <Sparkles className="w-3 h-3" />
                Paid Off
              </span>
            )}
            {liability.interest_rate && (
              <span className="text-[11px] font-medium px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">
                {parseFloat(liability.interest_rate)}% APR
              </span>
            )}
            {isArchived && (
              <span className="text-[11px] font-medium px-2 py-0.5 rounded-full bg-zinc-700 text-zinc-300">
                Archived
              </span>
            )}
          </div>
          <div className="flex items-center gap-3 text-xs text-muted mt-1">
            <span className="capitalize">{liability.liability_type.replace("_", " ")}</span>
            {liability.lender && (
              <span className="flex items-center gap-1">
                <Building2 className="w-3 h-3 text-gold" />
                {liability.lender}
              </span>
            )}
            {liability.next_due_date && (
              <span className="flex items-center gap-1">
                <Calendar className="w-3 h-3" />
                Due {liability.next_due_date}
              </span>
            )}
          </div>
        </div>

        {/* Action icons */}
        <div className="flex items-center gap-1">
          {onViewProjection && (
            <button
              onClick={() => onViewProjection(liability)}
              title="View payoff projection"
              className="p-1.5 rounded-md hover:bg-[var(--surface-hover)] text-muted hover:text-gold transition-colors"
            >
              <TrendingDown className="w-4 h-4" />
            </button>
          )}
          {isArchived ? (
            <button
              onClick={() => restoreMutation.mutate()}
              title="Restore liability"
              className="p-1.5 rounded-md hover:bg-[var(--surface-hover)] text-muted hover:text-main transition-colors"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          ) : (
            <button
              onClick={() => archiveMutation.mutate()}
              title="Archive liability"
              className="p-1.5 rounded-md hover:bg-[var(--surface-hover)] text-muted hover:text-red-400 transition-colors"
            >
              <Archive className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Outstanding & Progress */}
      <div className="space-y-2 mb-4">
        <div className="flex items-baseline justify-between">
          <div>
            <div className="text-[11px] text-muted">Outstanding Balance</div>
            <span className="text-xl font-bold text-main font-mono">
              ${liability.outstanding_principal}{" "}
              <span className="text-xs font-normal text-muted">{liability.currency}</span>
            </span>
          </div>
          <div className="text-right">
            <div className="text-[11px] text-muted">Original Principal</div>
            <span className="text-xs text-muted font-mono">
              ${liability.original_principal} {liability.currency}
            </span>
          </div>
        </div>

        {/* Progress bar (Repaid %) */}
        <div className="w-full h-2 rounded-full bg-[var(--surface-muted)] overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-emerald-500 to-emerald-400 transition-all duration-500"
            style={{ width: `${Math.min(100, liability.progress_percent)}%` }}
          />
        </div>

        <div className="flex justify-between text-xs text-muted">
          <span>{liability.progress_percent.toFixed(1)}% repaid</span>
          <span>${liability.paid_principal} paid</span>
        </div>
      </div>

      {/* Card Action footer */}
      {!isArchived && !isPaidOff && (
        <div className="pt-3 border-t border-[var(--border)] flex justify-end">
          <button
            onClick={() => onRepay(liability)}
            data-testid={`repay-btn-${liability.id}`}
            className="flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg bg-gold/10 text-gold border border-gold/30 hover:bg-gold/20 transition-all cursor-pointer"
          >
            <ArrowDownRight className="w-3.5 h-3.5" />
            Record Repayment
          </button>
        </div>
      )}
    </div>
  );
};
