import React, { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  X,
  History,
  ArrowRight,
  Pencil,
  Archive,
  RotateCcw,
  AlertCircle,
  CheckCircle2,
} from "lucide-react";
import {
  archiveTransaction,
  getTransactionAudit,
  restoreTransaction,
  updateTransaction,
} from "../api";
import { Transaction } from "../types";
import { formatDateTime } from "@/lib/format";
import { MoneyDisplay } from "@/components/money";
import { queryKeys } from "@/lib/query-keys";
import { ApiError } from "@/lib/api/client";
import { parseMoneyInput } from "@/lib/money";
import { fetchCategories } from "@/features/categories/api";

interface TransactionAuditDrawerProps {
  transaction: Transaction | null;
  isOpen: boolean;
  onClose: () => void;
  onTransactionUpdated?: (tx: Transaction) => void;
}

export const TransactionAuditDrawer: React.FC<TransactionAuditDrawerProps> = ({
  transaction,
  isOpen,
  onClose,
  onTransactionUpdated,
}) => {
  const queryClient = useQueryClient();
  const [isEditing, setIsEditing] = useState(false);
  const [isArchiving, setIsArchiving] = useState(false);
  const [editTitle, setEditTitle] = useState("");
  const [editAmount, setEditAmount] = useState("");
  const [editOccurredOn, setEditOccurredOn] = useState("");
  const [editCategoryId, setEditCategoryId] = useState("");
  const [editMerchant, setEditMerchant] = useState("");
  const [editNotes, setEditNotes] = useState("");
  const [editReason, setEditReason] = useState("");
  const [archiveReason, setArchiveReason] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (transaction) {
      setEditTitle(transaction.title);
      setEditAmount(transaction.amount);
      setEditOccurredOn(transaction.occurred_on);
      setEditCategoryId(transaction.category_id || "");
      setEditMerchant(transaction.merchant || "");
      setEditNotes(transaction.notes || "");
      setEditReason("");
      setArchiveReason("");
      setIsEditing(false);
      setIsArchiving(false);
      setActionError(null);
      setActionSuccess(null);
    }
  }, [transaction?.id, transaction?.version]);

  const { data: auditLogs = [], isLoading } = useQuery({
    queryKey: ["transactions", "audit", transaction?.id],
    queryFn: () => (transaction ? getTransactionAudit(transaction.id) : Promise.resolve([])),
    enabled: isOpen && !!transaction,
  });

  const { data: categories = [] } = useQuery({
    queryKey: ["categories"],
    queryFn: fetchCategories,
    enabled: isOpen && isEditing,
  });

  const invalidateAll = (txId: string) => {
    queryClient.invalidateQueries({ queryKey: queryKeys.transactions.all });
    queryClient.invalidateQueries({ queryKey: queryKeys.accounts.all });
    queryClient.invalidateQueries({ queryKey: ["transactions", "audit", txId] });
    queryClient.invalidateQueries({ queryKey: ["dashboard-data"] });
    queryClient.invalidateQueries({ queryKey: ["budgets"] });
  };

  const updateMutation = useMutation({
    mutationFn: (payload: Parameters<typeof updateTransaction>[1]) =>
      updateTransaction(transaction!.id, payload),
    onSuccess: (updated) => {
      invalidateAll(updated.id);
      setIsEditing(false);
      setActionError(null);
      setActionSuccess("Transaction updated with new immutable revision.");
      onTransactionUpdated?.(updated);
    },
    onError: (err: unknown) => {
      setActionError(err instanceof ApiError ? err.message : "Failed to update transaction.");
    },
  });

  const archiveMutation = useMutation({
    mutationFn: (reason: string) => archiveTransaction(transaction!.id, reason),
    onSuccess: (archived) => {
      invalidateAll(archived.id);
      setIsArchiving(false);
      setActionError(null);
      setActionSuccess("Transaction archived and offsetting ledger entries posted.");
      onTransactionUpdated?.(archived);
    },
    onError: (err: unknown) => {
      setActionError(err instanceof ApiError ? err.message : "Failed to archive transaction.");
    },
  });

  const restoreMutation = useMutation({
    mutationFn: () => restoreTransaction(transaction!.id),
    onSuccess: (restored) => {
      invalidateAll(restored.id);
      setActionError(null);
      setActionSuccess("Transaction restored to active ledger.");
      onTransactionUpdated?.(restored);
    },
    onError: (err: unknown) => {
      setActionError(err instanceof ApiError ? err.message : "Failed to restore transaction.");
    },
  });

  if (!isOpen || !transaction) return null;

  const handleSaveEdit = (e: React.FormEvent) => {
    e.preventDefault();
    setActionError(null);
    setActionSuccess(null);

    if (!editReason.trim()) {
      setActionError("Please enter an audit reason for modifying this ledger entry.");
      return;
    }

    const parsed = parseMoneyInput(editAmount, 2);
    if (!parsed.ok) {
      setActionError("Please enter a valid monetary amount (up to 2 decimal places).");
      return;
    }

    updateMutation.mutate({
      expected_version: transaction.version,
      reason: editReason.trim(),
      title: editTitle.trim(),
      amount: parsed.serialized,
      occurred_on: editOccurredOn,
      category_id: transaction.is_split ? undefined : editCategoryId || null,
      merchant: editMerchant.trim() || undefined,
      notes: editNotes.trim() || undefined,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-xs">
      <div className="w-full max-w-lg bg-[var(--surface)] border-l border-[var(--border)] h-full overflow-y-auto p-6 shadow-2xl flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between border-b border-[var(--border)] pb-4 mb-5">
            <div className="flex items-center gap-2">
              <History className="w-5 h-5 text-gold" />
              <div>
                <h2 className="text-lg font-medium text-main">Transaction Inspector</h2>
                <p className="text-xs text-muted">Edit, archive, or inspect immutable revisions.</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-muted hover:text-main cursor-pointer"
              aria-label="Close"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {actionError && (
            <div className="mb-4 flex items-center gap-2 rounded-lg bg-[var(--negative-bg)] border border-[var(--negative-border)] p-3 text-xs text-[var(--negative)]">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{actionError}</span>
            </div>
          )}

          {actionSuccess && (
            <div className="mb-4 flex items-center gap-2 rounded-lg bg-[var(--positive-bg)] border border-[var(--positive-border)] p-3 text-xs text-[var(--positive)]">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{actionSuccess}</span>
            </div>
          )}

          {/* Transaction Summary Header */}
          <div className="rounded-xl bg-[var(--surface-raised)] border border-[var(--border)] p-4 mb-4 space-y-2">
            <div className="flex items-center justify-between gap-2">
              <span className="font-semibold text-main text-sm truncate">{transaction.title}</span>
              <MoneyDisplay
                amountMinor={transaction.amount_minor}
                currency={transaction.currency}
                className="font-bold text-sm shrink-0"
              />
            </div>
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted">
              <span>Account: {transaction.account_name}</span>
              <span className="font-mono">
                {transaction.occurred_on} · v{transaction.version}
              </span>
            </div>
            {transaction.tags && transaction.tags.length > 0 && (
              <div className="flex flex-wrap gap-1 pt-1">
                {transaction.tags.map((tag) => (
                  <span
                    key={tag}
                    className="text-[10px] px-2 py-0.5 rounded-full bg-[var(--surface)] border border-[var(--border)] text-gold font-medium"
                  >
                    #{tag}
                  </span>
                ))}
              </div>
            )}

            {/* Lifecycle Control Buttons */}
            <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-[var(--border)]">
              {!transaction.is_archived && (
                <button
                  type="button"
                  onClick={() => {
                    setIsEditing((v) => !v);
                    setIsArchiving(false);
                    setActionError(null);
                  }}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] hover:bg-[var(--surface-hover)] text-xs font-medium text-main cursor-pointer transition-colors"
                >
                  <Pencil className="w-3.5 h-3.5 text-gold" />
                  {isEditing ? "Cancel Edit" : "Edit Entry"}
                </button>
              )}

              {transaction.is_archived ? (
                <button
                  type="button"
                  onClick={() => restoreMutation.mutate()}
                  disabled={restoreMutation.isPending}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-[var(--positive-bg)] border border-[var(--positive-border)] text-xs font-medium text-[var(--positive)] cursor-pointer hover:opacity-90 disabled:opacity-50"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  {restoreMutation.isPending ? "Restoring..." : "Restore Entry"}
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => {
                    setIsArchiving((v) => !v);
                    setIsEditing(false);
                    setActionError(null);
                  }}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-[var(--negative-border)] bg-[var(--negative-bg)] text-xs font-medium text-[var(--negative)] cursor-pointer hover:opacity-90"
                >
                  <Archive className="w-3.5 h-3.5" />
                  Archive Entry
                </button>
              )}
            </div>
          </div>

          {/* Inline Edit Panel */}
          {isEditing && (
            <form
              onSubmit={handleSaveEdit}
              className="rounded-xl border border-[var(--border)] bg-[var(--surface-raised)] p-4 mb-5 space-y-3"
            >
              <div className="text-xs font-semibold text-main">Correct Ledger Entry (v{transaction.version} → v{transaction.version + 1})</div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="sm:col-span-2">
                  <label className="block text-[11px] font-medium text-muted mb-1">Title</label>
                  <input
                    type="text"
                    required
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    className="w-full rounded-lg bg-[var(--surface)] border border-[var(--border)] px-3 py-1.5 text-xs text-main focus:border-[var(--accent)] focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-medium text-muted mb-1">Amount ({transaction.currency})</label>
                  <input
                    type="text"
                    required
                    value={editAmount}
                    onChange={(e) => setEditAmount(e.target.value)}
                    className="w-full rounded-lg bg-[var(--surface)] border border-[var(--border)] px-3 py-1.5 text-xs font-mono text-main focus:border-[var(--accent)] focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-medium text-muted mb-1">Date</label>
                  <input
                    type="date"
                    required
                    value={editOccurredOn}
                    onChange={(e) => setEditOccurredOn(e.target.value)}
                    className="w-full rounded-lg bg-[var(--surface)] border border-[var(--border)] px-3 py-1.5 text-xs text-main focus:border-[var(--accent)] focus:outline-none"
                  />
                </div>
                {!transaction.is_split && categories.length > 0 && (
                  <div className="sm:col-span-2">
                    <label className="block text-[11px] font-medium text-muted mb-1">Category</label>
                    <select
                      value={editCategoryId}
                      onChange={(e) => setEditCategoryId(e.target.value)}
                      className="w-full rounded-lg bg-[var(--surface)] border border-[var(--border)] px-3 py-1.5 text-xs text-main focus:border-[var(--accent)] focus:outline-none"
                    >
                      <option value="">Uncategorized</option>
                      {categories.map((cat) => (
                        <option key={cat.id} value={cat.id}>
                          {cat.name}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
                <div>
                  <label className="block text-[11px] font-medium text-muted mb-1">Merchant</label>
                  <input
                    type="text"
                    value={editMerchant}
                    onChange={(e) => setEditMerchant(e.target.value)}
                    className="w-full rounded-lg bg-[var(--surface)] border border-[var(--border)] px-3 py-1.5 text-xs text-main focus:border-[var(--accent)] focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-medium text-muted mb-1">Notes</label>
                  <input
                    type="text"
                    value={editNotes}
                    onChange={(e) => setEditNotes(e.target.value)}
                    className="w-full rounded-lg bg-[var(--surface)] border border-[var(--border)] px-3 py-1.5 text-xs text-main focus:border-[var(--accent)] focus:outline-none"
                  />
                </div>
                <div className="sm:col-span-2">
                  <label className="block text-[11px] font-medium text-muted mb-1">
                    Audit Reason <span className="text-[var(--negative)]">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={editReason}
                    onChange={(e) => setEditReason(e.target.value)}
                    placeholder="e.g. Corrected receipt total or merchant typo"
                    className="w-full rounded-lg bg-[var(--surface)] border border-[var(--border)] px-3 py-1.5 text-xs text-main focus:border-[var(--accent)] focus:outline-none"
                  />
                </div>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsEditing(false)}
                  className="px-3 py-1.5 text-xs text-muted hover:text-main cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={updateMutation.isPending}
                  className="px-3.5 py-1.5 rounded-lg bg-gold text-xs font-semibold cursor-pointer disabled:opacity-50"
                >
                  {updateMutation.isPending ? "Posting..." : "Save Revision"}
                </button>
              </div>
            </form>
          )}

          {/* Inline Archive Confirmation */}
          {isArchiving && (
            <div className="rounded-xl border border-[var(--negative-border)] bg-[var(--negative-bg)] p-4 mb-5 space-y-3">
              <div className="text-xs font-semibold text-[var(--negative)]">
                Soft-Archive Transaction
              </div>
              <p className="text-[11px] text-muted">
                Archiving preserves full audit history while reversing the ledger impact.
              </p>
              <input
                type="text"
                value={archiveReason}
                onChange={(e) => setArchiveReason(e.target.value)}
                placeholder="Reason for archiving (e.g. Duplicate entry)"
                className="w-full rounded-lg bg-[var(--surface)] border border-[var(--border)] px-3 py-1.5 text-xs text-main focus:border-[var(--negative)] focus:outline-none"
              />
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setIsArchiving(false)}
                  className="px-3 py-1.5 text-xs text-muted hover:text-main cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={() => archiveMutation.mutate(archiveReason.trim() || "Archived by user")}
                  disabled={archiveMutation.isPending}
                  className="px-3.5 py-1.5 rounded-lg bg-[var(--negative)] text-white text-xs font-semibold cursor-pointer disabled:opacity-50"
                >
                  {archiveMutation.isPending ? "Archiving..." : "Confirm Archive"}
                </button>
              </div>
            </div>
          )}

          {/* Revisions Timeline */}
          <div className="space-y-4">
            <h3 className="text-xs font-semibold text-muted uppercase tracking-wider">
              Revision Log ({auditLogs.length})
            </h3>

            {isLoading ? (
              <div className="py-6 text-center text-xs text-muted">Loading audit log...</div>
            ) : (
              <div className="relative pl-6 space-y-6 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-[var(--border)]">
                {auditLogs.map((log) => (
                  <div key={log.id} className="relative">
                    <span className="absolute -left-6 top-1.5 w-2.5 h-2.5 rounded-full bg-gold ring-4 ring-[var(--surface)]" />

                    <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-raised)] p-3 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-main">
                          Revision {log.revision} &bull; {log.action.toUpperCase()}
                        </span>
                        <span className="text-[10px] text-faint font-mono">
                          {formatDateTime(log.created_at)}
                        </span>
                      </div>

                      {log.reason && (
                        <div className="text-xs text-muted bg-[var(--surface)] border border-[var(--border)] px-2.5 py-1.5 rounded">
                          <span className="text-faint font-medium">Reason: </span>
                          <span className="italic">{log.reason}</span>
                        </div>
                      )}

                      {log.changed_fields && log.changed_fields.length > 0 && (
                        <div className="space-y-1 pt-1">
                          <span className="text-[11px] font-medium text-muted">
                            Modified Fields:
                          </span>
                          <div className="flex flex-wrap gap-1">
                            {log.changed_fields.map((f) => (
                              <span
                                key={f}
                                className="text-[10px] rounded bg-[var(--surface)] border border-[var(--border)] px-1.5 py-0.5 text-main font-mono"
                              >
                                {f}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {log.revision > 1 && log.before && log.after && (
                        <div className="text-[11px] text-muted space-y-1 pt-1 border-t border-[var(--border)]">
                          {log.changed_fields.includes("amount") && (
                            <div className="flex items-center gap-2">
                              <span>Amount:</span>
                              <span className="line-through text-negative font-tabular">
                                {String(log.before.amount || "")}
                              </span>
                              <ArrowRight className="w-3 h-3 text-muted" />
                              <span className="text-positive font-tabular font-medium">
                                {String(log.after.amount || "")}
                              </span>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="pt-4 border-t border-[var(--border)] mt-6 text-center">
          <p className="text-[11px] text-faint">
            Accounting rule: Past posted entries are never overwritten; previous entries are reversed with offsetting credits/debits.
          </p>
        </div>
      </div>
    </div>
  );
};
