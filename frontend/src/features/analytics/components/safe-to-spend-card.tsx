import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Sparkles,
  Info,
  ChevronDown,
  ChevronUp,
  Clock,
  ShieldAlert,
} from "lucide-react";
import { fetchSafeToSpend } from "../api/analytics-api";
import { SafeToSpendResponse } from "../types";

interface SafeToSpendCardProps {
  initialData?: SafeToSpendResponse;
  currency?: string;
}

export const SafeToSpendCard: React.FC<SafeToSpendCardProps> = ({
  initialData,
  currency,
}) => {
  const [horizonDays, setHorizonDays] = useState<number | undefined>(undefined);
  const [showDetails, setShowDetails] = useState(false);

  const { data, isLoading, isError } = useQuery<SafeToSpendResponse>({
    queryKey: ["analytics", "safe-to-spend", horizonDays, currency],
    queryFn: () =>
      fetchSafeToSpend({
        horizon: horizonDays ? undefined : "period_end",
        horizon_days: horizonDays,
        currency,
      }),
    initialData,
  });

  if (isLoading && !data) {
    return (
      <div className="rounded-xl border border-[#2b313a] bg-[#181a20] p-6 text-slate-400 animate-pulse">
        <div className="h-6 w-48 bg-slate-800 rounded mb-4" />
        <div className="h-10 w-64 bg-slate-800 rounded mb-6" />
        <div className="grid grid-cols-4 gap-2">
          <div className="h-12 bg-slate-800 rounded" />
          <div className="h-12 bg-slate-800 rounded" />
          <div className="h-12 bg-slate-800 rounded" />
          <div className="h-12 bg-slate-800 rounded" />
        </div>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="rounded-xl border border-rose-500/20 bg-rose-500/5 p-6 text-rose-400">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-5 h-5" />
          <span className="font-semibold text-sm">Failed to load Safe-to-Spend</span>
        </div>
      </div>
    );
  }

  const comp = data.components;
  const accounts = data.accounts || [];
  const excluded = data.excluded_accounts || [];

  return (
    <div className="rounded-xl border border-[#2b313a] bg-[#181a20] p-6 shadow-sm">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#2b313a] pb-4 mb-5">
        <div>
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-amber-400" />
            <h2 className="text-lg font-semibold text-white tracking-tight">Safe-to-Spend</h2>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Liquid cash available after upcoming bills, savings earmarks, and pending outflows
          </p>
        </div>

        {/* Horizon Filter */}
        <div className="flex items-center gap-1 rounded-lg border border-[#2b313a] bg-slate-900/60 p-0.5 text-xs">
          <button
            type="button"
            onClick={() => setHorizonDays(undefined)}
            className={`px-2.5 py-1 rounded font-medium transition-colors cursor-pointer ${
              horizonDays === undefined
                ? "bg-amber-400 text-black font-semibold"
                : "text-slate-400 hover:text-white"
            }`}
          >
            End of Month
          </button>
          <button
            type="button"
            onClick={() => setHorizonDays(14)}
            className={`px-2.5 py-1 rounded font-medium transition-colors cursor-pointer ${
              horizonDays === 14
                ? "bg-amber-400 text-black font-semibold"
                : "text-slate-400 hover:text-white"
            }`}
          >
            14 Days
          </button>
          <button
            type="button"
            onClick={() => setHorizonDays(7)}
            className={`px-2.5 py-1 rounded font-medium transition-colors cursor-pointer ${
              horizonDays === 7
                ? "bg-amber-400 text-black font-semibold"
                : "text-slate-400 hover:text-white"
            }`}
          >
            7 Days
          </button>
        </div>
      </div>

      {/* Main Headline */}
      <div className="mb-6">
        <div className="flex items-baseline gap-3">
          <span className="font-mono text-3xl sm:text-4xl font-bold tracking-tight text-white">
            {data.display}
          </span>
          <span className="text-sm font-semibold text-slate-400">{data.currency}</span>
          {data.is_negative && (
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20">
              Raw: {data.raw} {data.currency} (Overcommitted)
            </span>
          )}
        </div>
        <div className="flex items-center gap-1.5 mt-2 text-xs text-slate-400">
          <Clock className="w-3.5 h-3.5 text-amber-400" />
          <span>Calculated for horizon: {data.horizon.label} ({data.horizon.start} to {data.horizon.end})</span>
        </div>
      </div>

      {/* Equation Breakdown Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-6">
        <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3">
          <div className="text-[10px] font-semibold text-emerald-400 uppercase tracking-wider">
            Spendable Cash
          </div>
          <div className="font-mono text-base font-bold text-white mt-1">
            {comp.spendable_balance}
          </div>
          <div className="text-[10px] text-slate-400 mt-0.5">{accounts.length} accounts</div>
        </div>

        <div className="rounded-lg border border-slate-700/60 bg-slate-800/40 p-3">
          <div className="text-[10px] font-semibold text-slate-300 uppercase tracking-wider">
            Pending Outflows
          </div>
          <div className="font-mono text-base font-bold text-slate-300 mt-1">
            {comp.pending_outflows}
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5">Not yet posted</div>
        </div>

        <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3">
          <div className="text-[10px] font-semibold text-amber-400 uppercase tracking-wider">
            Reserved Bills
          </div>
          <div className="font-mono text-base font-bold text-amber-300 mt-1">
            {comp.reserved_bills}
          </div>
          <div className="text-[10px] text-slate-400 mt-0.5">Due in horizon</div>
        </div>

        <div className="rounded-lg border border-purple-500/20 bg-purple-500/5 p-3">
          <div className="text-[10px] font-semibold text-purple-400 uppercase tracking-wider">
            Planned Savings
          </div>
          <div className="font-mono text-base font-bold text-purple-300 mt-1">
            {comp.planned_savings}
          </div>
          <div className="text-[10px] text-slate-400 mt-0.5">Earmarks & goals</div>
        </div>
      </div>

      {/* How this is calculated toggle */}
      <button
        type="button"
        onClick={() => setShowDetails((prev) => !prev)}
        className="w-full flex items-center justify-between px-4 py-2.5 rounded-lg border border-slate-700/60 bg-slate-800/40 hover:bg-slate-800/80 text-xs font-medium text-slate-300 transition-colors cursor-pointer"
        aria-expanded={showDetails}
      >
        <span className="flex items-center gap-2">
          <Info className="w-4 h-4 text-amber-400" />
          How this is calculated & Account inclusion
        </span>
        {showDetails ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
      </button>

      {/* Collapsible Details Drawer */}
      {showDetails && (
        <div className="mt-4 space-y-4 pt-3 border-t border-slate-800 text-xs">
          {/* Notes */}
          {data.notes && data.notes.length > 0 && (
            <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 text-slate-400 italic">
              {data.notes.map((n, i) => (
                <div key={i}>• {n}</div>
              ))}
            </div>
          )}

          {/* Included Spendable Accounts */}
          <div>
            <h4 className="font-semibold text-emerald-400 uppercase tracking-wider text-[11px] mb-2">
              Included Accounts ({accounts.length})
            </h4>
            <div className="space-y-1">
              {accounts.map((acc) => (
                <div
                  key={acc.id}
                  className="flex items-center justify-between py-1.5 px-3 rounded bg-slate-900/40 border border-slate-800/80"
                >
                  <span className="font-medium text-slate-200">{acc.name}</span>
                  <span className="font-mono text-emerald-400">
                    {acc.balance} {data.currency}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Excluded Accounts */}
          {excluded.length > 0 && (
            <div>
              <h4 className="font-semibold text-slate-400 uppercase tracking-wider text-[11px] mb-2">
                Excluded Accounts ({excluded.length})
              </h4>
              <div className="space-y-1">
                {excluded.map((acc) => (
                  <div
                    key={acc.id}
                    className="flex items-center justify-between py-1.5 px-3 rounded bg-slate-900/40 border border-slate-800/60 text-slate-500"
                  >
                    <span>{acc.name}</span>
                    <span className="capitalize text-[10px]">{acc.reason.replace("_", " ")}</span>
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
