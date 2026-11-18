import React, { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import * as Dialog from "@radix-ui/react-dialog";
import { PlusCircle, X, AlertCircle, Info } from "lucide-react";
import { Account } from "@/features/accounts/types";
import { SavingsGoal, recordSavingsContribution } from "../api/savings-api";

interface ContributeDialogProps {
  goal: SavingsGoal | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  accounts: Account[];
}

export const ContributeDialog: React.FC<ContributeDialogProps> = ({
  goal,
  open,
  onOpenChange,
  accounts,
}) => {
  const queryClient = useQueryClient();
  const eligibleAccounts = accounts.filter(
    (a) => !a.is_archived && a.currency === goal?.currency
  );

  const [kind, setKind] = useState<"earmark" | "withdrawal" | "adjustment">("earmark");
  const [amount, setAmount] = useState("");
  const [accountId, setAccountId] = useState(
    goal?.linked_account_id || eligibleAccounts[0]?.id || ""
  );
  const [note, setNote] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: (data: { goalId: string; payload: any }) =>
      recordSavingsContribution(data.goalId, data.payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["savings-goals"] });
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
      onOpenChange(false);
      resetForm();
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.message || err?.message || "Failed to record contribution.";
      setErrorMessage(msg);
    },
  });

  const resetForm = () => {
    setAmount("");
    setNote("");
    setErrorMessage(null);
  };

  if (!goal) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    const amt = parseFloat(amount);
    if (isNaN(amt) || amt <= 0) {
      setErrorMessage("Please enter a positive amount.");
      return;
    }

    mutation.mutate({
      goalId: goal.id,
      payload: {
        kind,
        amount,
        account_id: accountId,
        note: note.trim() || null,
      },
    });
  };

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/60 backdrop-blur-xs z-50 animate-fade-in" />
        <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-md bg-[var(--surface)] border border-[var(--border)] rounded-2xl p-6 shadow-2xl z-50 animate-scale-in">
          <div className="flex items-center justify-between pb-4 border-b border-[var(--border)]">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-gold/10 text-gold border border-gold/20">
                <PlusCircle className="w-5 h-5" />
              </div>
              <div>
                <Dialog.Title className="text-lg font-bold text-main">
                  Contribute to Goal
                </Dialog.Title>
                <p className="text-xs text-muted">{goal.name}</p>
              </div>
            </div>
            <Dialog.Close className="p-1 rounded-lg hover:bg-[var(--surface-hover)] text-muted hover:text-main">
              <X className="w-5 h-5" />
            </Dialog.Close>
          </div>

          {errorMessage && (
            <div className="mt-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Earmark explanation notice */}
          {kind === "earmark" && (
            <div className="mt-4 p-3 rounded-lg bg-gold/5 border border-gold/20 text-gold text-xs flex items-start gap-2">
              <Info className="w-4 h-4 shrink-0 mt-0.5" />
              <span>
                An earmark allocates existing funds to this goal without moving money. Net worth and account balance remain unchanged.
              </span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="mt-4 space-y-4">
            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => setKind("earmark")}
                className={`py-2 text-xs font-medium rounded-lg border transition-all cursor-pointer ${
                  kind === "earmark"
                    ? "bg-gold text-black border-gold"
                    : "bg-[var(--surface-muted)] text-muted border-[var(--border)]"
                }`}
              >
                Earmark
              </button>
              <button
                type="button"
                onClick={() => setKind("withdrawal")}
                className={`py-2 text-xs font-medium rounded-lg border transition-all cursor-pointer ${
                  kind === "withdrawal"
                    ? "bg-gold text-black border-gold"
                    : "bg-[var(--surface-muted)] text-muted border-[var(--border)]"
                }`}
              >
                Withdrawal
              </button>
              <button
                type="button"
                onClick={() => setKind("adjustment")}
                className={`py-2 text-xs font-medium rounded-lg border transition-all cursor-pointer ${
                  kind === "adjustment"
                    ? "bg-gold text-black border-gold"
                    : "bg-[var(--surface-muted)] text-muted border-[var(--border)]"
                }`}
              >
                Adjustment
              </button>
            </div>

            <div>
              <label className="block text-xs font-medium text-muted mb-1">Source Account</label>
              <select
                value={accountId}
                onChange={(e) => setAccountId(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-[var(--surface-muted)] border border-[var(--border)] text-sm text-main focus:border-gold outline-hidden"
              >
                {eligibleAccounts.map((acc) => (
                  <option key={acc.id} value={acc.id}>
                    {acc.name} ({acc.currency})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <div className="flex justify-between items-center mb-1">
                <label className="block text-xs font-medium text-muted">Amount</label>
                {kind === "earmark" && goal.linked_account_id === accountId && (
                  <span className="text-[11px] text-muted">
                    Max capacity: ${(goal.unallocated_capacity / 100).toFixed(2)}
                  </span>
                )}
              </div>
              <div className="relative">
                <input
                  type="number"
                  step="0.01"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  placeholder="100.00"
                  className="w-full px-3 py-2 rounded-lg bg-[var(--surface-muted)] border border-[var(--border)] text-sm text-main focus:border-gold outline-hidden pr-14"
                  required
                />
                <span className="absolute right-3 top-2 text-xs text-muted">
                  {goal.currency}
                </span>
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-muted mb-1">Note (Optional)</label>
              <input
                type="text"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Reason or description"
                className="w-full px-3 py-2 rounded-lg bg-[var(--surface-muted)] border border-[var(--border)] text-sm text-main focus:border-gold outline-hidden"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => onOpenChange(false)}
                className="px-4 py-2 rounded-lg text-sm text-muted hover:bg-[var(--surface-hover)]"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={mutation.isPending}
                className="px-4 py-2 rounded-lg bg-gold text-black font-semibold text-sm hover:brightness-110 disabled:opacity-50 cursor-pointer"
              >
                {mutation.isPending ? "Recording..." : "Record"}
              </button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
};
