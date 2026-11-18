import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Calendar,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Layers,
  ChevronDown,
  ChevronUp,
  ShieldAlert,
} from "lucide-react";
import { fetchDailyAllowance } from "../api/analytics-api";
import { DailyAllowanceResponse } from "../types";

interface DailyAllowanceCardProps {
  initialData?: DailyAllowanceResponse;
  currency?: string;
}

export const DailyAllowanceCard: React.FC<DailyAllowanceCardProps> = ({
  initialData,
  currency,
}) => {
  const [showBudgets, setShowBudgets] = useState(false);

  const { data, isLoading, isError } = useQuery<DailyAllowanceResponse>({
    queryKey: ["analytics", "daily-allowance", currency],
    queryFn: () => fetchDailyAllowance({ currency }),
    initialData,
  });

  if (isLoading && !data) {
    return (
      <div className="rounded-xl border border-[#2b313a] bg-[#181a20] p-6 text-slate-400 animate-pulse">
        <div className="h-6 w-48 bg-slate-800 rounded mb-4" />
        <div className="h-10 w-64 bg-slate-800 rounded mb-6" />
        <div className="h-16 bg-slate-800 rounded" />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="rounded-xl border border-rose-500/20 bg-rose-500/5 p-6 text-rose-400">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-5 h-5" />
          <span className="font-semibold text-sm">Failed to load daily allowance</span>
        </div>
      </div>
    );
  }

  const isOverBudget = data.state === "over_budget";
  const isPeriodEnded = data.state === "period_ended";
  const flexibleBudgets = data.budgets || [];
  const excludedBudgets = data.excluded || [];

  return (
    <div className="rounded-xl border border-[#2b313a] bg-[#181a20] p-6 shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[#2b313a] pb-4 mb-5">
        <div>
          <div className="flex items-center gap-2">
            <Calendar className="w-5 h-5 text-amber-400" />
            <h2 className="text-lg font-semibold text-white tracking-tight">Daily Allowance</h2>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Pacing guideline: flexible budget remaining divided by remaining period days
          </p>
        </div>

        {/* State Badge */}
        {isOverBudget ? (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <AlertTriangle className="w-3.5 h-3.5" />
            Over Budget
          </span>
        ) : isPeriodEnded ? (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700">
            <Clock className="w-3.5 h-3.5" />
            Period Ended
          </span>
        ) : (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3.5 h-3.5" />
            On Track
          </span>
        )}
      </div>

      {/* Main Headline */}
      <div className="mb-5">
        <div className="flex items-baseline gap-2">
          <span
            className={`font-mono text-3xl sm:text-4xl font-bold tracking-tight ${
              isOverBudget ? "text-rose-400" : "text-white"
            }`}
          >
            {data.allowance}
          </span>
          <span className="text-sm font-semibold text-slate-400">
            {data.currency} / day
          </span>
        </div>

        {/* Explanation text */}
        <p className="text-xs text-slate-300 mt-2 font-medium">
          {data.explanation}
        </p>
      </div>

      {/* Pacing Info Strip */}
      <div className="grid grid-cols-2 gap-3 mb-5 text-xs">
        <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
          <div className="text-slate-400 text-[11px]">Days Remaining</div>
          <div className="font-mono font-bold text-white text-base mt-0.5">
            {data.remaining_days} days
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5">
            through {data.period.end}
          </div>
        </div>

        <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
          <div className="text-slate-400 text-[11px]">Flexible Pool</div>
          <div className="font-mono font-bold text-emerald-400 text-base mt-0.5">
            {data.flexible_remaining} {data.currency}
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5">
            across {flexibleBudgets.length} flexible budget{flexibleBudgets.length === 1 ? "" : "s"}
          </div>
        </div>
      </div>

      {/* Budgets Toggle */}
      <button
        type="button"
        onClick={() => setShowBudgets((prev) => !prev)}
        className="w-full flex items-center justify-between px-4 py-2.5 rounded-lg border border-slate-700/60 bg-slate-800/40 hover:bg-slate-800/80 text-xs font-medium text-slate-300 transition-colors cursor-pointer"
        aria-expanded={showBudgets}
      >
        <span className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-amber-400" />
          View Contributing Budgets ({flexibleBudgets.length + excludedBudgets.length})
        </span>
        {showBudgets ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
      </button>

      {/* Collapsible Budgets Panel */}
      {showBudgets && (
        <div className="mt-4 space-y-4 pt-2 border-t border-slate-800 text-xs">
          {/* Flexible Budgets */}
          <div>
            <h4 className="font-semibold text-emerald-400 uppercase tracking-wider text-[11px] mb-2">
              Flexible Budgets (Counted in Allowance)
            </h4>
            {flexibleBudgets.length === 0 ? (
              <p className="text-xs text-slate-500 italic">No flexible budgets configured.</p>
            ) : (
              <div className="space-y-1">
                {flexibleBudgets.map((b) => (
                  <div
                    key={b.id}
                    className="flex items-center justify-between py-1.5 px-3 rounded bg-slate-900/40 border border-slate-800/80"
                  >
                    <span className="font-medium text-slate-200">{b.name}</span>
                    <span className="font-mono text-emerald-400">
                      {b.remaining} {data.currency} remaining
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Excluded Fixed Budgets */}
          {excludedBudgets.length > 0 && (
            <div>
              <h4 className="font-semibold text-slate-400 uppercase tracking-wider text-[11px] mb-2">
                Fixed & Reserved Budgets (Excluded)
              </h4>
              <div className="space-y-1">
                {excludedBudgets.map((b) => (
                  <div
                    key={b.id}
                    className="flex items-center justify-between py-1.5 px-3 rounded bg-slate-900/40 border border-slate-800/60 text-slate-500"
                  >
                    <span>{b.name}</span>
                    <span className="text-[10px] capitalize">Fixed budget</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
