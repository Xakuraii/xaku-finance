import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  TrendingUp,
  TrendingDown,
  Minus,
  Landmark,
  ShieldAlert,
  ChevronDown,
  ChevronUp,
  Calendar,
  Layers,
} from "lucide-react";
import { fetchNetWorth } from "../api/analytics-api";
import { NetWorthResponse } from "../types";

interface NetWorthCardProps {
  initialData?: NetWorthResponse;
  asOf?: string;
  currency?: string;
}

export const NetWorthCard: React.FC<NetWorthCardProps> = ({
  initialData,
  asOf,
  currency,
}) => {
  const [showBreakdown, setShowBreakdown] = useState(false);

  const { data, isLoading, isError } = useQuery<NetWorthResponse>({
    queryKey: ["analytics", "net-worth", asOf, currency],
    queryFn: () => fetchNetWorth({ as_of: asOf, currency }),
    initialData,
  });

  if (isLoading && !data) {
    return (
      <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 text-muted animate-pulse">
        <div className="h-6 w-48 bg-[var(--surface-raised)] rounded mb-4" />
        <div className="h-10 w-64 bg-[var(--surface-raised)] rounded mb-6" />
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="h-16 bg-[var(--surface-raised)] rounded" />
          <div className="h-16 bg-[var(--surface-raised)] rounded" />
        </div>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="rounded-xl border border-[var(--negative-border)] bg-[var(--negative-bg)] p-6 text-[var(--negative)]">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-5 h-5" />
          <span className="font-semibold text-sm">Failed to load net worth</span>
        </div>
      </div>
    );
  }

  const isNegative = data.net_worth.startsWith("-");
  const change = data.change;
  const assetItems = data.breakdown.assets || [];
  const liabilityItems = data.breakdown.liabilities || [];

  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 shadow-sm">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[var(--border)] pb-4 mb-5">
        <div>
          <div className="flex items-center gap-2">
            <Landmark className="w-5 h-5 text-gold" />
            <h2 className="text-lg font-semibold text-main tracking-tight">Net Worth</h2>
          </div>
          <p className="text-xs text-muted mt-0.5">
            Double-entry ledger balance as of {data.as_of}
          </p>
        </div>

        <div className="flex items-center gap-2">
          {data.conversion_unavailable && (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-[var(--warning-bg)] text-[var(--warning)] border border-[var(--warning-border)]">
              <ShieldAlert className="w-3.5 h-3.5" />
              FX Rate Missing
            </span>
          )}
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-[var(--surface-raised)] text-muted border border-[var(--border)]">
            <Calendar className="w-3.5 h-3.5 text-muted" />
            {data.as_of}
          </span>
        </div>
      </div>

      {/* Main Headline */}
      <div className="mb-6">
        <div className="flex flex-wrap items-baseline gap-3">
          <span
            className={`font-mono text-3xl sm:text-4xl font-bold tracking-tight ${
              isNegative ? "text-[var(--negative)]" : "text-main"
            }`}
          >
            {data.net_worth}
          </span>
          <span className="text-sm font-semibold text-muted">{data.currency}</span>
        </div>

        {/* Change indicator */}
        {change && (
          <div className="flex items-center gap-1.5 mt-2 text-xs">
            {change.direction === "up" && (
              <span className="flex items-center gap-1 text-[var(--positive)] font-medium">
                <TrendingUp className="w-3.5 h-3.5" />
                +{change.amount} {data.currency}
              </span>
            )}
            {change.direction === "down" && (
              <span className="flex items-center gap-1 text-[var(--negative)] font-medium">
                <TrendingDown className="w-3.5 h-3.5" />
                {change.amount} {data.currency}
              </span>
            )}
            {change.direction === "flat" && (
              <span className="flex items-center gap-1 text-muted font-medium">
                <Minus className="w-3.5 h-3.5" />
                0.00 {data.currency}
              </span>
            )}
            <span className="text-faint">since {change.since}</span>
          </div>
        )}
      </div>

      {/* Assets vs Liabilities Summary Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
        <div className="rounded-lg border border-[var(--positive-border)] bg-[var(--positive-bg)] p-4">
          <div className="text-xs font-medium text-[var(--positive)] uppercase tracking-wider mb-1">
            Total Assets
          </div>
          <div className="font-mono text-xl font-bold text-main">
            {data.assets} <span className="text-xs text-muted font-sans">{data.currency}</span>
          </div>
          <div className="text-[11px] text-muted mt-1">
            {assetItems.length} active asset account{assetItems.length === 1 ? "" : "s"}
          </div>
        </div>

        <div className="rounded-lg border border-[var(--negative-border)] bg-[var(--negative-bg)] p-4">
          <div className="text-xs font-medium text-[var(--negative)] uppercase tracking-wider mb-1">
            Total Liabilities
          </div>
          <div className="font-mono text-xl font-bold text-main">
            {data.liabilities}{" "}
            <span className="text-xs text-muted font-sans">{data.currency}</span>
          </div>
          <div className="text-[11px] text-muted mt-1">
            {liabilityItems.length} active obligation{liabilityItems.length === 1 ? "" : "s"}
          </div>
        </div>
      </div>

      {/* Breakdown Toggle */}
      <button
        type="button"
        onClick={() => setShowBreakdown((prev) => !prev)}
        className="w-full flex items-center justify-between px-4 py-2.5 rounded-lg border border-[var(--border)] bg-[var(--surface-raised)] hover:bg-[var(--surface-hover)] text-xs font-medium text-main transition-colors cursor-pointer"
        aria-expanded={showBreakdown}
      >
        <span className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-gold" />
          View Asset & Liability Breakdown ({assetItems.length + liabilityItems.length})
        </span>
        {showBreakdown ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
      </button>

      {/* Collapsible Breakdown Panel */}
      {showBreakdown && (
        <div className="mt-4 space-y-4 pt-2 border-t border-[var(--border)]">
          {/* Assets Section */}
          <div>
            <h3 className="text-xs font-semibold text-[var(--positive)] uppercase tracking-wider mb-2">
              Assets
            </h3>
            {assetItems.length === 0 ? (
              <p className="text-xs text-muted italic">No asset accounts recorded.</p>
            ) : (
              <div className="space-y-1.5">
                {assetItems.map((item, idx) => (
                  <div
                    key={`asset-${item.account_id || idx}`}
                    className="flex items-center justify-between py-2 px-3 rounded-lg bg-[var(--surface-raised)] border border-[var(--border)] text-xs"
                  >
                    <div>
                      <div className="font-medium text-main">{item.name}</div>
                      {item.currency !== data.currency && (
                        <div className="text-[10px] text-muted">
                          Native: {item.native_amount} {item.currency}
                        </div>
                      )}
                    </div>
                    <div className="font-mono font-medium text-[var(--positive)]">
                      {item.amount} {data.currency}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Liabilities Section */}
          <div>
            <h3 className="text-xs font-semibold text-[var(--negative)] uppercase tracking-wider mb-2">
              Liabilities
            </h3>
            {liabilityItems.length === 0 ? (
              <p className="text-xs text-muted italic">No liabilities recorded.</p>
            ) : (
              <div className="space-y-1.5">
                {liabilityItems.map((item, idx) => (
                  <div
                    key={`liab-${item.liability_id || item.account_id || idx}`}
                    className="flex items-center justify-between py-2 px-3 rounded-lg bg-[var(--surface-raised)] border border-[var(--border)] text-xs"
                  >
                    <div>
                      <div className="font-medium text-main">{item.name}</div>
                      {item.currency !== data.currency && (
                        <div className="text-[10px] text-muted">
                          Native: {item.native_amount} {item.currency}
                        </div>
                      )}
                    </div>
                    <div className="font-mono font-medium text-[var(--negative)]">
                      {item.outstanding || item.amount} {data.currency}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
