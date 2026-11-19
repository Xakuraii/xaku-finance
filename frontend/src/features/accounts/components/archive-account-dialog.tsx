import React, { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { X, AlertTriangle } from "lucide-react";
import { archiveAccount } from "../api";
import { Account } from "../types";
import { queryKeys } from "@/lib/query-keys";
import { ApiError } from "@/lib/api/client";
import { MoneyDisplay } from "@/components/money";

interface ArchiveAccountDialogProps {
  account: Account | null;
  isOpen: boolean;
  onClose: () => void;
}

export const ArchiveAccountDialog: React.FC<ArchiveAccountDialogProps> = ({
  account,
  isOpen,
  onClose,
}) => {
  const queryClient = useQueryClient();
  const [reason, setReason] = useState("");
  const [acknowledge, setAcknowledge] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const hasNonZeroBalance = account ? account.balance_minor !== 0 : false;

  const mutation = useMutation({
    mutationFn: (data: { id: string; reason: string; acknowledge_balance: boolean }) =>
      archiveAccount(data.id, {
        reason: data.reason,
        acknowledge_balance: data.acknowledge_balance,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.accounts.all });
      onClose();
      setReason("");
      setAcknowledge(false);
      setErrorMessage(null);
    },
    onError: (err: unknown) => {
      if (err instanceof ApiError) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage("Failed to archive account.");
      }
    },
  });

  if (!isOpen || !account) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (hasNonZeroBalance && !acknowledge) {
      setErrorMessage("You must acknowledge the non-zero balance before archiving.");
      return;
    }

    mutation.mutate({
      id: account.id,
      reason: reason.trim(),
      acknowledge_balance: acknowledge,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-xs p-4">
      <div className="w-full max-w-md rounded-lg bg-[var(--surface-raised)] border border-[var(--border-strong)] p-6 shadow-2xl">
        <div className="flex items-center justify-between border-b border-[var(--border)] pb-4 mb-4">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-warning" />
            <h2 className="text-lg font-medium text-main">Archive Account</h2>
          </div>
          <button
            onClick={onClose}
            className="text-muted hover:text-main cursor-pointer"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {errorMessage && (
          <div className="mb-4 rounded bg-[var(--negative-bg)] border border-[var(--negative-border)] p-3 text-sm text-[var(--negative)]">
            {errorMessage}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <p className="text-sm text-muted">
            Are you sure you want to archive <span className="font-semibold text-main">{account.name}</span>?
            Archiving will hide this account from spending lists, but all transaction history and ledger entries will be preserved.
          </p>

          {hasNonZeroBalance && (
            <div className="rounded border border-[var(--warning-border)] bg-[var(--warning-bg)] p-3 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="text-warning font-medium">Current Balance:</span>
                <MoneyDisplay
                  amountMinor={account.balance_minor}
                  currency={account.currency}
                  className="text-sm font-semibold"
                />
              </div>
              <div className="flex items-start gap-2 pt-1">
                <input
                  type="checkbox"
                  id="acknowledgeNonZero"
                  checked={acknowledge}
                  onChange={(e) => setAcknowledge(e.target.checked)}
                  className="mt-0.5 rounded border-[var(--border)] bg-[var(--surface)] accent-[var(--accent)]"
                />
                <label htmlFor="acknowledgeNonZero" className="text-xs text-muted leading-tight">
                  I acknowledge that this account has an active non-zero balance and should be archived.
                </label>
              </div>
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-muted mb-1">
              Reason for Archiving <span className="text-negative">*</span>
            </label>
            <input
              type="text"
              required
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g. Account closed at branch, switched providers"
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
              className="rounded bg-negative/90 hover:bg-negative text-white px-4 py-2 text-xs font-medium cursor-pointer disabled:opacity-50"
            >
              {mutation.isPending ? "Archiving..." : "Archive Account"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
