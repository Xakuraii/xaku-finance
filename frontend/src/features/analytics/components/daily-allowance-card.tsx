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
      <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 text-muted animate-pulse">
        <div className="h-6 w-48 bg-[var(--surface-raised)] rounded mb-4" />
        <div className="h-10 w-64 bg-[var(--surface-raised)] rounded mb-6" />
        <div className="h-16 bg-[var(--surface-raised)] rounded" />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="rounded-xl border border-[var(--negative-border)] bg-[var(--negative-bg)] p-6 text-[var(--negative)]">
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
    <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 shadow-sm">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[var(--border)] pb-4 mb-5">
        <div>
          <div className="flex items-center gap-2">
            <Calendar className="w-5 h-5 text-gold" />
            <h2 className="text-lg font-semibold text-main tracking-tight">Daily Allowance</h2>
          </div>
          <p className="text-xs text-muted mt-0.5">
            Pacing guideline: flexible budget remaining divided by remaining period days
          </p>
        </div>

        {/* State Badge */}
        {isOverBudget ? (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-[var(--negative-bg)] text-[var(--negative)] border border-[var(--negative-border)]">
            <AlertTriangle className="w-3.5 h-3.5" />
            Over Budget
          </span>
        ) : isPeriodEnded ? (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-[var(--surface-raised)] text-muted border border-[var(--border)]">
            <Clock className="w-3.5 h-3.5" />
            Period Ended
          </span>
        ) : (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-[var(--positive-bg)] text-[var(--positive)] border border-[var(--positive-border)]">
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
              isOverBudget ? "text-[var(--negative)]" : "text-main"
            }`}
          >
            {data.allowance}
          </span>
          <span className="text-sm font-semibold text-muted">
            {data.currency} / day
          </span>
        </div>
        <div className="flex items-center gap-1.5 mt-2 text-xs text-muted">
          <Clock className="w-3.5 h-3.5 text-gold" />
          <span>
            {data.remaining_days} days remaining in current period (until {data.period.end})
          </span>
        </div>
      </div>

      {/* Summary Metrics */}
      <div className="grid grid-cols-2 gap-3 mb-5">
        <div className="p-3 rounded-lg border border-[var(--border)] bg-[var(--surface-raised)]">
          <div className="text-[10px] font-semibold text-muted uppercase tracking-wider">
            Total Flexible Remaining
          </div>
          <div className="font-mono text-lg font-bold text-main mt-0.5">
            {data.flexible_remaining} <span className="text-xs font-normal text-muted">{data.currency}</span>
          </div>
          <div className="text-[10px] text-faint mt-0.5">
            {flexibleBudgets.length} flexible budget{flexibleBudgets.length === 1 ? "" : "s"}
          </div>
        </div>

        <div className="p-3 rounded-lg border border-[var(--border)] bg-[var(--surface-raised)]">
          <div className="text-[10px] font-semibold text-muted uppercase tracking-wider">
            Pacing Health
          </div>
          <div className="font-mono font-bold text-[var(--positive)] text-base mt-0.5">
            {isOverBudget ? "Action Needed" : "Disciplined"}
          </div>
          <div className="text-[10px] text-muted mt-0.5">
            {data.remaining_days} days to next cycle
          </div>
        </div>
      </div>

      {/* Budget Inclusion Drawer Toggle */}
      <button
        type="button"
        onClick={() => setShowBudgets((prev) => !prev)}
        className="w-full flex items-center justify-between px-4 py-2.5 rounded-lg border border-[var(--border)] bg-[var(--surface-raised)] hover:bg-[var(--surface-hover)] text-xs font-medium text-main transition-colors cursor-pointer"
        aria-expanded={showBudgets}
      >
        <span className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-gold" />
          Included Flexible Budgets ({flexibleBudgets.length})
        </span>
        {showBudgets ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
      </button>

      {/* Collapsible Budget Details */}
      {showBudgets && (
        <div className="mt-4 space-y-4 pt-2 border-t border-[var(--border)] text-xs">
          <div>
            <h4 className="font-semibold text-[var(--positive)] uppercase tracking-wider text-[11px] mb-2">
              Flexible Spending Budgets ({flexibleBudgets.length})
            </h4>
            {flexibleBudgets.length === 0 ? (
              <p className="text-muted italic">No flexible budgets active.</p>
            ) : (
              <div className="space-y-1.5">
                {flexibleBudgets.map((b) => (
                  <div
                    key={b.id}
                    className="flex items-center justify-between py-2 px-3 rounded bg-[var(--surface-raised)] border border-[var(--border)]"
                  >
                    <div>
                      <span className="font-medium text-main">{b.name}</span>
                    </div>
                    <div className="text-right">
                      <span className="font-mono text-[var(--positive)] font-medium">
                        {b.remaining} {data.currency} left
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {excludedBudgets.length > 0 && (
            <div>
              <h4 className="font-semibold text-muted uppercase tracking-wider text-[11px] mb-2">
                Excluded Fixed Budgets ({excludedBudgets.length})
              </h4>
              <div className="space-y-1">
                {excludedBudgets.map((b) => (
                  <div
                    key={b.id}
                    className="flex items-center justify-between py-1.5 px-3 rounded bg-[var(--surface-raised)]/60 border border-[var(--border)] text-muted"
                  >
                    <span>{b.name}</span>
                    <span className="capitalize text-[10px] text-faint">
                      {b.reason ? b.reason.replace("_", " ") : "Fixed"}
                    </span>
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
