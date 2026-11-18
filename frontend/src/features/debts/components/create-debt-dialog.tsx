import React, { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import * as Dialog from "@radix-ui/react-dialog";
import { CreditCard, X, AlertCircle, Info } from "lucide-react";
import { Account } from "@/features/accounts/types";
import { createLiability } from "../api/debts-api";

interface CreateDebtDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  accounts: Account[];
}

export const CreateDebtDialog: React.FC<CreateDebtDialogProps> = ({
  open,
  onOpenChange,
  accounts,
}) => {
  const queryClient = useQueryClient();
  const activeAccounts = accounts.filter((a) => !a.is_archived);

  const [name, setName] = useState("");
  const [originalPrincipal, setOriginalPrincipal] = useState("");
  const [currency, setCurrency] = useState("USD");
  const [liabilityType, setLiabilityType] = useState("personal_loan");
  const [interestRate, setInterestRate] = useState("");
  const [interestType, setInterestType] = useState("simple");
  const [lender, setLender] = useState("");
  const [dueDay, setDueDay] = useState("");
  const [nextDueDate, setNextDueDate] = useState("");
  const [disburseAccountId, setDisburseAccountId] = useState("");
  const [notes, setNotes] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: createLiability,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["debts"] });
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      onOpenChange(false);
      resetForm();
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.message || err?.message || "Failed to create liability.";
      setErrorMessage(msg);
    },
  });

  const resetForm = () => {
    setName("");
    setOriginalPrincipal("");
    setInterestRate("");
    setLender("");
    setDueDay("");
    setNextDueDate("");
    setDisburseAccountId("");
    setNotes("");
    setErrorMessage(null);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!name.trim()) {
      setErrorMessage("Liability name is required.");
      return;
    }
    const amt = parseFloat(originalPrincipal);
    if (isNaN(amt) || amt <= 0) {
      setErrorMessage("Principal amount must be a positive number.");
      return;
    }

    mutation.mutate({
      name: name.trim(),
      original_principal: originalPrincipal,
      currency,
      liability_type: liabilityType,
      interest_rate: interestRate ? interestRate : null,
      interest_type: interestRate ? interestType : "none",
      lender: lender.trim() || null,
      due_day: dueDay ? parseInt(dueDay, 10) : null,
      next_due_date: nextDueDate || null,
      initial_disbursement_account_id: disburseAccountId || null,
      notes: notes.trim() || null,
    });
  };

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/60 backdrop-blur-xs z-50 animate-fade-in" />
        <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-lg bg-[var(--surface)] border border-[var(--border)] rounded-2xl p-6 shadow-2xl z-50 animate-scale-in max-h-[90vh] overflow-y-auto">
          <div className="flex items-center justify-between pb-4 border-b border-[var(--border)]">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-gold/10 text-gold border border-gold/20">
                <CreditCard className="w-5 h-5" />
              </div>
              <Dialog.Title className="text-lg font-bold text-main">
                Add Liability / Loan
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
              <label className="block text-xs font-medium text-muted mb-1">Loan / Liability Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Student Loan, Auto Financing, Mortgage"
                className="w-full px-3 py-2 rounded-lg bg-[var(--surface-muted)] border border-[var(--border)] text-sm text-main focus:border-gold outline-hidden"
                required
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-muted mb-1">Original Principal</label>
                <input
                  type="number"
                  step="0.01"
                  value={originalPrincipal}
                  onChange={(e) => setOriginalPrincipal(e.target.value)}
                  placeholder="5000.00"
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
                <label className="block text-xs font-medium text-muted mb-1">Liability Type</label>
                <select
                  value={liabilityType}
                  onChange={(e) => setLiabilityType(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-[var(--surface-muted)] border border-[var(--border)] text-sm text-main focus:border-gold outline-hidden"
                >
                  <option value="personal_loan">Personal Loan</option>
                  <option value="student_loan">Student Loan</option>
                  <option value="credit_card">Credit Card</option>
                  <option value="mortgage">Mortgage</option>
                  <option value="family_loan">Family Loan</option>
                  <option value="other">Other Liability</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-muted mb-1">Lender / Creditor</label>
                <input
                  type="text"
                  value={lender}
                  onChange={(e) => setLender(e.target.value)}
                  placeholder="e.g. Bank, Chase, Family member"
                  className="w-full px-3 py-2 rounded-lg bg-[var(--surface-muted)] border border-[var(--border)] text-sm text-main focus:border-gold outline-hidden"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-muted mb-1">Interest Rate (% APR)</label>
                <input
                  type="number"
                  step="0.0001"
                  value={interestRate}
                  onChange={(e) => setInterestRate(e.target.value)}
                  placeholder="5.2500"
                  className="w-full px-3 py-2 rounded-lg bg-[var(--surface-muted)] border border-[var(--border)] text-sm text-main focus:border-gold outline-hidden"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-muted mb-1">Interest Type</label>
                <select
                  value={interestType}
                  onChange={(e) => setInterestType(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-[var(--surface-muted)] border border-[var(--border)] text-sm text-main focus:border-gold outline-hidden"
                >
                  <option value="simple">Simple</option>
                  <option value="compound">Compound</option>
                  <option value="none">Interest-free</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-muted mb-1">Monthly Due Day (1-31)</label>
                <input
                  type="number"
                  min="1"
                  max="31"
                  value={dueDay}
                  onChange={(e) => setDueDay(e.target.value)}
                  placeholder="15"
                  className="w-full px-3 py-2 rounded-lg bg-[var(--surface-muted)] border border-[var(--border)] text-sm text-main focus:border-gold outline-hidden"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-muted mb-1">Next Due Date</label>
                <input
                  type="date"
                  value={nextDueDate}
                  onChange={(e) => setNextDueDate(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-[var(--surface-muted)] border border-[var(--border)] text-sm text-main focus:border-gold outline-hidden"
                />
              </div>
            </div>

            {/* Optional initial disbursement */}
            <div className="p-3 rounded-xl bg-gold/5 border border-gold/20 space-y-2">
              <div className="flex items-center gap-1.5 text-xs font-medium text-gold">
                <Info className="w-4 h-4 shrink-0" />
                Initial Disbursement (Optional)
              </div>
              <p className="text-[11px] text-muted">
                If this is a newly borrowed loan received into an account, select the receiving account below to deposit funds and track double-entry debt.
              </p>
              <select
                value={disburseAccountId}
                onChange={(e) => setDisburseAccountId(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-[var(--surface-muted)] border border-[var(--border)] text-sm text-main focus:border-gold outline-hidden"
              >
                <option value="">Do not disburse (Pre-existing loan)</option>
                {activeAccounts
                  .filter((a) => a.currency === currency)
                  .map((acc) => (
                    <option key={acc.id} value={acc.id}>
                      Deposit to: {acc.name} ({acc.currency})
                    </option>
                  ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-muted mb-1">Notes (Optional)</label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Loan terms, account numbers, or details"
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
                {mutation.isPending ? "Creating..." : "Add Liability"}
              </button>
            </div>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
};
