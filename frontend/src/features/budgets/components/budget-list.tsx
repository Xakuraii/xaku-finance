import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Plus, PiggyBank, TrendingDown, DollarSign, Wallet } from "lucide-react";
import { fetchBudgetOverview, fetchBudgets } from "../api/budgets-api";
import { BudgetCard } from "./budget-card";
import { CreateBudgetDialog } from "./create-budget-dialog";
import { Budget, BudgetOverview } from "../types";

interface BudgetListProps {
  categories?: Array<{ id: string; name: string; kind: string }>;
  defaultCurrency?: string;
}

export const BudgetList: React.FC<BudgetListProps> = ({
  categories = [],
  defaultCurrency = "USD",
}) => {
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

  return (
    <div className="space-y-6">
      {/* Header and Action */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
            <PiggyBank className="w-6 h-6 text-[#F0B90B]" />
            Budget Management
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Track category spending allocations with positive-only rollover enforcement.
          </p>
        </div>

        <button
          type="button"
          onClick={() => setCreateDialogOpen(true)}
          className="flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-xl bg-[#F0B90B] text-black hover:bg-[#FCD535] shadow-lg shadow-[#F0B90B]/10 transition-all cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          New Budget
        </button>
      </div>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="rounded-xl border border-[#2b313a] bg-[#181a20] p-4 text-white">
          <div className="flex items-center gap-2 text-xs text-slate-400 mb-1">
            <Wallet className="w-4 h-4 text-[#F0B90B]" />
            Total Budgeted
          </div>
          <div className="text-2xl font-bold font-mono text-slate-100">
            {overview?.total_budgeted || "0.00"}{" "}
            <span className="text-xs font-sans text-slate-400">{currency}</span>
          </div>
        </div>

        <div className="rounded-xl border border-[#2b313a] bg-[#181a20] p-4 text-white">
          <div className="flex items-center gap-2 text-xs text-slate-400 mb-1">
            <TrendingDown className="w-4 h-4 text-orange-400" />
            Total Spent
          </div>
          <div className="text-2xl font-bold font-mono text-slate-100">
            {overview?.total_spent || "0.00"}{" "}
            <span className="text-xs font-sans text-slate-400">{currency}</span>
          </div>
        </div>

        <div className="rounded-xl border border-[#2b313a] bg-[#181a20] p-4 text-white">
          <div className="flex items-center gap-2 text-xs text-slate-400 mb-1">
            <DollarSign className="w-4 h-4 text-emerald-400" />
            Total Remaining
          </div>
          <div className="text-2xl font-bold font-mono text-slate-100">
            {overview?.total_remaining || "0.00"}{" "}
            <span className="text-xs font-sans text-slate-400">{currency}</span>
          </div>
        </div>
      </div>

      {/* Budgets Grid */}
      {budgetsLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[1, 2].map((i) => (
            <div
              key={i}
              className="h-40 rounded-xl border border-[#2b313a] bg-[#181a20] animate-pulse"
            />
          ))}
        </div>
      ) : budgets.length === 0 ? (
        <div className="py-12 text-center rounded-xl border border-dashed border-[#2b313a] bg-[#181a20]/40 text-slate-400">
          <PiggyBank className="w-10 h-10 mx-auto mb-3 text-slate-500 opacity-60" />
          <h3 className="font-semibold text-slate-200">No active budgets</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto mt-1 mb-4">
            Create your first budget to monitor spending against your monthly and weekly goals.
          </p>
          <button
            type="button"
            onClick={() => setCreateDialogOpen(true)}
            className="px-4 py-2 text-xs font-semibold rounded-lg bg-[#F0B90B] text-black hover:bg-[#FCD535] transition-all"
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
