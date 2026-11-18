import React from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  Lock,
  Sparkles,
} from "lucide-react";
import { Budget } from "../types";
import { closeBudgetPeriod } from "../api/budgets-api";

interface BudgetCardProps {
  budget: Budget;
  onEdit?: (budget: Budget) => void;
}

export const BudgetCard: React.FC<BudgetCardProps> = ({ budget }) => {
  const queryClient = useQueryClient();
  const period = budget.current_period;

  const closeMutation = useMutation({
    mutationFn: () => closeBudgetPeriod(budget.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["budgets"] });
    },
  });

  const spentPercent = period?.spent_percentage ?? 0;
  const health = period?.health_status ?? "on_track";
  const currency = budget.currency;

  // Determine progress bar style based on health state
  let progressColor = "bg-gradient-to-r from-[#F0B90B] to-[#FCD535]";
  if (health === "over_budget") {
    progressColor = "bg-red-500";
  } else if (health === "alert") {
    progressColor = "bg-orange-500";
  } else if (health === "warning") {
    progressColor = "bg-amber-400";
  }

  const isOverBudget = health === "over_budget";
  const hasRollover = (period?.rollover_in_minor ?? 0) > 0;

  return (
    <div
      data-testid={`budget-card-${budget.id}`}
      className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5 text-main shadow-xs relative overflow-hidden transition-all hover:border-[var(--border-strong)]"
    >
      {/* Top row: Name, Category, and Status pill */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div>
          <div className="flex items-center gap-2">
            <h4 className="font-semibold text-base text-main">{budget.name}</h4>
            {hasRollover && (
              <span
                data-testid="rollover-pill"
                className="inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full bg-gold/10 text-gold border border-gold/30"
              >
                <Sparkles className="w-3 h-3" />
                +{period?.rollover_in} {currency} rollover
              </span>
            )}
          </div>
          <p className="text-xs text-muted mt-0.5">
            Category: <span className="text-main font-medium">{budget.category.name}</span>
            <span className="mx-1.5">•</span>
            <span className="capitalize">{budget.period_type}</span>
          </p>
        </div>

        {/* Health state badge */}
        <div>
          {health === "over_budget" && (
            <span
              data-testid="badge-over-budget"
              className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded-md bg-red-500/10 text-negative border border-red-500/30"
            >
              <AlertTriangle className="w-3.5 h-3.5" />
              Over Budget
            </span>
          )}
          {health === "alert" && (
            <span
              data-testid="badge-alert"
              className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded-md bg-orange-500/10 text-warning border border-orange-500/30"
            >
              <AlertTriangle className="w-3.5 h-3.5" />
              Alert (100%)
            </span>
          )}
          {health === "warning" && (
            <span
              data-testid="badge-warning"
              className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded-md bg-amber-500/10 text-warning border border-amber-500/30"
            >
              <AlertTriangle className="w-3.5 h-3.5" />
              Warning (80%)
            </span>
          )}
          {health === "on_track" && (
            <span
              data-testid="badge-on-track"
              className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded-md bg-emerald-500/10 text-positive border border-emerald-500/30"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              On Track
            </span>
          )}
        </div>
      </div>

      {/* Numbers row: Spent vs Total Available */}
      <div className="flex items-baseline justify-between text-sm mb-2">
        <div>
          <span className="text-xl font-bold font-tabular text-main">
            {period?.spent || "0.00"}
          </span>
          <span className="text-xs text-muted ml-1.5 font-sans">
            spent of{" "}
            <span className="font-tabular text-main font-semibold">
              {period?.total_available || budget.base_amount} {currency}
            </span>
          </span>
        </div>

        <div className="text-right">
          {isOverBudget ? (
            <span className="text-xs font-semibold text-negative font-tabular">
              {period?.remaining} {currency} over
            </span>
          ) : (
            <span className="text-xs font-medium text-positive font-tabular">
              {period?.remaining} {currency} left
            </span>
          )}
        </div>
      </div>

      {/* Progress Bar */}
      <div className="h-2.5 w-full bg-[var(--surface-raised)] rounded-full overflow-hidden border border-[var(--border)] mb-3">
        <div
          data-testid="budget-progress-bar"
          className={`h-full ${progressColor} transition-all duration-500 rounded-full`}
          style={{ width: `${Math.min(spentPercent, 100)}%` }}
        />
      </div>

      {/* Bottom Footer: Dates and Actions */}
      <div className="flex items-center justify-between pt-2 border-t border-[var(--border)] text-xs text-muted">
        <div>
          {period ? (
            <span>
              {period.period_start} → {period.period_end}
            </span>
          ) : (
            <span>Starts: {budget.starts_on}</span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {budget.rollover_enabled && (
            <button
              type="button"
              onClick={() => closeMutation.mutate()}
              disabled={closeMutation.isPending || period?.status === "closed"}
              className="flex items-center gap-1 px-2.5 py-1 rounded bg-[var(--surface-raised)] border border-[var(--border)] text-muted hover:text-main hover:border-[var(--accent)] transition-all disabled:opacity-40 cursor-pointer"
              title="Close current period and roll positive balance forward"
            >
              <Lock className="w-3 h-3 text-gold" />
              {closeMutation.isPending ? "Closing..." : "Close Period"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
