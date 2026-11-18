import React, { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import * as Dialog from "@radix-ui/react-dialog";
import { ArrowDownRight, X, AlertCircle, Info } from "lucide-react";
import { Account } from "@/features/accounts/types";
import { Liability, recordDebtRepayment } from "../api/debts-api";

interface RepaymentDialogProps {
  liability: Liability | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  accounts: Account[];
}

export const RepaymentDialog: React.FC<RepaymentDialogProps> = ({
  liability,
  open,
  onOpenChange,
  accounts,
}) => {
  const queryClient = useQueryClient();
  const eligibleAccounts = accounts.filter(
    (a) => !a.is_archived && a.currency === liability?.currency
  );

  const [payingAccountId, setPayingAccountId] = useState(
    liability?.linked_account_id || eligibleAccounts[0]?.id || ""
  );
  const [principalAmount, setPrincipalAmount] = useState("");
  const [interestAmount, setInterestAmount] = useState("0.00");
  const [feeAmount, setFeeAmount] = useState("0.00");
  const [paidOn, setPaidOn] = useState(new Date().toISOString().split("T")[0]);
  const [note, setNote] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: (data: { liabilityId: string; payload: any }) =>
      recordDebtRepayment(data.liabilityId, data.payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["debts"] });
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      onOpenChange(false);
      resetForm();
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.message || err?.message || "Failed to record repayment.";
      setErrorMessage(msg);
    },
  });

  const resetForm = () => {
    setPrincipalAmount("");
    setInterestAmount("0.00");
    setFeeAmount("0.00");
    setNote("");
    setErrorMessage(null);
  };

  if (!liability) return null;

  const pVal = parseFloat(principalAmount) || 0;
  const iVal = parseFloat(interestAmount) || 0;
  const fVal = parseFloat(feeAmount) || 0;
  const totalVal = (pVal + iVal + fVal).toFixed(2);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (pVal <= 0 && iVal <= 0 && fVal <= 0) {
      setErrorMessage("Total repayment must be greater than zero.");
      return;
    }

    if (pVal > parseFloat(liability.outstanding_principal)) {
      setErrorMessage(
        `Principal repayment ($${pVal.toFixed(2)}) cannot exceed outstanding principal ($${liability.outstanding_principal}).`
      );
      return;
    }

    mutation.mutate({
      liabilityId: liability.id,
      payload: {
        paying_account_id: payingAccountId,
        principal_amount: principalAmount || "0.00",
        interest_amount: interestAmount || "0.00",
        fee_amount: feeAmount || "0.00",
        paid_on: paidOn,
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
              <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <ArrowDownRight className="w-5 h-5" />
              </div>
              <div>
                <Dialog.Title className="text-lg font-bold text-main">
                  Record Debt Repayment
                </Dialog.Title>
                <p className="text-xs text-muted">{liability.name}</p>
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

          {/* Double-entry explanation notice */}
          <div className="mt-4 p-3 rounded-xl bg-gold/5 border border-gold/20 text-xs space-y-1.5">
            <div className="flex items-center gap-1.5 font-medium text-gold">
              <Info className="w-4 h-4 shrink-0" />
              Financial Accounting Effect
            </div>
            <p className="text-[11px] text-muted">
              • Principal (${pVal.toFixed(2)}) reduces your debt: moves value from asset to liability (net worth unaffected).<br />
              • Interest (${iVal.toFixed(2)}) & Fees (${fVal.toFixed(2)}) are recognized as expenses: net worth decreases by ${(iVal + fVal).toFixed(2)}.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="mt-4 space-y-4">
            <div>
              <label className="block text-xs font-medium text-muted mb-1">Paying Account</label>
              <select
                value={payingAccountId}
                onChange={(e) => setPayingAccountId(e.target.value)}
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
                <label className="block text-xs font-medium text-muted">Principal Reduction</label>
                <span className="text-[11px] text-muted">
                  Max: ${liability.outstanding_principal}
                </span>
              </div>
              <input
                type="number"
                step="0.01"
                value={principalAmount}
                onChange={(e) => setPrincipalAmount(e.target.value)}
                placeholder="0.00"
                className="w-full px-3 py-2 rounded-lg bg-[var(--surface-muted)] border border-[var(--border)] text-sm text-main focus:border-gold outline-hidden"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-muted mb-1">Interest Expense</label>
                <input
                  type="number"
                  step="0.01"
                  value={interestAmount}
                  onChange={(e) => setInterestAmount(e.target.value)}
                  placeholder="0.00"
                  className="w-full px-3 py-2 rounded-lg bg-[var(--surface-muted)] border border-[var(--border)] text-sm text-main focus:border-gold outline-hidden"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-muted mb-1">Bank / Finance Fee</label>
                <input
                  type="number"
                  step="0.01"
                  value={feeAmount}
                  onChange={(e) => setFeeAmount(e.target.value)}
                  placeholder="0.00"
                  className="w-full px-3 py-2 rounded-lg bg-[var(--surface-muted)] border border-[var(--border)] text-sm text-main focus:border-gold outline-hidden"
                />
              </div>
            </div>

            <div className="p-3 rounded-lg bg-[var(--surface-muted)] border border-[var(--border)] flex items-center justify-between">
              <span className="text-xs text-muted">Total Payment</span>
              <span className="text-base font-bold text-main font-mono">
                ${totalVal} {liability.currency}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-muted mb-1">Payment Date</label>
                <input
                  type="date"
                  value={paidOn}
                  onChange={(e) => setPaidOn(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-[var(--surface-muted)] border border-[var(--border)] text-sm text-main focus:border-gold outline-hidden"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-muted mb-1">Note (Optional)</label>
                <input
                  type="text"
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder="e.g. Check #104"
                  className="w-full px-3 py-2 rounded-lg bg-[var(--surface-muted)] border border-[var(--border)] text-sm text-main focus:border-gold outline-hidden"
                />
              </div>
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
                {mutation.isPending ? "Posting..." : "Confirm Repayment"}
              </button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
};
