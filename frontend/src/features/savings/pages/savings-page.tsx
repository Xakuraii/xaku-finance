import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Target, Plus, CheckCircle2 } from "lucide-react";
import { fetchSavingsGoals, SavingsGoal } from "../api/savings-api";
import { SavingsGoalCard } from "../components/savings-goal-card";
import { CreateGoalDialog } from "../components/create-goal-dialog";
import { ContributeDialog } from "../components/contribute-dialog";
import { GoalProjectionModal } from "../components/goal-projection-card";
import { getAccounts } from "@/features/accounts/api";
import { queryKeys } from "@/lib/query-keys";

export const SavingsPage: React.FC = () => {
  const [includeArchived, setIncludeArchived] = useState(false);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [selectedGoal, setSelectedGoal] = useState<SavingsGoal | null>(null);
  const [contributeOpen, setContributeOpen] = useState(false);
  const [projectionGoal, setProjectionGoal] = useState<SavingsGoal | null>(null);
  const [projectionOpen, setProjectionOpen] = useState(false);

  const { data: goals = [], isLoading } = useQuery({
    queryKey: ["savings-goals", includeArchived],
    queryFn: () => fetchSavingsGoals(includeArchived),
  });

  const { data: accounts = [] } = useQuery({
    queryKey: queryKeys.accounts.list(false),
    queryFn: () => getAccounts(false),
  });

  // Metrics
  const totalTargetMinor = goals.reduce((sum, g) => sum + g.target_amount_minor, 0);
  const totalCurrentMinor = goals.reduce((sum, g) => sum + g.current_amount_minor, 0);
  const activeCount = goals.filter((g) => g.status === "active").length;
  const achievedCount = goals.filter((g) => g.status === "achieved").length;

  const handleContribute = (goal: SavingsGoal) => {
    setSelectedGoal(goal);
    setContributeOpen(true);
  };

  const handleViewProjection = (goal: SavingsGoal) => {
    setProjectionGoal(goal);
    setProjectionOpen(true);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto p-4 md:p-6 animate-fade-in">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-main flex items-center gap-2">
            <Target className="w-6 h-6 text-gold" />
            Savings Goals
          </h1>
          <p className="text-sm text-muted">
            Track allocations, virtual earmarks, and target deadlines tied to real funds.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-xs text-muted cursor-pointer select-none">
            <input
              type="checkbox"
              checked={includeArchived}
              onChange={(e) => setIncludeArchived(e.target.checked)}
              className="rounded-sm border-[var(--border)] text-gold focus:ring-gold"
            />
            Show archived
          </label>
          <button
            onClick={() => setCreateDialogOpen(true)}
            data-testid="create-goal-btn"
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gold text-black font-semibold text-sm hover:brightness-110 shadow-sm cursor-pointer transition-all"
          >
            <Plus className="w-4 h-4" />
            New Goal
          </button>
        </div>
      </div>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl border border-[var(--border)] bg-[var(--surface)]">
          <div className="text-xs text-muted font-medium mb-1">Total Target</div>
          <div className="text-2xl font-bold text-main font-mono">
            ${(totalTargetMinor / 100).toLocaleString(undefined, { minimumFractionDigits: 2 })}
          </div>
        </div>
        <div className="p-4 rounded-xl border border-[var(--border)] bg-[var(--surface)]">
          <div className="text-xs text-muted font-medium mb-1">Total Saved</div>
          <div className="text-2xl font-bold text-gold font-mono">
            ${(totalCurrentMinor / 100).toLocaleString(undefined, { minimumFractionDigits: 2 })}
          </div>
        </div>
        <div className="p-4 rounded-xl border border-[var(--border)] bg-[var(--surface)]">
          <div className="text-xs text-muted font-medium mb-1">Active Goals</div>
          <div className="text-2xl font-bold text-main">{activeCount}</div>
        </div>
        <div className="p-4 rounded-xl border border-[var(--border)] bg-[var(--surface)]">
          <div className="text-xs text-muted font-medium mb-1">Achieved</div>
          <div className="text-2xl font-bold text-emerald-400 flex items-center gap-1.5">
            <CheckCircle2 className="w-5 h-5" />
            {achievedCount}
          </div>
        </div>
      </div>

      {/* Goals Grid */}
      {isLoading ? (
        <div className="py-12 text-center text-muted">Loading savings goals...</div>
      ) : goals.length === 0 ? (
        <div className="py-16 text-center border border-dashed border-[var(--border)] rounded-2xl p-8">
          <div className="p-3 w-fit mx-auto rounded-full bg-gold/10 text-gold mb-3">
            <Target className="w-8 h-8" />
          </div>
          <h3 className="font-semibold text-lg text-main mb-1">No savings goals yet</h3>
          <p className="text-sm text-muted max-w-sm mx-auto mb-4">
            Set up your first financial goal to earmark funds toward vacations, emergencies, or large purchases.
          </p>
          <button
            onClick={() => setCreateDialogOpen(true)}
            className="px-4 py-2 rounded-xl bg-gold text-black font-semibold text-sm hover:brightness-110 cursor-pointer"
          >
            Create Goal
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {goals.map((goal) => (
            <SavingsGoalCard
              key={goal.id}
              goal={goal}
              onContribute={handleContribute}
              onViewProjection={handleViewProjection}
            />
          ))}
        </div>
      )}

      {/* Dialogs */}
      <CreateGoalDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        accounts={accounts}
      />
      <ContributeDialog
        goal={selectedGoal}
        open={contributeOpen}
        onOpenChange={setContributeOpen}
        accounts={accounts}
      />
      <GoalProjectionModal
        goal={projectionGoal}
        open={projectionOpen}
        onOpenChange={setProjectionOpen}
      />
    </div>
  );
};
