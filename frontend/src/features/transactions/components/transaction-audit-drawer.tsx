import React from "react";
import { useQuery } from "@tanstack/react-query";
import { X, History, ArrowRight } from "lucide-react";
import { getTransactionAudit } from "../api";
import { Transaction } from "../types";
import { formatDateTime } from "@/lib/format";
import { MoneyDisplay } from "@/components/money";

interface TransactionAuditDrawerProps {
  transaction: Transaction | null;
  isOpen: boolean;
  onClose: () => void;
}

export const TransactionAuditDrawer: React.FC<TransactionAuditDrawerProps> = ({
  transaction,
  isOpen,
  onClose,
}) => {
  const { data: auditLogs = [], isLoading } = useQuery({
    queryKey: ["transactions", "audit", transaction?.id],
    queryFn: () => (transaction ? getTransactionAudit(transaction.id) : Promise.resolve([])),
    enabled: isOpen && !!transaction,
  });

  if (!isOpen || !transaction) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-xs">
      <div className="w-full max-w-lg bg-[var(--surface)] border-l border-[var(--border)] h-full overflow-y-auto p-6 shadow-2xl flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between border-b border-[var(--border)] pb-4 mb-6">
            <div className="flex items-center gap-2">
              <History className="w-5 h-5 text-gold" />
              <div>
                <h2 className="text-lg font-medium text-main">Audit History</h2>
                <p className="text-xs text-muted">Immutable ledger revision trail.</p>
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

          {/* Transaction Summary Header */}
          <div className="rounded-lg bg-[var(--surface-raised)] border border-[var(--border)] p-4 mb-6 space-y-1">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-main text-sm">{transaction.title}</span>
              <MoneyDisplay
                amountMinor={transaction.amount_minor}
                currency={transaction.currency}
                className="font-bold text-sm"
              />
            </div>
            <div className="flex items-center justify-between text-xs text-muted">
              <span>Account: {transaction.account_name}</span>
              <span>Date: {transaction.occurred_on}</span>
            </div>
          </div>

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

                    <div className="rounded border border-[var(--border)] bg-[var(--surface-raised)] p-3 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-main">
                          Revision {log.revision} &bull; {log.action.toUpperCase()}
                        </span>
                        <span className="text-[10px] text-faint">
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
                                className="text-[10px] rounded bg-gray-800 border border-gray-700 px-1.5 py-0.5 text-main font-mono"
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
