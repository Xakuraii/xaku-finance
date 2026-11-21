import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Archive, RotateCcw, ShieldCheck, Wallet, ArrowRightLeft, UploadCloud } from "lucide-react";
import { getAccounts, restoreAccount } from "../api";
import { Account } from "../types";
import { CreateAccountDialog } from "./create-account-dialog";
import { ArchiveAccountDialog } from "./archive-account-dialog";
import { TransferDialog } from "@/features/transfers/components/transfer-dialog";
import { ImportWizardDialog } from "@/features/imports/components/import-wizard-dialog";
import { MoneyDisplay } from "@/components/money";
import { formatAccountType } from "@/lib/format";
import { queryKeys } from "@/lib/query-keys";
import {
  convertMajorToUsdAndKhr,
  formatKhr,
  formatUsd,
  useCurrency,
} from "@/lib/currency-context";

export const StatementSheet: React.FC = () => {
  const queryClient = useQueryClient();
  const { usdToKhrRate } = useCurrency();
  const [includeArchived, setIncludeArchived] = useState(false);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isTransferOpen, setIsTransferOpen] = useState(false);
  const [isImportOpen, setIsImportOpen] = useState(false);
  const [accountToArchive, setAccountToArchive] = useState<Account | null>(null);

  const { data: accounts = [], isLoading } = useQuery({
    queryKey: queryKeys.accounts.list(includeArchived),
    queryFn: () => getAccounts(includeArchived),
  });

  const restoreMutation = useMutation({
    mutationFn: restoreAccount,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.accounts.all });
    },
  });

  // Calculate totals by currency and combined dual-currency portfolio
  const totalsByCurrency: Record<string, number> = {};
  let combinedUsd = 0;
  let combinedKhr = 0;

  accounts.forEach((acc) => {
    if (!acc.is_archived) {
      totalsByCurrency[acc.currency] = (totalsByCurrency[acc.currency] || 0) + acc.balance_minor;
      const converted = convertMajorToUsdAndKhr(acc.balance_minor / 100, acc.currency, usdToKhrRate);
      combinedUsd += converted.usd;
      combinedKhr += converted.khr;
    }
  });

  return (
    <div className="space-y-6">
      {/* Action header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-[var(--border)] pb-4">
        <div>
          <h1 className="font-display text-2xl font-semibold text-main tracking-tight">
            Accounts Register
          </h1>
          <p className="text-xs text-muted mt-1">
            Authoritative financial balances calculated directly from the double-entry ledger.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          <label className="flex items-center gap-2 text-xs text-muted cursor-pointer select-none">
            <input
              type="checkbox"
              checked={includeArchived}
              onChange={(e) => setIncludeArchived(e.target.checked)}
              className="rounded border-[var(--border)] bg-[var(--surface)] accent-[var(--accent)]"
            />
            Show Archived
          </label>

          <button
            onClick={() => setIsImportOpen(true)}
            className="flex items-center gap-1.5 rounded border border-[var(--border)] bg-[var(--surface)] hover:bg-[var(--surface-hover)] px-3 py-2 text-xs font-medium text-main cursor-pointer shadow-xs transition-colors"
            title="Import bank statement CSV"
          >
            <UploadCloud className="w-3.5 h-3.5 text-gold" />
            Import CSV
          </button>

          <button
            onClick={() => setIsTransferOpen(true)}
            className="flex items-center gap-2 rounded border border-[var(--border)] bg-[var(--surface)] hover:bg-[var(--surface-hover)] px-3.5 py-2 text-xs font-medium text-main cursor-pointer shadow-xs transition-colors"
          >
            <ArrowRightLeft className="w-4 h-4 text-gold" />
            Transfer
          </button>

          <button
            onClick={() => setIsCreateOpen(true)}
            className="flex items-center gap-2 rounded bg-gold px-3.5 py-2 text-xs font-medium cursor-pointer shadow-sm"
          >
            <Plus className="w-4 h-4" />
            New Account
          </button>
        </div>
      </div>

      {/* Dual-Currency & Combined Portfolio Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="rounded-xl bg-[var(--surface)] border border-[var(--border)] p-4 relative overflow-hidden">
          <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-[var(--accent)]" />
          <div className="flex items-center justify-between text-xs text-muted">
            <span>Combined Portfolio (USD)</span>
            <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-[var(--surface-raised)] border border-[var(--border)]">
              $ USD
            </span>
          </div>
          <div className="mt-1.5 font-mono text-2xl font-bold text-gold">
            {formatUsd(combinedUsd)}
          </div>
          <div className="text-[11px] text-faint mt-1 font-mono">
            All USD &amp; KHR accounts @ {usdToKhrRate.toLocaleString()} ៛/$
          </div>
        </div>

        <div className="rounded-xl bg-[var(--surface)] border border-[var(--border)] p-4 relative overflow-hidden">
          <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-[var(--positive)]" />
          <div className="flex items-center justify-between text-xs text-muted">
            <span>Combined Portfolio (Khmer Riel)</span>
            <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-[var(--surface-raised)] border border-[var(--border)]">
              ៛ KHR
            </span>
          </div>
          <div className="mt-1.5 font-mono text-2xl font-bold text-[var(--positive)]">
            {formatKhr(combinedKhr)}
          </div>
          <div className="text-[11px] text-faint mt-1 font-mono">
            Dual-currency equivalent balance
          </div>
        </div>

        <div className="rounded-xl bg-[var(--surface)] border border-[var(--border)] p-4">
          <div className="text-xs text-muted mb-2">Native Ledger Balances</div>
          {Object.entries(totalsByCurrency).length > 0 ? (
            <div className="space-y-1.5">
              {Object.entries(totalsByCurrency).map(([curr, amountMinor]) => (
                <div
                  key={curr}
                  className="flex items-center justify-between px-2.5 py-1.5 rounded-lg bg-[var(--surface-raised)] border border-[var(--border)] text-xs"
                >
                  <span className="font-mono font-semibold text-main">{curr}</span>
                  <MoneyDisplay
                    amountMinor={amountMinor}
                    currency={curr}
                    className="text-sm font-semibold text-main"
                  />
                </div>
              ))}
            </div>
          ) : (
            <div className="text-xs text-faint py-2">
              No active balances. Create an account to begin tracking.
            </div>
          )}
        </div>
      </div>

      {/* Statement Table */}
      <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] overflow-hidden shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm min-w-[620px]">
            <thead className="border-b border-[var(--border)] bg-[var(--surface-raised)] text-xs font-medium text-[var(--text-muted)]">
              <tr>
                <th className="py-3 px-4">Account Name</th>
                <th className="py-3 px-4">Type</th>
                <th className="py-3 px-4">Spendable</th>
                <th className="py-3 px-4 text-right">Ledger Balance</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)] font-normal">
              {isLoading ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-xs text-muted">
                    Loading accounts...
                  </td>
                </tr>
              ) : accounts.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-12 text-center text-muted">
                    <Wallet className="w-8 h-8 mx-auto text-faint mb-2" />
                    <p className="text-sm font-medium text-main">No accounts found</p>
                    <p className="text-xs text-faint mt-1">
                      Add a checking account, cash wallet, or savings goal to get started.
                    </p>
                  </td>
                </tr>
              ) : (
                accounts.map((acc) => (
                  <tr
                    key={acc.id}
                    className={`hover:bg-[var(--surface-raised)] transition-colors ${
                      acc.is_archived ? "opacity-60 bg-black/10" : ""
                    }`}
                  >
                    <td className="py-3 px-4">
                      <div className="font-medium text-main flex items-center gap-2">
                        {acc.name}
                        {acc.is_archived && (
                          <span className="text-[10px] rounded bg-[var(--surface-raised)] border border-[var(--border)] px-1.5 py-0.5 text-faint">
                            Archived
                          </span>
                        )}
                      </div>
                      {acc.description && (
                        <div className="text-xs text-muted truncate max-w-xs">{acc.description}</div>
                      )}
                    </td>
                    <td className="py-3 px-4 text-xs text-muted">
                      {formatAccountType(acc.account_type)}
                    </td>
                    <td className="py-3 px-4">
                      {acc.is_spendable ? (
                        <span className="inline-flex items-center gap-1 text-[11px] font-medium text-positive">
                          <ShieldCheck className="w-3.5 h-3.5" />
                          Spendable
                        </span>
                      ) : (
                        <span className="text-[11px] text-faint">Excluded</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <MoneyDisplay
                        amountMinor={acc.balance_minor}
                        currency={acc.currency}
                        className="font-medium text-sm"
                      />
                    </td>
                    <td className="py-3 px-4 text-right space-x-2">
                      {acc.is_archived ? (
                        <button
                          onClick={() => restoreMutation.mutate(acc.id)}
                          className="inline-flex items-center gap-1 text-xs text-gold hover:underline cursor-pointer"
                        >
                          <RotateCcw className="w-3.5 h-3.5" />
                          Restore
                        </button>
                      ) : (
                        <button
                          onClick={() => setAccountToArchive(acc)}
                          className="inline-flex items-center gap-1 text-xs text-muted hover:text-negative cursor-pointer"
                          title="Archive account"
                        >
                          <Archive className="w-3.5 h-3.5" />
                          Archive
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <CreateAccountDialog
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
      />

      <TransferDialog
        open={isTransferOpen}
        onOpenChange={setIsTransferOpen}
        accounts={accounts}
      />

      <ImportWizardDialog
        open={isImportOpen}
        onOpenChange={setIsImportOpen}
        accounts={accounts}
      />

      <ArchiveAccountDialog
        account={accountToArchive}
        isOpen={!!accountToArchive}
        onClose={() => setAccountToArchive(null)}
      />
    </div>
  );
};
