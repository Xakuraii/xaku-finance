import React, { useState, useEffect } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import * as Dialog from "@radix-ui/react-dialog";
import { ArrowRightLeft, X, AlertCircle, RefreshCw } from "lucide-react";
import { Account } from "@/features/accounts/types";
import { createTransfer } from "../api/transfers-api";
import { queryKeys } from "@/lib/query-keys";

interface TransferDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  accounts: Account[];
}

export const TransferDialog: React.FC<TransferDialogProps> = ({
  open,
  onOpenChange,
  accounts,
}) => {
  const queryClient = useQueryClient();
  const spendableAccounts = accounts.filter((a) => !a.is_archived);

  const [sourceAccountId, setSourceAccountId] = useState<string>(
    spendableAccounts[0]?.id || ""
  );
  const [destAccountId, setDestAccountId] = useState<string>(
    spendableAccounts[1]?.id || spendableAccounts[0]?.id || ""
  );
  const [amount, setAmount] = useState<string>("");
  const [rate, setRate] = useState<string>("");
  const [destinationAmount, setDestinationAmount] = useState<string>("");
  const [referenceRate, setReferenceRate] = useState<string>("");
  const [transferFee, setTransferFee] = useState<string>("0.00");
  const [occurredOn, setOccurredOn] = useState<string>(
    new Date().toISOString().split("T")[0]
  );
  const [notes, setNotes] = useState<string>("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const sourceAccount = accounts.find((a) => a.id === sourceAccountId);
  const destAccount = accounts.find((a) => a.id === destAccountId);
  const isCrossCurrency = Boolean(
    sourceAccount && destAccount && sourceAccount.currency !== destAccount.currency
  );

  // Sync destination amount when amount or rate changes in cross-currency
  useEffect(() => {
    if (isCrossCurrency && amount && rate) {
      const parsedAmt = parseFloat(amount);
      const parsedRate = parseFloat(rate);
      if (!isNaN(parsedAmt) && !isNaN(parsedRate) && parsedRate > 0) {
        setDestinationAmount((parsedAmt * parsedRate).toFixed(2));
      }
    } else if (!isCrossCurrency) {
      setDestinationAmount(amount);
    }
  }, [amount, rate, isCrossCurrency]);

  const mutation = useMutation({
    mutationFn: createTransfer,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.accounts.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.transactions.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.transfers.all });
      onOpenChange(false);
      resetForm();
    },
    onError: (err: any) => {
      setErrorMessage(
        err?.response?.data?.error?.message ||
          err?.message ||
          "Failed to execute transfer. Please check input parameters."
      );
    },
  });

  const resetForm = () => {
    setAmount("");
    setRate("");
    setDestinationAmount("");
    setReferenceRate("");
    setTransferFee("0.00");
    setNotes("");
    setErrorMessage(null);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!sourceAccountId || !destAccountId) {
      setErrorMessage("Please select both source and destination accounts.");
      return;
    }
    if (sourceAccountId === destAccountId) {
      setErrorMessage("Source and destination accounts must be different.");
      return;
    }
    if (!amount || parseFloat(amount) <= 0) {
      setErrorMessage("Transfer amount must be greater than zero.");
      return;
    }
    if (isCrossCurrency && (!rate || parseFloat(rate) <= 0)) {
      setErrorMessage("Please provide a valid exchange rate for cross-currency transfer.");
      return;
    }

    mutation.mutate({
      source_account_id: sourceAccountId,
      destination_account_id: destAccountId,
      amount,
      destination_amount: isCrossCurrency ? destinationAmount : undefined,
      rate: isCrossCurrency ? rate : undefined,
      reference_rate: isCrossCurrency && referenceRate ? referenceRate : undefined,
      transfer_fee: transferFee,
      occurred_on: occurredOn,
      notes,
    });
  };

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/60 backdrop-blur-xs z-50 animate-fade-in" />
        <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-lg bg-[var(--surface)] border border-[var(--border)] rounded-xl shadow-2xl p-6 z-50 focus:outline-hidden max-h-[90vh] overflow-y-auto">
          <div className="flex items-center justify-between border-b border-[var(--border)] pb-4 mb-4">
            <div className="flex items-center gap-2 text-gold">
              <ArrowRightLeft className="w-5 h-5" />
              <Dialog.Title className="font-display font-semibold text-lg text-main">
                Internal Account Transfer
              </Dialog.Title>
            </div>
            <Dialog.Close asChild>
              <button
                type="button"
                className="text-muted hover:text-main cursor-pointer"
                aria-label="Close"
              >
                <X className="w-4 h-4" />
              </button>
            </Dialog.Close>
          </div>

          {errorMessage && (
            <div className="flex items-start gap-2 p-3 mb-4 rounded-md bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{errorMessage}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Account selection row */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-muted mb-1">
                  From Account
                </label>
                <select
                  value={sourceAccountId}
                  onChange={(e) => setSourceAccountId(e.target.value)}
                  className="w-full rounded-md border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-xs text-main focus:border-[var(--accent)] focus:outline-hidden"
                >
                  {spendableAccounts.map((acc) => (
                    <option key={acc.id} value={acc.id}>
                      {acc.name} ({acc.currency})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-muted mb-1">
                  To Account
                </label>
                <select
                  value={destAccountId}
                  onChange={(e) => setDestAccountId(e.target.value)}
                  className="w-full rounded-md border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-xs text-main focus:border-[var(--accent)] focus:outline-hidden"
                >
                  {spendableAccounts.map((acc) => (
                    <option key={acc.id} value={acc.id}>
                      {acc.name} ({acc.currency})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Transfer Amount */}
            <div>
              <label className="block text-xs font-medium text-muted mb-1">
                Transfer Amount ({sourceAccount?.currency || "USD"})
              </label>
              <input
                type="text"
                placeholder="100.00"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                className="w-full rounded-md border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-sm font-mono text-main focus:border-[var(--accent)] focus:outline-hidden"
              />
            </div>

            {/* FX Section when currencies differ */}
            {isCrossCurrency && (
              <div className="rounded-lg bg-[var(--bg)] border border-[var(--border)] p-4 space-y-3">
                <div className="flex items-center gap-2 text-xs font-medium text-gold">
                  <RefreshCw className="w-3.5 h-3.5 animate-spin-slow" />
                  <span>Currency Conversion ({sourceAccount?.currency} → {destAccount?.currency})</span>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] text-muted mb-1">
                      Exchange Rate (1 {sourceAccount?.currency} = ? {destAccount?.currency})
                    </label>
                    <input
                      type="text"
                      placeholder="4050.00"
                      value={rate}
                      onChange={(e) => setRate(e.target.value)}
                      className="w-full rounded border border-[var(--border)] bg-[var(--surface)] px-2.5 py-1.5 text-xs font-mono text-main focus:border-[var(--accent)] focus:outline-hidden"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] text-muted mb-1">
                      Receiving Amount ({destAccount?.currency})
                    </label>
                    <input
                      type="text"
                      value={destinationAmount}
                      onChange={(e) => setDestinationAmount(e.target.value)}
                      className="w-full rounded border border-[var(--border)] bg-[var(--surface)] px-2.5 py-1.5 text-xs font-mono text-main focus:border-[var(--accent)] focus:outline-hidden"
                      placeholder="405000.00"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-[11px] text-muted mb-1">
                    Market Reference Rate (Optional, for spread calculation)
                  </label>
                  <input
                    type="text"
                    placeholder="4100.00"
                    value={referenceRate}
                    onChange={(e) => setReferenceRate(e.target.value)}
                    className="w-full rounded border border-[var(--border)] bg-[var(--surface)] px-2.5 py-1.5 text-xs font-mono text-main focus:border-[var(--accent)] focus:outline-hidden"
                  />
                  <p className="text-[10px] text-muted mt-1">
                    Difference between market reference and exchange rate is recorded as an explicit conversion fee.
                  </p>
                </div>
              </div>
            )}

            {/* Transfer Fee & Date */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-muted mb-1">
                  Bank Transfer Fee ({sourceAccount?.currency})
                </label>
                <input
                  type="text"
                  value={transferFee}
                  onChange={(e) => setTransferFee(e.target.value)}
                  className="w-full rounded-md border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-xs font-mono text-main focus:border-[var(--accent)] focus:outline-hidden"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-muted mb-1">
                  Transfer Date
                </label>
                <input
                  type="date"
                  value={occurredOn}
                  onChange={(e) => setOccurredOn(e.target.value)}
                  className="w-full rounded-md border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-xs text-main focus:border-[var(--accent)] focus:outline-hidden"
                />
              </div>
            </div>

            {/* Notes */}
            <div>
              <label className="block text-xs font-medium text-muted mb-1">
                Notes (Optional)
              </label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Reason or reference for transfer"
                rows={2}
                className="w-full rounded-md border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-xs text-main focus:border-[var(--accent)] focus:outline-hidden"
              />
            </div>

            {/* Actions */}
            <div className="flex items-center justify-end gap-3 pt-3 border-t border-[var(--border)]">
              <button
                type="button"
                onClick={() => onOpenChange(false)}
                className="px-4 py-2 text-xs font-medium text-muted hover:text-main cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={mutation.isPending}
                className="flex items-center gap-2 rounded bg-gold px-4 py-2 text-xs font-medium cursor-pointer shadow-sm hover:opacity-90 disabled:opacity-50"
              >
                {mutation.isPending ? "Transferring..." : "Execute Transfer"}
              </button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
};
