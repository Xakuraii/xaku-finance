import React from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Sparkles,
  Archive,
  RotateCcw,
  Calendar,
  Wallet,
  PlusCircle,
  TrendingUp,
} from "lucide-react";
import { SavingsGoal, archiveSavingsGoal, restoreSavingsGoal } from "../api/savings-api";

interface SavingsGoalCardProps {
  goal: SavingsGoal;
  onContribute: (goal: SavingsGoal) => void;
  onViewProjection?: (goal: SavingsGoal) => void;
}

export const SavingsGoalCard: React.FC<SavingsGoalCardProps> = ({
  goal,
  onContribute,
  onViewProjection,
}) => {
  const queryClient = useQueryClient();

  const archiveMutation = useMutation({
    mutationFn: () => archiveSavingsGoal(goal.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["savings-goals"] });
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
    },
  });

  const restoreMutation = useMutation({
    mutationFn: () => restoreSavingsGoal(goal.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["savings-goals"] });
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
    },
  });

  const isAchieved = goal.status === "achieved";
  const isArchived = goal.is_archived;

  return (
    <div
      data-testid={`savings-goal-card-${goal.id}`}
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
            <h4 className="font-semibold text-base text-main">{goal.name}</h4>
            {isAchieved && (
              <span
                data-testid="achieved-pill"
                className="inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
              >
                <Sparkles className="w-3 h-3" />
                Achieved
              </span>
            )}
            {goal.is_overfunded && (
              <span
                data-testid="overfunded-pill"
                className="inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full bg-[#F0B90B]/10 text-[#F0B90B] border border-[#F0B90B]/30"
              >
                +{(goal.overfunded_amount_minor / 100).toFixed(2)} Over
              </span>
            )}
            {isArchived && (
              <span className="text-[11px] font-medium px-2 py-0.5 rounded-full bg-zinc-700 text-zinc-300">
                Archived
              </span>
            )}
          </div>
          <div className="flex items-center gap-3 text-xs text-muted mt-1">
            <span className="capitalize">{goal.strategy.replace("_", " ")}</span>
            {goal.linked_account_name && (
              <span className="flex items-center gap-1">
                <Wallet className="w-3 h-3 text-gold" />
                {goal.linked_account_name}
              </span>
            )}
            {goal.target_date && (
              <span className="flex items-center gap-1">
                <Calendar className="w-3 h-3" />
                Due {goal.target_date}
              </span>
            )}
          </div>
        </div>

        {/* Action icons */}
        <div className="flex items-center gap-1">
          {onViewProjection && (
            <button
              onClick={() => onViewProjection(goal)}
              title="View projection"
              className="p-1.5 rounded-md hover:bg-[var(--surface-hover)] text-muted hover:text-gold transition-colors"
            >
              <TrendingUp className="w-4 h-4" />
            </button>
          )}
          {isArchived ? (
            <button
              onClick={() => restoreMutation.mutate()}
              title="Restore goal"
              className="p-1.5 rounded-md hover:bg-[var(--surface-hover)] text-muted hover:text-main transition-colors"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          ) : (
            <button
              onClick={() => archiveMutation.mutate()}
              title="Archive goal (releases earmarks)"
              className="p-1.5 rounded-md hover:bg-[var(--surface-hover)] text-muted hover:text-red-400 transition-colors"
            >
              <Archive className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Progress & Amounts */}
      <div className="space-y-2 mb-4">
        <div className="flex items-baseline justify-between">
          <span className="text-xl font-bold text-main font-mono">
            {goal.current_amount}{" "}
            <span className="text-xs font-normal text-muted">{goal.currency}</span>
          </span>
          <span className="text-xs text-muted font-mono">
            Target: {goal.target_amount} {goal.currency}
          </span>
        </div>

        {/* Progress bar */}
        <div className="w-full h-2.5 rounded-full bg-[var(--surface-muted)] overflow-hidden">
          <div
            className={`h-full transition-all duration-500 ${
              isAchieved
                ? "bg-gradient-to-r from-emerald-500 to-emerald-400"
                : "bg-gradient-to-r from-[#F0B90B] to-[#FCD535]"
            }`}
            style={{ width: `${Math.min(100, goal.progress_percent)}%` }}
          />
        </div>

        <div className="flex justify-between text-xs text-muted">
          <span>{goal.progress_percent.toFixed(1)}% funded</span>
          {goal.linked_account_id && (
            <span className="text-[11px] text-muted">
              Capacity: ${(goal.unallocated_capacity / 100).toFixed(2)} available
            </span>
          )}
        </div>
      </div>

      {/* Card Action footer */}
      {!isArchived && (
        <div className="pt-3 border-t border-[var(--border)] flex justify-end">
          <button
            onClick={() => onContribute(goal)}
            data-testid={`contribute-btn-${goal.id}`}
            className="flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg bg-gold/10 text-gold border border-gold/30 hover:bg-gold/20 transition-all cursor-pointer"
          >
            <PlusCircle className="w-3.5 h-3.5" />
            Contribute / Earmark
          </button>
        </div>
      )}
    </div>
  );
};
