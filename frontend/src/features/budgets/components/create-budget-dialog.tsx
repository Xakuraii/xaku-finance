import React, { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import * as Dialog from "@radix-ui/react-dialog";
import { X, Sparkles, PlusCircle } from "lucide-react";
import { createBudget } from "../api/budgets-api";
import { CreateBudgetPayload } from "../types";

interface CreateBudgetDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  categories: Array<{ id: string; name: string; kind: string }>;
  defaultCurrency?: string;
}

export const CreateBudgetDialog: React.FC<CreateBudgetDialogProps> = ({
  open,
  onOpenChange,
  categories,
  defaultCurrency = "USD",
}) => {
  const queryClient = useQueryClient();
  const expenseCategories = categories.filter((c) => c.kind === "expense");

  const [name, setName] = useState("");
  const [categoryId, setCategoryId] = useState(expenseCategories[0]?.id || "");
  const [amount, setAmount] = useState("");
  const [periodType, setPeriodType] = useState<"monthly" | "weekly">("monthly");
  const [rolloverEnabled, setRolloverEnabled] = useState(false);
  const [rolloverCap, setRolloverCap] = useState("");
  const [isFlexible, setIsFlexible] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: (payload: CreateBudgetPayload) => createBudget(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["budgets"] });
      onOpenChange(false);
      resetForm();
    },
    onError: (err: any) => {
      setErrorMessage(err.message || "Failed to create budget.");
    },
  });

  const resetForm = () => {
    setName("");
    setAmount("");
    setRolloverEnabled(false);
    setRolloverCap("");
    setErrorMessage(null);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!name.trim()) {
      setErrorMessage("Please enter a budget name.");
      return;
    }
    if (!categoryId) {
      setErrorMessage("Please select an expense category.");
      return;
    }
    if (!amount || parseFloat(amount) <= 0) {
      setErrorMessage("Please enter a positive budget amount.");
      return;
    }

    mutation.mutate({
      name: name.trim(),
      category_id: categoryId,
      amount,
      currency: defaultCurrency,
      period_type: periodType,
      rollover_enabled: rolloverEnabled,
      rollover_cap: rolloverCap ? rolloverCap : null,
      is_flexible: isFlexible,
    });
  };

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 animate-fade-in" />
        <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-md rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6 shadow-2xl z-50 text-main animate-scale-in">
          <div className="flex items-center justify-between pb-3 border-b border-[var(--border)]">
            <div className="flex items-center gap-2">
              <PlusCircle className="w-5 h-5 text-gold" />
              <Dialog.Title className="text-lg font-bold text-main">
                Create New Budget
              </Dialog.Title>
            </div>
            <Dialog.Close asChild>
              <button
                type="button"
                className="text-muted hover:text-main p-1 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </Dialog.Close>
          </div>

          <form onSubmit={handleSubmit} className="mt-4 space-y-4">
            {errorMessage && (
              <div className="p-3 text-xs bg-[var(--negative-bg)] border border-[var(--negative-border)] text-[var(--negative)] rounded-lg">
                {errorMessage}
              </div>
            )}

            <div>
              <label className="block text-xs font-medium text-main mb-1">
                Budget Name
              </label>
              <input
                type="text"
                placeholder="e.g. Monthly Groceries"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full bg-[var(--surface-raised)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-main focus:outline-none focus:border-[var(--accent)]"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-main mb-1">
                Expense Category
              </label>
              <select
                value={categoryId}
                onChange={(e) => setCategoryId(e.target.value)}
                className="w-full bg-[var(--surface-raised)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-main focus:outline-none focus:border-[var(--accent)]"
                required
              >
                {expenseCategories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-main mb-1">
                  Budget Amount ({defaultCurrency})
                </label>
                <input
                  type="text"
                  placeholder="250.00"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  className="w-full bg-[var(--surface-raised)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-main font-mono focus:outline-none focus:border-[var(--accent)]"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-main mb-1">
                  Period Type
                </label>
                <select
                  value={periodType}
                  onChange={(e) => setPeriodType(e.target.value as any)}
                  className="w-full bg-[var(--surface-raised)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-main focus:outline-none focus:border-[var(--accent)]"
                >
                  <option value="monthly">Monthly</option>
                  <option value="weekly">Weekly</option>
                </select>
              </div>
            </div>

            {/* Rollover Settings */}
            <div className="pt-2 border-t border-[var(--border)]/60 space-y-3">
              <label className="flex items-center gap-2 text-xs text-main cursor-pointer">
                <input
                  type="checkbox"
                  checked={rolloverEnabled}
                  onChange={(e) => setRolloverEnabled(e.target.checked)}
                  className="rounded border-[var(--border)] text-gold focus:ring-[#F0B90B] accent-[#F0B90B]"
                />
                <span className="flex items-center gap-1">
                  <Sparkles className="w-3.5 h-3.5 text-gold" />
                  Enable Positive Rollover
                </span>
              </label>

              <label className="flex items-center gap-2 text-xs text-main cursor-pointer">
                <input
                  type="checkbox"
                  checked={isFlexible}
                  onChange={(e) => setIsFlexible(e.target.checked)}
                  className="rounded border-[var(--border)] text-gold focus:ring-[#F0B90B] accent-[#F0B90B]"
                />
                <span>Flexible Budget (funds Safe-to-Spend & Daily Allowance)</span>
              </label>

              {rolloverEnabled && (
                <div>
                  <label className="block text-xs text-muted mb-1">
                    Rollover Cap (Optional max limit)
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. 50.00"
                    value={rolloverCap}
                    onChange={(e) => setRolloverCap(e.target.value)}
                    className="w-full bg-[var(--surface-raised)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-main font-mono focus:outline-none focus:border-[var(--accent)]"
                  />
                </div>
              )}
            </div>

            <div className="pt-4 flex justify-end gap-3 border-t border-[var(--border)]">
              <Dialog.Close asChild>
                <button
                  type="button"
                  className="px-4 py-2 text-xs font-medium text-muted hover:text-main rounded-lg transition-colors"
                >
                  Cancel
                </button>
              </Dialog.Close>
              <button
                type="submit"
                disabled={mutation.isPending}
                className="px-4 py-2 text-xs font-semibold rounded-lg bg-[#F0B90B] text-black hover:bg-[#FCD535] transition-all disabled:opacity-50"
              >
                {mutation.isPending ? "Creating..." : "Create Budget"}
              </button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
};
