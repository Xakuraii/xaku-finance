import React from "react";
import { Transaction } from "../types";
import { MoneyDisplay } from "@/components/money";
import { formatDate } from "@/lib/format";
import { History, Split } from "lucide-react";

interface TransactionsTableProps {
  transactions: Transaction[];
  isLoading: boolean;
  onSelectTransaction: (tx: Transaction) => void;
}

export const TransactionsTable: React.FC<TransactionsTableProps> = ({
  transactions,
  isLoading,
  onSelectTransaction,
}) => {
  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] overflow-hidden shadow-xs">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-[var(--border)] bg-[var(--surface-raised)] text-[11px] font-medium text-muted uppercase tracking-wider">
            <tr>
              <th className="py-3 px-4">Date</th>
              <th className="py-3 px-4">Title / Merchant</th>
              <th className="py-3 px-4">Account</th>
              <th className="py-3 px-4">Category</th>
              <th className="py-3 px-4">Status</th>
              <th className="py-3 px-4 text-right">Amount</th>
              <th className="py-3 px-4 text-right">Audit</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--border)] font-normal">
            {isLoading ? (
              <tr>
                <td colSpan={7} className="py-8 text-center text-xs text-muted">
                  Loading transactions...
                </td>
              </tr>
            ) : transactions.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-12 text-center text-muted">
                  <p className="text-sm font-medium text-main">No transactions recorded yet</p>
                  <p className="text-xs text-faint mt-1">
                    Add income or expenses to begin tracking your cash flow.
                  </p>
                </td>
              </tr>
            ) : (
              transactions.map((tx) => {
                const isPending = tx.status === "pending";
                const isExpense = tx.type === "expense";
                const isIncome = tx.type === "income";

                return (
                  <tr
                    key={tx.id}
                    onClick={() => onSelectTransaction(tx)}
                    className={`hover:bg-[var(--surface-raised)] transition-colors cursor-pointer ${
                      isPending ? "border-dashed" : ""
                    } ${tx.is_archived ? "opacity-50" : ""}`}
                  >
                    <td className="py-3 px-4 text-xs font-tabular text-muted whitespace-nowrap">
                      {formatDate(tx.occurred_on)}
                    </td>

                    <td className="py-3 px-4">
                      <div className="font-medium text-main flex items-center gap-1.5">
                        {tx.title}
                        {tx.is_split && (
                          <span
                            className="inline-flex items-center gap-0.5 text-[10px] rounded bg-gold/10 text-gold border border-gold/30 px-1 py-0.2"
                            title="Split transaction"
                          >
                            <Split className="w-2.5 h-2.5" />
                            Split
                          </span>
                        )}
                      </div>
                      {tx.merchant && (
                        <div className="text-[11px] text-faint">{tx.merchant}</div>
                      )}
                    </td>

                    <td className="py-3 px-4 text-xs text-muted whitespace-nowrap">
                      {tx.account_name}
                    </td>

                    <td className="py-3 px-4 text-xs text-muted">
                      {tx.is_split
                        ? `${tx.splits.length} splits`
                        : tx.category_name || "Uncategorized"}
                    </td>

                    <td className="py-3 px-4">
                      {tx.status === "pending" ? (
                        <span className="inline-flex text-[10px] rounded bg-amber-950/40 border border-amber-800 px-1.5 py-0.5 text-warning font-medium">
                          Pending
                        </span>
                      ) : tx.status === "cancelled" ? (
                        <span className="inline-flex text-[10px] rounded bg-gray-900 border border-gray-800 px-1.5 py-0.5 text-faint">
                          Cancelled
                        </span>
                      ) : (
                        <span className="inline-flex text-[10px] rounded bg-green-950/30 border border-green-900/50 px-1.5 py-0.5 text-positive font-medium">
                          Completed
                        </span>
                      )}
                    </td>

                    <td className="py-3 px-4 text-right whitespace-nowrap">
                      <MoneyDisplay
                        amountMinor={tx.amount_minor}
                        currency={tx.currency}
                        showSign={isIncome || isExpense}
                        colored
                        className="font-medium text-sm"
                      />
                    </td>

                    <td className="py-3 px-4 text-right">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectTransaction(tx);
                        }}
                        className="inline-flex items-center gap-1 text-xs text-muted hover:text-gold cursor-pointer"
                        title="View audit revision history"
                      >
                        <History className="w-3.5 h-3.5" />
                        <span className="text-[11px]">v{tx.version}</span>
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
