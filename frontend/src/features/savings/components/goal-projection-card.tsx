import React from "react";
import { useQuery } from "@tanstack/react-query";
import { TrendingUp, Clock, DollarSign, X } from "lucide-react";
import * as Dialog from "@radix-ui/react-dialog";
import { SavingsGoal, fetchSavingsProjection } from "../api/savings-api";

interface GoalProjectionModalProps {
  goal: SavingsGoal | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export const GoalProjectionModal: React.FC<GoalProjectionModalProps> = ({
  goal,
  open,
  onOpenChange,
}) => {
  const { data: projection, isLoading } = useQuery({
    queryKey: ["savings-projection", goal?.id],
    queryFn: () => fetchSavingsProjection(goal!.id),
    enabled: Boolean(open && goal?.id),
  });

  if (!goal) return null;

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/60 backdrop-blur-xs z-50 animate-fade-in" />
        <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-md bg-[var(--surface)] border border-[var(--border)] rounded-2xl p-6 shadow-2xl z-50 animate-scale-in">
          <div className="flex items-center justify-between pb-4 border-b border-[var(--border)]">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-gold/10 text-gold border border-gold/20">
                <TrendingUp className="w-5 h-5" />
              </div>
              <div>
                <Dialog.Title className="text-lg font-bold text-main">
                  Savings Projection
                </Dialog.Title>
                <p className="text-xs text-muted">{goal.name}</p>
              </div>
            </div>
            <Dialog.Close className="p-1 rounded-lg hover:bg-[var(--surface-hover)] text-muted hover:text-main">
              <X className="w-5 h-5" />
            </Dialog.Close>
          </div>

          {isLoading ? (
            <div className="py-8 text-center text-sm text-muted">Calculating projection...</div>
          ) : projection ? (
            <div className="mt-4 space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 rounded-xl bg-[var(--surface-muted)] border border-[var(--border)]">
                  <div className="flex items-center gap-1.5 text-xs text-muted mb-1">
                    <DollarSign className="w-3.5 h-3.5 text-gold" />
                    Remaining
                  </div>
                  <div className="text-base font-bold text-main font-mono">
                    ${(projection.remaining_amount_minor / 100).toFixed(2)}
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-[var(--surface-muted)] border border-[var(--border)]">
                  <div className="flex items-center gap-1.5 text-xs text-muted mb-1">
                    <Clock className="w-3.5 h-3.5 text-gold" />
                    Timeline
                  </div>
                  <div className="text-base font-bold text-main">
                    {projection.days_remaining !== null
                      ? `${projection.days_remaining} days`
                      : "No deadline"}
                  </div>
                </div>
              </div>

              {projection.required_monthly_contribution && (
                <div className="p-4 rounded-xl bg-gold/5 border border-gold/20">
                  <div className="text-xs text-gold font-medium mb-1">
                    Suggested Monthly Pace
                  </div>
                  <div className="text-2xl font-black text-main font-mono">
                    ${projection.required_monthly_contribution}{" "}
                    <span className="text-xs font-normal text-muted">/ month</span>
                  </div>
                  <p className="text-[11px] text-muted mt-1">
                    Saving this amount every month will hit your target by{" "}
                    {projection.target_date}.
                  </p>
                </div>
              )}

              <div className="flex justify-end pt-2">
                <button
                  type="button"
                  onClick={() => onOpenChange(false)}
                  className="px-4 py-2 rounded-lg bg-[var(--surface-muted)] text-sm text-main hover:bg-[var(--surface-hover)] cursor-pointer"
                >
                  Close
                </button>
              </div>
            </div>
          ) : null}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
};
