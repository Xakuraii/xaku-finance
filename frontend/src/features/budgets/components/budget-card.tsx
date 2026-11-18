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
      className="rounded-xl border border-[#2b313a] bg-[#181a20] p-5 text-white shadow-md relative overflow-hidden transition-all hover:border-[#3b414d]"
    >
      {/* Top row: Name, Category, and Status pill */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div>
          <div className="flex items-center gap-2">
            <h4 className="font-semibold text-base text-slate-100">{budget.name}</h4>
            {hasRollover && (
              <span
                data-testid="rollover-pill"
                className="inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full bg-[#F0B90B]/10 text-[#F0B90B] border border-[#F0B90B]/30"
              >
                <Sparkles className="w-3 h-3" />
                +{period?.rollover_in} {currency} rollover
              </span>
            )}
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Category: <span className="text-slate-300 font-medium">{budget.category.name}</span>
            <span className="mx-1.5">•</span>
            <span className="capitalize">{budget.period_type}</span>
          </p>
        </div>

        {/* Health state badge */}
        <div>
          {health === "over_budget" && (
            <span
              data-testid="badge-over-budget"
              className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded-md bg-red-500/10 text-red-400 border border-red-500/30"
            >
              <AlertTriangle className="w-3.5 h-3.5" />
              Over Budget
            </span>
          )}
          {health === "alert" && (
            <span
              data-testid="badge-alert"
              className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded-md bg-orange-500/10 text-orange-400 border border-orange-500/30"
            >
              <AlertTriangle className="w-3.5 h-3.5" />
              Alert (100%)
            </span>
          )}
          {health === "warning" && (
            <span
              data-testid="badge-warning"
              className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded-md bg-amber-500/10 text-amber-400 border border-amber-500/30"
            >
              <AlertTriangle className="w-3.5 h-3.5" />
              Warning (80%)
            </span>
          )}
          {health === "on_track" && (
            <span
              data-testid="badge-on-track"
              className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
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
          <span className="text-xl font-bold font-mono text-slate-100">
            {period?.spent || "0.00"}
          </span>
          <span className="text-xs text-slate-400 ml-1.5 font-sans">
            spent of{" "}
            <span className="font-mono text-slate-300">
              {period?.total_available || budget.base_amount} {currency}
            </span>
          </span>
        </div>

        <div className="text-right">
          {isOverBudget ? (
            <span className="text-xs font-semibold text-red-400 font-mono">
              {period?.remaining} {currency} over
            </span>
          ) : (
            <span className="text-xs font-medium text-emerald-400 font-mono">
              {period?.remaining} {currency} left
            </span>
          )}
        </div>
      </div>

      {/* Progress Bar */}
      <div className="h-2.5 w-full bg-[#0b0e11] rounded-full overflow-hidden border border-[#2b313a]/60 mb-3">
        <div
          data-testid="budget-progress-bar"
          className={`h-full ${progressColor} transition-all duration-500 rounded-full`}
          style={{ width: `${Math.min(spentPercent, 100)}%` }}
        />
      </div>

      {/* Bottom Footer: Dates and Actions */}
      <div className="flex items-center justify-between pt-2 border-t border-[#2b313a]/60 text-xs text-slate-400">
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
              className="flex items-center gap-1 px-2.5 py-1 rounded bg-[#0b0e11] border border-[#2b313a] text-slate-300 hover:text-white hover:border-[#F0B90B] transition-all disabled:opacity-40"
              title="Close current period and roll positive balance forward"
            >
              <Lock className="w-3 h-3 text-[#F0B90B]" />
              {closeMutation.isPending ? "Closing..." : "Close Period"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
