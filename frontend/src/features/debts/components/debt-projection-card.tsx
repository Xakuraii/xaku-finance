import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { TrendingDown, Clock, DollarSign, X, Calendar } from "lucide-react";
import * as Dialog from "@radix-ui/react-dialog";
import { Liability, fetchDebtProjection } from "../api/debts-api";

interface DebtProjectionModalProps {
  liability: Liability | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export const DebtProjectionModal: React.FC<DebtProjectionModalProps> = ({
  liability,
  open,
  onOpenChange,
}) => {
  const [customPayment, setCustomPayment] = useState("");

  const { data: projection, isLoading } = useQuery({
    queryKey: ["debt-projection", liability?.id, customPayment],
    queryFn: () => fetchDebtProjection(liability!.id, customPayment || undefined),
    enabled: Boolean(open && liability?.id),
  });

  if (!liability) return null;

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/60 backdrop-blur-xs z-50 animate-fade-in" />
        <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-md bg-[var(--surface)] border border-[var(--border)] rounded-2xl p-6 shadow-2xl z-50 animate-scale-in">
          <div className="flex items-center justify-between pb-4 border-b border-[var(--border)]">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-gold/10 text-gold border border-gold/20">
                <TrendingDown className="w-5 h-5" />
              </div>
              <div>
                <Dialog.Title className="text-lg font-bold text-main">
                  Payoff Projection
                </Dialog.Title>
                <p className="text-xs text-muted">{liability.name}</p>
              </div>
            </div>
            <Dialog.Close className="p-1 rounded-lg hover:bg-[var(--surface-hover)] text-muted hover:text-main">
              <X className="w-5 h-5" />
            </Dialog.Close>
          </div>

          <div className="mt-4 space-y-4">
            <div>
              <label className="block text-xs font-medium text-muted mb-1">
                Custom Monthly Payment ($)
              </label>
              <input
                type="number"
                step="1"
                value={customPayment}
                onChange={(e) => setCustomPayment(e.target.value)}
                placeholder="e.g. 250"
                className="w-full px-3 py-2 rounded-lg bg-[var(--surface-muted)] border border-[var(--border)] text-sm text-main focus:border-gold outline-hidden"
              />
            </div>

            {isLoading ? (
              <div className="py-8 text-center text-sm text-muted">Calculating projection...</div>
            ) : projection ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 rounded-xl bg-[var(--surface-muted)] border border-[var(--border)]">
                    <div className="flex items-center gap-1.5 text-xs text-muted mb-1">
                      <Clock className="w-3.5 h-3.5 text-gold" />
                      Months to Freedom
                    </div>
                    <div className="text-xl font-bold text-main">
                      {projection.estimated_months_to_payoff !== null
                        ? `${projection.estimated_months_to_payoff} mos`
                        : "Never (pay more)"}
                    </div>
                  </div>

                  <div className="p-3 rounded-xl bg-[var(--surface-muted)] border border-[var(--border)]">
                    <div className="flex items-center gap-1.5 text-xs text-muted mb-1">
                      <DollarSign className="w-3.5 h-3.5 text-gold" />
                      Total Interest
                    </div>
                    <div className="text-xl font-bold text-main font-mono">
                      ${(projection.total_interest_minor! / 100).toFixed(2)}
                    </div>
                  </div>
                </div>

                {projection.projected_payoff_date && (
                  <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
                    <div className="flex items-center gap-1.5 text-xs font-medium mb-1">
                      <Calendar className="w-4 h-4" />
                      Debt-Free Date
                    </div>
                    <div className="text-xl font-black font-mono">
                      {projection.projected_payoff_date}
                    </div>
                    <p className="text-[11px] text-muted mt-1">
                      At this pace, this debt will be completely liquidated.
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
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
};
