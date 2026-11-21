import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Plus, PiggyBank, TrendingDown, DollarSign, Wallet } from "lucide-react";
import { fetchBudgetOverview, fetchBudgets } from "../api/budgets-api";
import { BudgetCard } from "./budget-card";
import { CreateBudgetDialog } from "./create-budget-dialog";
import { Budget, BudgetOverview } from "../types";
import {
  convertMajorToUsdAndKhr,
  formatDualAmount,
  resolveModeReadout,
  useCurrency,
} from "@/lib/currency-context";

interface BudgetListProps {
  categories?: Array<{ id: string; name: string; kind: string }>;
  defaultCurrency?: string;
}

export const BudgetList: React.FC<BudgetListProps> = ({
  categories = [],
  defaultCurrency = "USD",
}) => {
  const { mode, usdToKhrRate, isProviderMounted } = useCurrency();
  const [createDialogOpen, setCreateDialogOpen] = useState(false);

  const { data: budgets = [], isLoading: budgetsLoading } = useQuery<Budget[]>({
    queryKey: ["budgets"],
    queryFn: fetchBudgets,
  });

  const { data: overview } = useQuery<BudgetOverview>({
    queryKey: ["budgets", "overview"],
    queryFn: () => fetchBudgetOverview(defaultCurrency),
  });

  const currency = overview?.currency || defaultCurrency;

  const budgetDualTotals = (() => {
    const activeBudgets = budgets.filter((b) => !b.is_archived);
    if (activeBudgets.length > 0) {
      let budgetedUsd = 0;
      let budgetedKhr = 0;
      let spentUsd = 0;
      let spentKhr = 0;
      let remainingUsd = 0;
      let remainingKhr = 0;

      for (const b of activeBudgets) {
        const availMinor = b.current_period?.total_available_minor ?? b.base_amount_minor;
        const spentMinor = b.current_period?.spent_minor ?? 0;
        const remMinor = b.current_period?.remaining_minor ?? availMinor - spentMinor;

        const aConv = convertMajorToUsdAndKhr(availMinor / 100, b.currency, usdToKhrRate);
        const sConv = convertMajorToUsdAndKhr(spentMinor / 100, b.currency, usdToKhrRate);
        const rConv = convertMajorToUsdAndKhr(remMinor / 100, b.currency, usdToKhrRate);

        budgetedUsd += aConv.usd;
        budgetedKhr += aConv.khr;
        spentUsd += sConv.usd;
        spentKhr += sConv.khr;
        remainingUsd += rConv.usd;
        remainingKhr += rConv.khr;
      }

      return {
        budgeted: resolveModeReadout(budgetedUsd, budgetedKhr, mode),
        spent: resolveModeReadout(spentUsd, spentKhr, mode),
        remaining: resolveModeReadout(remainingUsd, remainingKhr, mode),
      };
    }

    return {
      budgeted: formatDualAmount(overview?.total_budgeted || "0.00", currency, mode, usdToKhrRate),
      spent: formatDualAmount(overview?.total_spent || "0.00", currency, mode, usdToKhrRate),
      remaining: formatDualAmount(overview?.total_remaining || "0.00", currency, mode, usdToKhrRate),
    };
  })();

  return (
    <div className="space-y-6">
      {/* Header and Action */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-[var(--border)] pb-4">
        <div>
          <h2 className="text-2xl font-bold text-main font-display flex items-center gap-2">
            <PiggyBank className="w-6 h-6 text-gold" />
            Budget Management
          </h2>
          <p className="text-xs text-muted mt-1">
            Track category spending allocations with positive-only rollover enforcement.
          </p>
        </div>

        <button
          type="button"
          onClick={() => setCreateDialogOpen(true)}
          className="flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-lg bg-gold hover:opacity-90 transition-all cursor-pointer shadow-xs"
        >
          <Plus className="w-4 h-4" />
          New Budget
        </button>
      </div>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 text-main shadow-xs">
          <div className="flex items-center gap-2 text-xs text-muted mb-1">
            <Wallet className="w-4 h-4 text-gold" />
            Total Budgeted
          </div>
          <div className="text-2xl font-bold font-tabular text-main">
            {isProviderMounted ? (
              budgetDualTotals.budgeted.primary
            ) : (
              <>
                {overview?.total_budgeted || "0.00"}{" "}
                <span className="text-xs font-sans text-muted">{currency}</span>
              </>
            )}
          </div>
          {isProviderMounted && budgetDualTotals.budgeted.secondary && (
            <div className="text-[11px] font-mono text-muted mt-0.5">
              {budgetDualTotals.budgeted.secondary}
            </div>
          )}
        </div>

        <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 text-main shadow-xs">
          <div className="flex items-center gap-2 text-xs text-muted mb-1">
            <TrendingDown className="w-4 h-4 text-negative" />
            Total Spent
          </div>
          <div className="text-2xl font-bold font-tabular text-main">
            {isProviderMounted ? (
              budgetDualTotals.spent.primary
            ) : (
              <>
                {overview?.total_spent || "0.00"}{" "}
                <span className="text-xs font-sans text-muted">{currency}</span>
              </>
            )}
          </div>
          {isProviderMounted && budgetDualTotals.spent.secondary && (
            <div className="text-[11px] font-mono text-muted mt-0.5">
              {budgetDualTotals.spent.secondary}
            </div>
          )}
        </div>

        <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 text-main shadow-xs">
          <div className="flex items-center gap-2 text-xs text-muted mb-1">
            <DollarSign className="w-4 h-4 text-positive" />
            Total Remaining
          </div>
          <div className="text-2xl font-bold font-tabular text-main">
            {isProviderMounted ? (
              budgetDualTotals.remaining.primary
            ) : (
              <>
                {overview?.total_remaining || "0.00"}{" "}
                <span className="text-xs font-sans text-muted">{currency}</span>
              </>
            )}
          </div>
          {isProviderMounted && budgetDualTotals.remaining.secondary && (
            <div className="text-[11px] font-mono text-muted mt-0.5">
              {budgetDualTotals.remaining.secondary}
            </div>
          )}
        </div>
      </div>

      {/* Budgets Grid */}
      {budgetsLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[1, 2].map((i) => (
            <div
              key={i}
              className="h-40 rounded-xl border border-[var(--border)] bg-[var(--surface)] animate-pulse"
            />
          ))}
        </div>
      ) : budgets.length === 0 ? (
        <div className="py-12 text-center rounded-xl border border-dashed border-[var(--border)] bg-[var(--surface-raised)] text-muted">
          <PiggyBank className="w-10 h-10 mx-auto mb-3 opacity-60 text-gold" />
          <h3 className="font-semibold text-main">No active budgets</h3>
          <p className="text-xs text-muted max-w-sm mx-auto mt-1 mb-4">
            Create your first budget to monitor spending against your monthly and weekly goals.
          </p>
          <button
            type="button"
            onClick={() => setCreateDialogOpen(true)}
            className="px-4 py-2 text-xs font-semibold rounded-lg bg-gold hover:opacity-90 transition-all cursor-pointer"
          >
            Create Budget
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {budgets.map((b) => (
            <BudgetCard key={b.id} budget={b} />
          ))}
        </div>
      )}

      {/* Create Modal */}
      <CreateBudgetDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        categories={categories}
        defaultCurrency={defaultCurrency}
      />
    </div>
  );
};
