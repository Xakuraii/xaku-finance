import React, { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { X, AlertCircle } from "lucide-react";
import { createAccount } from "../api";
import { AccountType } from "../types";
import { queryKeys } from "@/lib/query-keys";
import { ApiError } from "@/lib/api/client";

interface CreateAccountDialogProps {
  isOpen: boolean;
  onClose: () => void;
}

export const CreateAccountDialog: React.FC<CreateAccountDialogProps> = ({
  isOpen,
  onClose,
}) => {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [accountType, setAccountType] = useState<AccountType>("checking");
  const [currency, setCurrency] = useState("USD");
  const [openingBalance, setOpeningBalance] = useState("");
  const [description, setDescription] = useState("");
  const [isSpendable, setIsSpendable] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: createAccount,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.accounts.all });
      onClose();
      // Reset form
      setName("");
      setOpeningBalance("");
      setDescription("");
      setErrorMessage(null);
    },
    onError: (err: unknown) => {
      if (err instanceof ApiError) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage("Failed to create account. Please check your inputs.");
      }
    },
  });

  if (!isOpen) return null;

  const handleTypeChange = (type: AccountType) => {
    setAccountType(type);
    if (type === "savings" || type === "investment" || type === "credit_card") {
      setIsSpendable(false);
    } else {
      setIsSpendable(true);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    mutation.mutate({
      name: name.trim(),
      account_type: accountType,
      currency,
      opening_balance: openingBalance.trim() ? openingBalance.trim() : undefined,
      is_spendable: accountType === "savings" ? false : isSpendable,
      description: description.trim() || undefined,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-xs p-4">
      <div className="w-full max-w-md rounded-lg bg-[var(--surface-raised)] border border-[var(--border-strong)] p-6 shadow-2xl">
        <div className="flex items-center justify-between border-b border-[var(--border)] pb-4 mb-4">
          <h2 className="text-lg font-medium text-main">New Financial Account</h2>
          <button
            onClick={onClose}
            className="text-muted hover:text-main cursor-pointer"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {errorMessage && (
          <div className="mb-4 flex items-center gap-2 rounded bg-[var(--negative-bg)] border border-[var(--negative-border)] p-3 text-sm text-[var(--negative)]">
            <AlertCircle className="w-4 h-4 shrink-0 text-negative" />
            <span>{errorMessage}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-muted mb-1">Account Name</label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Main Checking, ABA Mobile, Cash"
              className="w-full rounded bg-[var(--surface)] border border-[var(--border)] px-3 py-2 text-sm text-main focus:border-[var(--accent)] focus:outline-none"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-muted mb-1">Account Type</label>
              <select
                value={accountType}
                onChange={(e) => handleTypeChange(e.target.value as AccountType)}
                className="w-full rounded bg-[var(--surface)] border border-[var(--border)] px-3 py-2 text-sm text-main focus:border-[var(--accent)] focus:outline-none"
              >
                <option value="checking">Checking</option>
                <option value="savings">Savings</option>
                <option value="cash">Cash Wallet</option>
                <option value="ewallet">E-Wallet</option>
                <option value="credit_card">Credit Card</option>
                <option value="investment">Investment</option>
                <option value="other">Other</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-muted mb-1">Currency</label>
              <select
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
                className="w-full rounded bg-[var(--surface)] border border-[var(--border)] px-3 py-2 text-sm text-main focus:border-[var(--accent)] focus:outline-none"
              >
                <option value="USD">USD ($)</option>
                <option value="KHR">KHR (៛)</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-muted mb-1">
              Opening Balance <span className="text-faint font-normal">(Optional)</span>
            </label>
            <div className="relative">
              <input
                type="text"
                value={openingBalance}
                onChange={(e) => setOpeningBalance(e.target.value)}
                placeholder="0.00"
                className="w-full rounded bg-[var(--surface)] border border-[var(--border)] px-3 py-2 text-sm text-main font-tabular focus:border-[var(--accent)] focus:outline-none"
              />
              <span className="absolute right-3 top-2 text-xs text-muted font-tabular">
                {currency}
              </span>
            </div>
            <p className="mt-1 text-[11px] text-faint">
              Recorded as equity balance, never counted as ordinary income.
            </p>
          </div>

          <div className="flex items-center gap-2 pt-1">
            <input
              type="checkbox"
              id="isSpendable"
              checked={accountType === "savings" ? false : isSpendable}
              disabled={accountType === "savings"}
              onChange={(e) => setIsSpendable(e.target.checked)}
              className="rounded border-[var(--border)] bg-[var(--surface)] accent-[var(--accent)]"
            />
            <label
              htmlFor="isSpendable"
              className={`text-xs ${accountType === "savings" ? "text-faint" : "text-muted"}`}
            >
              Designate as Spendable (included in Safe-to-Spend calculations)
            </label>
          </div>

          <div>
            <label className="block text-xs font-medium text-muted mb-1">
              Description <span className="text-faint font-normal">(Optional)</span>
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              placeholder="Notes regarding this account..."
              className="w-full rounded bg-[var(--surface)] border border-[var(--border)] px-3 py-2 text-sm text-main focus:border-[var(--accent)] focus:outline-none"
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-3 border-t border-[var(--border)]">
            <button
              type="button"
              onClick={onClose}
              className="rounded px-4 py-2 text-xs font-medium text-muted hover:text-main cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={mutation.isPending}
              className="rounded bg-gold px-4 py-2 text-xs font-medium cursor-pointer disabled:opacity-50"
            >
              {mutation.isPending ? "Creating..." : "Create Account"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
