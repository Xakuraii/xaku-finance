import React, { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import * as Dialog from "@radix-ui/react-dialog";
import { Target, X, AlertCircle } from "lucide-react";
import { Account } from "@/features/accounts/types";
import { createSavingsGoal } from "../api/savings-api";

interface CreateGoalDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  accounts: Account[];
}

export const CreateGoalDialog: React.FC<CreateGoalDialogProps> = ({
  open,
  onOpenChange,
  accounts,
}) => {
  const queryClient = useQueryClient();
  const activeAccounts = accounts.filter((a) => !a.is_archived);

  const [name, setName] = useState("");
  const [targetAmount, setTargetAmount] = useState("");
  const [currency, setCurrency] = useState("USD");
  const [targetDate, setTargetDate] = useState("");
  const [strategy, setStrategy] = useState<"linked_account" | "earmark">("linked_account");
  const [linkedAccountId, setLinkedAccountId] = useState(activeAccounts[0]?.id || "");
  const [notes, setNotes] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: createSavingsGoal,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["savings-goals"] });
      onOpenChange(false);
      resetForm();
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.message || err?.message || "Failed to create savings goal.";
      setErrorMessage(msg);
    },
  });

  const resetForm = () => {
    setName("");
    setTargetAmount("");
    setTargetDate("");
    setNotes("");
    setErrorMessage(null);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!name.trim()) {
      setErrorMessage("Goal name is required.");
      return;
    }
    const amt = parseFloat(targetAmount);
    if (isNaN(amt) || amt <= 0) {
      setErrorMessage("Target amount must be a positive number.");
      return;
    }

    mutation.mutate({
      name: name.trim(),
      target_amount: targetAmount,
      currency,
      target_date: targetDate || null,
      strategy,
      linked_account_id: strategy === "linked_account" ? linkedAccountId : null,
      notes: notes.trim() || null,
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
                <Target className="w-5 h-5" />
              </div>
              <Dialog.Title className="text-lg font-bold text-main">
                Create Savings Goal
              </Dialog.Title>
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

          <form onSubmit={handleSubmit} className="mt-4 space-y-4">
            <div>
              <label className="block text-xs font-medium text-muted mb-1">Goal Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Emergency Fund, New Laptop"
                className="w-full px-3 py-2 rounded-lg bg-[var(--surface-muted)] border border-[var(--border)] text-sm text-main focus:border-gold outline-hidden"
                required
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-muted mb-1">Target Amount</label>
                <input
                  type="number"
                  step="0.01"
                  value={targetAmount}
                  onChange={(e) => setTargetAmount(e.target.value)}
                  placeholder="1000.00"
                  className="w-full px-3 py-2 rounded-lg bg-[var(--surface-muted)] border border-[var(--border)] text-sm text-main focus:border-gold outline-hidden"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-muted mb-1">Currency</label>
                <select
                  value={currency}
                  onChange={(e) => setCurrency(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-[var(--surface-muted)] border border-[var(--border)] text-sm text-main focus:border-gold outline-hidden"
                >
                  <option value="USD">USD ($)</option>
                  <option value="KHR">KHR (៛)</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-muted mb-1">Strategy</label>
                <select
                  value={strategy}
                  onChange={(e) => setStrategy(e.target.value as any)}
                  className="w-full px-3 py-2 rounded-lg bg-[var(--surface-muted)] border border-[var(--border)] text-sm text-main focus:border-gold outline-hidden"
                >
                  <option value="linked_account">Linked Account</option>
                  <option value="earmark">Virtual Earmark</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-muted mb-1">Target Date</label>
                <input
                  type="date"
                  value={targetDate}
                  onChange={(e) => setTargetDate(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-[var(--surface-muted)] border border-[var(--border)] text-sm text-main focus:border-gold outline-hidden"
                />
              </div>
            </div>

            {strategy === "linked_account" && (
              <div>
                <label className="block text-xs font-medium text-muted mb-1">Backing Account</label>
                <select
                  value={linkedAccountId}
                  onChange={(e) => setLinkedAccountId(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-[var(--surface-muted)] border border-[var(--border)] text-sm text-main focus:border-gold outline-hidden"
                >
                  {activeAccounts.map((acc) => (
                    <option key={acc.id} value={acc.id}>
                      {acc.name} ({acc.currency})
                    </option>
                  ))}
                </select>
              </div>
            )}

            <div>
              <label className="block text-xs font-medium text-muted mb-1">Notes (Optional)</label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="What is this goal for?"
                rows={2}
                className="w-full px-3 py-2 rounded-lg bg-[var(--surface-muted)] border border-[var(--border)] text-sm text-main focus:border-gold outline-hidden resize-none"
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
                {mutation.isPending ? "Creating..." : "Create Goal"}
              </button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
};
