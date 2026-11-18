import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { X, AlertCircle } from "lucide-react";
import { createTransaction } from "../api";
import { TransactionType, SpendingNecessity } from "../types";
import { SplitEditor, SplitItem } from "./split-editor";
import { getAccounts } from "@/features/accounts/api";
import { queryKeys } from "@/lib/query-keys";
import { ApiError } from "@/lib/api/client";
import { parseMoneyInput } from "@/lib/money";

interface CreateTransactionDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

export const CreateTransactionDrawer: React.FC<CreateTransactionDrawerProps> = ({
  isOpen,
  onClose,
}) => {
  const queryClient = useQueryClient();
  const [txType, setTxType] = useState<TransactionType>("expense");
  const [accountId, setAccountId] = useState("");
  const [amount, setAmount] = useState("");
  const [title, setTitle] = useState("");
  const [occurredOn, setOccurredOn] = useState(() => new Date().toISOString().slice(0, 10));
  const [categoryId, setCategoryId] = useState("");
  const [necessity, setNecessity] = useState<SpendingNecessity | "">("");
  const [merchant, setMerchant] = useState("");
  const [notes, setNotes] = useState("");
  const [isSplit, setIsSplit] = useState(false);
  const [splits, setSplits] = useState<SplitItem[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { data: accounts = [] } = useQuery({
    queryKey: queryKeys.accounts.list(false),
    queryFn: () => getAccounts(false),
  });

  const selectedAccount = accounts.find((a) => a.id === accountId) || accounts[0];
  const currency = selectedAccount?.currency || "USD";

  const mutation = useMutation({
    mutationFn: createTransaction,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.transactions.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.accounts.all });
      onClose();
      // Reset
      setTitle("");
      setAmount("");
      setNotes("");
      setMerchant("");
      setIsSplit(false);
      setSplits([]);
      setErrorMessage(null);
    },
    onError: (err: unknown) => {
      if (err instanceof ApiError) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage("Failed to record transaction. Please verify your inputs.");
      }
    },
  });

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    const parsedMoney = parseMoneyInput(amount, 2);
    if (!parsedMoney.ok) {
      setErrorMessage("Please enter a valid amount (maximum 2 decimal digits).");
      return;
    }

    const currentAccId = accountId || selectedAccount?.id;
    if (!currentAccId) {
      setErrorMessage("Please select an account.");
      return;
    }

    let splitsPayload = undefined;
    if (isSplit) {
      if (splits.length < 2) {
        setErrorMessage("A split transaction must have at least 2 categories.");
        return;
      }
      splitsPayload = splits.map((s) => ({
        category_id: s.category_id || "",
        amount: typeof s.amount === "number" ? (s.amount / 100).toFixed(2) : String(s.amount),
        memo: s.memo || "",
      }));
    }

    mutation.mutate({
      type: txType,
      account_id: currentAccId,
      amount: parsedMoney.serialized,
      currency,
      occurred_on: occurredOn,
      title: title.trim(),
      category_id: isSplit ? undefined : categoryId || undefined,
      splits: splitsPayload,
      necessity: necessity ? necessity : undefined,
      merchant: merchant.trim() || undefined,
      notes: notes.trim() || undefined,
    });
  };

  const totalMinor = parseMoneyInput(amount, 2).ok
    ? (parseMoneyInput(amount, 2) as any).amountMinor
    : 0;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-xs">
      <div className="w-full max-w-lg bg-[var(--surface)] border-l border-[var(--border)] h-full overflow-y-auto p-6 shadow-2xl flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between border-b border-[var(--border)] pb-4 mb-6">
            <div>
              <h2 className="text-lg font-medium text-main">Record Transaction</h2>
              <p className="text-xs text-muted mt-0.5">
                Every transaction posts directly to the double-entry ledger.
              </p>
            </div>
            <button onClick={onClose} className="text-muted hover:text-main cursor-pointer" aria-label="Close">
              <X className="w-5 h-5" />
            </button>
          </div>

          {errorMessage && (
            <div className="mb-4 flex items-center gap-2 rounded bg-red-950/40 border border-red-900/60 p-3 text-xs text-red-200">
              <AlertCircle className="w-4 h-4 shrink-0 text-negative" />
              <span>{errorMessage}</span>
            </div>
          )}

          <form id="tx-form" onSubmit={handleSubmit} className="space-y-4">
            {/* Type selector */}
            <div className="flex rounded bg-[var(--surface-raised)] border border-[var(--border)] p-1">
              <button
                type="button"
                onClick={() => setTxType("expense")}
                className={`flex-1 py-1.5 text-xs font-medium rounded transition-colors cursor-pointer ${
                  txType === "expense"
                    ? "bg-negative/20 text-negative font-semibold"
                    : "text-muted hover:text-main"
                }`}
              >
                Expense
              </button>
              <button
                type="button"
                onClick={() => setTxType("income")}
                className={`flex-1 py-1.5 text-xs font-medium rounded transition-colors cursor-pointer ${
                  txType === "income"
                    ? "bg-positive/20 text-positive font-semibold"
                    : "text-muted hover:text-main"
                }`}
              >
                Income
              </button>
            </div>

            {/* Account & Currency */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-muted mb-1">Account</label>
                <select
                  value={accountId || selectedAccount?.id || ""}
                  onChange={(e) => setAccountId(e.target.value)}
                  className="w-full rounded bg-[var(--surface-raised)] border border-[var(--border)] px-3 py-2 text-sm text-main focus:border-[var(--accent)] focus:outline-none"
                >
                  {accounts.map((acc) => (
                    <option key={acc.id} value={acc.id}>
                      {acc.name} ({acc.currency})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-muted mb-1">Date</label>
                <input
                  type="date"
                  required
                  value={occurredOn}
                  onChange={(e) => setOccurredOn(e.target.value)}
                  className="w-full rounded bg-[var(--surface-raised)] border border-[var(--border)] px-3 py-2 text-sm text-main focus:border-[var(--accent)] focus:outline-none"
                />
              </div>
            </div>

            {/* Title & Amount */}
            <div className="grid grid-cols-3 gap-3">
              <div className="col-span-2">
                <label className="block text-xs font-medium text-muted mb-1">Title</label>
                <input
                  type="text"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Weekly Groceries, Monthly Rent"
                  className="w-full rounded bg-[var(--surface-raised)] border border-[var(--border)] px-3 py-2 text-sm text-main focus:border-[var(--accent)] focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-muted mb-1">Amount</label>
                <div className="relative">
                  <input
                    type="text"
                    required
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                    placeholder="0.00"
                    className="w-full rounded bg-[var(--surface-raised)] border border-[var(--border)] px-3 py-2 text-sm text-main font-tabular focus:border-[var(--accent)] focus:outline-none"
                  />
                  <span className="absolute right-2.5 top-2 text-xs text-muted font-tabular">
                    {currency}
                  </span>
                </div>
              </div>
            </div>

            {/* Splits toggle or Category */}
            <div className="pt-2">
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs font-medium text-muted">Category Allocation</label>
                <label className="flex items-center gap-1.5 text-xs text-gold cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={isSplit}
                    onChange={(e) => {
                      setIsSplit(e.target.checked);
                      if (e.target.checked && splits.length === 0) {
                        setSplits([
                          { amount: Math.round(totalMinor * 0.6) },
                          { amount: Math.round(totalMinor * 0.4) },
                        ]);
                      }
                    }}
                    className="rounded border-[var(--border)] bg-[var(--surface)] accent-[var(--accent)]"
                  />
                  Split into multiple categories
                </label>
              </div>

              {isSplit ? (
                <SplitEditor
                  total={totalMinor}
                  currency={currency}
                  value={splits}
                  onChange={setSplits}
                  categories={[
                    { id: "11111111-1111-1111-1111-111111111111", name: "Groceries" },
                    { id: "22222222-2222-2222-2222-222222222222", name: "Household Supplies" },
                    { id: "33333333-3333-3333-3333-333333333333", name: "Dining Out" },
                    { id: "44444444-4444-4444-4444-444444444444", name: "Transportation" },
                    { id: "55555555-5555-5555-5555-555555555555", name: "Utilities" },
                  ]}
                />
              ) : (
                <input
                  type="text"
                  value={categoryId}
                  onChange={(e) => setCategoryId(e.target.value)}
                  placeholder="Category Name or ID"
                  className="w-full rounded bg-[var(--surface-raised)] border border-[var(--border)] px-3 py-2 text-sm text-main focus:border-[var(--accent)] focus:outline-none"
                />
              )}
            </div>

            {/* Necessity & Merchant */}
            <div className="grid grid-cols-2 gap-3 pt-2">
              <div>
                <label className="block text-xs font-medium text-muted mb-1">
                  Spending Necessity <span className="text-faint font-normal">(Optional)</span>
                </label>
                <select
                  value={necessity}
                  onChange={(e) => setNecessity(e.target.value as SpendingNecessity)}
                  className="w-full rounded bg-[var(--surface-raised)] border border-[var(--border)] px-3 py-2 text-sm text-main focus:border-[var(--accent)] focus:outline-none"
                >
                  <option value="">Unclassified</option>
                  <option value="essential">Essential (Needs)</option>
                  <option value="important">Important</option>
                  <option value="lifestyle">Lifestyle (Wants)</option>
                  <option value="unplanned">Unplanned</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-muted mb-1">
                  Merchant / Payee <span className="text-faint font-normal">(Optional)</span>
                </label>
                <input
                  type="text"
                  value={merchant}
                  onChange={(e) => setMerchant(e.target.value)}
                  placeholder="e.g. Supermarket, Landlord"
                  className="w-full rounded bg-[var(--surface-raised)] border border-[var(--border)] px-3 py-2 text-sm text-main focus:border-[var(--accent)] focus:outline-none"
                />
              </div>
            </div>

            {/* Notes */}
            <div>
              <label className="block text-xs font-medium text-muted mb-1">
                Notes <span className="text-faint font-normal">(Optional)</span>
              </label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={2}
                placeholder="Additional financial details..."
                className="w-full rounded bg-[var(--surface-raised)] border border-[var(--border)] px-3 py-2 text-sm text-main focus:border-[var(--accent)] focus:outline-none"
              />
            </div>
          </form>
        </div>

        <div className="flex items-center justify-end gap-3 pt-4 border-t border-[var(--border)] mt-6">
          <button
            type="button"
            onClick={onClose}
            className="rounded px-4 py-2 text-xs font-medium text-muted hover:text-main cursor-pointer"
          >
            Cancel
          </button>
          <button
            type="submit"
            form="tx-form"
            disabled={mutation.isPending}
            className="rounded bg-gold px-5 py-2 text-xs font-semibold cursor-pointer disabled:opacity-50 shadow-xs"
          >
            {mutation.isPending ? "Recording..." : "Record Transaction"}
          </button>
        </div>
      </div>
    </div>
  );
};
