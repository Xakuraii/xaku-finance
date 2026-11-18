import React, { useState, useEffect } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import * as Dialog from "@radix-ui/react-dialog";
import { Shield, X, AlertCircle } from "lucide-react";
import { Account } from "@/features/accounts/types";
import { SavingsGoal } from "@/features/savings/api/savings-api";
import {
  EmergencyFundStatus,
  updateEmergencyFundConfig,
} from "../api/emergency-fund-api";

interface EmergencyConfigDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  status: EmergencyFundStatus;
  accounts: Account[];
  goals: SavingsGoal[];
}

export const EmergencyConfigDialog: React.FC<EmergencyConfigDialogProps> = ({
  open,
  onOpenChange,
  status,
  accounts,
  goals,
}) => {
  const queryClient = useQueryClient();
  const activeAccounts = accounts.filter((a) => !a.is_archived);
  const activeGoals = goals.filter((g) => !g.is_archived);

  const [targetMonths, setTargetMonths] = useState<number>(status.target_months);
  const [sourceType, setSourceType] = useState<"account" | "goal" | "none">(
    status.designated_account_id
      ? "account"
      : status.designated_goal_id
      ? "goal"
      : "none"
  );
  const [designatedAccountId, setDesignatedAccountId] = useState<string>(
    status.designated_account_id || activeAccounts[0]?.id || ""
  );
  const [designatedGoalId, setDesignatedGoalId] = useState<string>(
    status.designated_goal_id || activeGoals[0]?.id || ""
  );
  const [isOverride, setIsOverride] = useState<boolean>(status.is_override);
  const [overrideAmount, setOverrideAmount] = useState<string>(
    status.override_monthly_expense || ""
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setTargetMonths(status.target_months);
      setIsOverride(status.is_override);
      setOverrideAmount(status.override_monthly_expense || "");
      if (status.designated_account_id) {
        setSourceType("account");
        setDesignatedAccountId(status.designated_account_id);
      } else if (status.designated_goal_id) {
        setSourceType("goal");
        setDesignatedGoalId(status.designated_goal_id);
      } else {
        setSourceType("none");
      }
      setErrorMessage(null);
    }
  }, [open, status]);

  const mutation = useMutation({
    mutationFn: updateEmergencyFundConfig,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["emergency-fund-status"] });
      onOpenChange(false);
    },
    onError: (err: any) => {
      const msg =
        err?.response?.data?.detail ||
        err?.message ||
        "Failed to update emergency fund settings.";
      setErrorMessage(msg);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (targetMonths <= 0) {
      setErrorMessage("Target months must be at least 1.");
      return;
    }

    if (isOverride) {
      const amt = parseFloat(overrideAmount);
      if (isNaN(amt) || amt <= 0) {
        setErrorMessage("Please enter a valid positive monthly expense override.");
        return;
      }
    }

    mutation.mutate({
      target_months: targetMonths,
      designated_account_id: sourceType === "account" ? designatedAccountId : "",
      designated_goal_id: sourceType === "goal" ? designatedGoalId : "",
      clear_override: !isOverride,
      monthly_expense_override: isOverride ? overrideAmount : null,
    });
  };

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 animate-fade-in" />
        <Dialog.Content className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-lg bg-surface border border-border rounded-xl shadow-2xl p-6 z-50 focus:outline-none">
          <div className="flex items-center justify-between pb-4 border-b border-border">
            <div className="flex items-center gap-2">
              <Shield className="w-5 h-5 text-primary" />
              <Dialog.Title className="text-lg font-semibold text-text-primary">
                Configure Emergency Fund
              </Dialog.Title>
            </div>
            <Dialog.Close className="text-text-muted hover:text-text-primary p-1 rounded-md">
              <X className="w-5 h-5" />
            </Dialog.Close>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4 pt-4">
            {errorMessage && (
              <div className="p-3 bg-danger/10 border border-danger/30 rounded-lg flex items-center gap-2 text-sm text-danger">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{errorMessage}</span>
              </div>
            )}

            {/* Coverage Target in Months */}
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-1">
                Target Coverage (Months)
              </label>
              <div className="flex gap-2 mb-2">
                {[3, 6, 9, 12].map((m) => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => setTargetMonths(m)}
                    className={`flex-1 py-1.5 text-xs font-semibold rounded-lg border transition-colors ${
                      targetMonths === m
                        ? "bg-primary text-white border-primary"
                        : "bg-surface-hover text-text-secondary border-border hover:border-text-muted"
                    }`}
                  >
                    {m} Months
                  </button>
                ))}
              </div>
              <input
                type="number"
                min="1"
                max="60"
                value={targetMonths}
                onChange={(e) => setTargetMonths(parseInt(e.target.value) || 1)}
                className="w-full px-3 py-2 bg-surface-hover border border-border rounded-lg text-sm text-text-primary focus:outline-none focus:border-primary"
              />
            </div>

            {/* Essential Expenses Calculation Source */}
            <div className="p-3 bg-surface-hover/50 rounded-lg border border-border/60 space-y-2">
              <label className="block text-sm font-medium text-text-primary">
                Monthly Essential Expenses Source
              </label>
              <div className="flex items-center gap-4 text-sm">
                <label className="flex items-center gap-2 cursor-pointer text-text-secondary">
                  <input
                    type="radio"
                    name="expense-source"
                    checked={!isOverride}
                    onChange={() => setIsOverride(false)}
                    className="accent-primary"
                  />
                  <span>
                    Computed from 90-day history (${status.computed_monthly_expense}/mo)
                  </span>
                </label>
              </div>
              <div className="flex items-center gap-4 text-sm">
                <label className="flex items-center gap-2 cursor-pointer text-text-secondary">
                  <input
                    type="radio"
                    name="expense-source"
                    checked={isOverride}
                    onChange={() => setIsOverride(true)}
                    className="accent-primary"
                  />
                  <span>Manual Override</span>
                </label>
              </div>

              {isOverride && (
                <div className="pt-2">
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    placeholder="e.g. 500.00"
                    value={overrideAmount}
                    onChange={(e) => setOverrideAmount(e.target.value)}
                    className="w-full px-3 py-2 bg-surface border border-border rounded-lg text-sm text-text-primary focus:outline-none focus:border-primary"
                  />
                  <p className="text-xs text-text-muted mt-1">
                    Explicitly override computed essential spending with your own baseline.
                  </p>
                </div>
              )}
            </div>

            {/* Designated Source */}
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-1">
                Backing Savings Source
              </label>
              <div className="grid grid-cols-3 gap-2 mb-2">
                <button
                  type="button"
                  onClick={() => setSourceType("account")}
                  className={`py-1.5 text-xs font-semibold rounded-lg border transition-colors ${
                    sourceType === "account"
                      ? "bg-primary text-white border-primary"
                      : "bg-surface-hover text-text-secondary border-border"
                  }`}
                >
                  Bank Account
                </button>
                <button
                  type="button"
                  onClick={() => setSourceType("goal")}
                  className={`py-1.5 text-xs font-semibold rounded-lg border transition-colors ${
                    sourceType === "goal"
                      ? "bg-primary text-white border-primary"
                      : "bg-surface-hover text-text-secondary border-border"
                  }`}
                >
                  Savings Goal
                </button>
                <button
                  type="button"
                  onClick={() => setSourceType("none")}
                  className={`py-1.5 text-xs font-semibold rounded-lg border transition-colors ${
                    sourceType === "none"
                      ? "bg-primary text-white border-primary"
                      : "bg-surface-hover text-text-secondary border-border"
                  }`}
                >
                  None
                </button>
              </div>

              {sourceType === "account" && (
                <select
                  value={designatedAccountId}
                  onChange={(e) => setDesignatedAccountId(e.target.value)}
                  className="w-full px-3 py-2 bg-surface-hover border border-border rounded-lg text-sm text-text-primary focus:outline-none focus:border-primary"
                >
                  {activeAccounts.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.name} ({a.account_type})
                    </option>
                  ))}
                </select>
              )}

              {sourceType === "goal" && (
                <select
                  value={designatedGoalId}
                  onChange={(e) => setDesignatedGoalId(e.target.value)}
                  className="w-full px-3 py-2 bg-surface-hover border border-border rounded-lg text-sm text-text-primary focus:outline-none focus:border-primary"
                >
                  {activeGoals.map((g) => (
                    <option key={g.id} value={g.id}>
                      {g.name} (${g.current_amount} / ${g.target_amount})
                    </option>
                  ))}
                </select>
              )}
            </div>

            <div className="flex justify-end gap-2 pt-4 border-t border-border">
              <button
                type="button"
                onClick={() => onOpenChange(false)}
                className="px-4 py-2 text-sm text-text-secondary hover:text-text-primary transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={mutation.isPending}
                className="px-4 py-2 text-sm bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50"
              >
                {mutation.isPending ? "Saving..." : "Save Configuration"}
              </button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
};
