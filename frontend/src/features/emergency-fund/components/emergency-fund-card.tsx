import React from "react";
import { Shield, Settings, AlertTriangle, CheckCircle, Info } from "lucide-react";
import { EmergencyFundStatus } from "../api/emergency-fund-api";
import { formatDualAmount, useCurrency } from "@/lib/currency-context";

interface EmergencyFundCardProps {
  status: EmergencyFundStatus;
  onConfigure: () => void;
}

export const EmergencyFundCard: React.FC<EmergencyFundCardProps> = ({
  status,
  onConfigure,
}) => {
  const { mode, usdToKhrRate, isProviderMounted } = useCurrency();
  const isFullyFunded = status.progress_percent >= 100;
  const baseCurr = (status as { currency?: string }).currency || "USD";
  const currentDual = formatDualAmount(status.current_savings, baseCurr, mode, usdToKhrRate);
  const targetDual = formatDualAmount(status.target_amount, baseCurr, mode, usdToKhrRate);
  const remainingDual = formatDualAmount(status.remaining_target, baseCurr, mode, usdToKhrRate);
  const monthlyDual = formatDualAmount(status.monthly_essential_expense, baseCurr, mode, usdToKhrRate);
  const computedDual = formatDualAmount(status.computed_monthly_expense, baseCurr, mode, usdToKhrRate);

  return (
    <div
      data-testid="emergency-fund-card"
      className="bg-[var(--surface)] border border-[var(--border)] rounded-xl p-6 shadow-sm space-y-6"
    >
      {/* Top Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-[var(--accent)]/10 border border-[var(--accent)]/20 flex items-center justify-center">
            <Shield className="w-5 h-5 text-[var(--accent)]" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-main">
              Emergency Fund Safety Net
            </h2>
            <p className="text-xs text-[var(--text-muted)]">
              {status.target_months} months essential expense coverage target
            </p>
          </div>
        </div>
        <button
          onClick={onConfigure}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-muted hover:text-main bg-[var(--surface-raised)] hover:bg-[var(--surface-hover)] border border-[var(--border)] rounded-lg transition-colors"
        >
          <Settings className="w-3.5 h-3.5" />
          <span>Configure</span>
        </button>
      </div>

      {/* Conflict Warning Banner (FR-EMG-06) */}
      {status.has_earmark_conflict && (
        <div
          data-testid="conflict-alert"
          className="p-3.5 bg-[var(--warning-bg)] border border-[var(--warning-border)] rounded-lg flex items-start gap-2.5 text-sm text-[var(--warning)]"
        >
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="font-semibold text-xs uppercase tracking-wider">
              Earmark Allocation Conflict Detected
            </p>
            <p className="text-xs leading-relaxed text-[var(--warning)]">
              {status.conflict_details}
            </p>
          </div>
        </div>
      )}

      {/* Progress & Target Section */}
      <div className="space-y-2">
        <div className="flex items-baseline justify-between gap-2">
          <div>
            <div className="flex items-baseline gap-2 flex-wrap">
              <span className="text-2xl font-bold font-mono text-main">
                {isProviderMounted ? currentDual.primary : `$${status.current_savings}`}
              </span>
              <span className="text-sm text-[var(--text-muted)]">
                of {isProviderMounted ? targetDual.primary : `$${status.target_amount}`} target
              </span>
            </div>
            {isProviderMounted && currentDual.secondary && (
              <div className="text-[11px] font-mono text-[var(--text-muted)] mt-0.5">
                {currentDual.secondary} / {targetDual.secondary}
              </div>
            )}
          </div>
          <div className="flex items-center gap-1 text-sm font-semibold">
            {isFullyFunded ? (
              <span className="text-[var(--positive)] flex items-center gap-1">
                <CheckCircle className="w-4 h-4" /> Fully Funded
              </span>
            ) : (
              <span className="text-muted">
                {status.progress_percent.toFixed(1)}%
              </span>
            )}
          </div>
        </div>

        {/* Progress Bar */}
        <div
          data-testid="progress-bar"
          className="w-full bg-[var(--surface-raised)] rounded-full h-3 overflow-hidden border border-[var(--border)]/50"
        >
          <div
            className={`h-full transition-all duration-500 animate-xaku-bar ${
              isFullyFunded ? "bg-[var(--positive)]" : "bg-[var(--accent)]"
            }`}
            style={{ width: `${Math.min(100, Math.max(0, status.progress_percent))}%` }}
          />
        </div>

        <div className="flex justify-between items-center text-xs text-[var(--text-muted)] pt-1">
          <span>
            Remaining needed:{" "}
            {isProviderMounted ? remainingDual.primary : `$${status.remaining_target}`}
          </span>
          <span>Coverage: {status.target_months} months</span>
        </div>
      </div>

      {/* Metrics Breakdown Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2 border-t border-[var(--border)]/60">
        <div className="p-3 bg-[var(--surface-raised)]/50 border border-[var(--border)]/40 rounded-lg">
          <div className="text-xs text-[var(--text-muted)] mb-1">Monthly Essential Spend</div>
          <div className="text-base font-semibold font-mono text-main">
            {isProviderMounted ? monthlyDual.primary : `$${status.monthly_essential_expense}`}
            <span className="text-xs font-normal font-sans text-[var(--text-muted)]"> / mo</span>
          </div>
          {isProviderMounted && monthlyDual.secondary && (
            <div className="text-[11px] font-mono text-[var(--text-muted)] mt-0.5">
              {monthlyDual.secondary} / mo
            </div>
          )}
          <div className="mt-1.5 flex items-center gap-1">
            <span
              data-testid="expense-source-badge"
              className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full ${
                status.is_override
                  ? "bg-amber-500/10 text-amber-500 border border-amber-500/20"
                  : "bg-blue-500/10 text-blue-500 border border-blue-500/20"
              }`}
            >
              {status.is_override ? "Manual Override" : "90-Day Lookback"}
            </span>
          </div>
        </div>

        <div className="p-3 bg-[var(--surface-raised)]/50 border border-[var(--border)]/40 rounded-lg">
          <div className="text-xs text-[var(--text-muted)] mb-1">Backing Account / Goal</div>
          <div className="text-base font-semibold text-main truncate">
            {status.designated_account_name ||
              status.designated_goal_name ||
              "Unassigned"}
          </div>
          <div className="mt-1.5 text-[10px] text-[var(--text-muted)]">
            {status.designated_account_id
              ? "Designated Bank Account"
              : status.designated_goal_id
              ? "Dedicated Savings Goal"
              : "No specific account mapped"}
          </div>
        </div>

        <div className="p-3 bg-[var(--surface-raised)]/50 border border-[var(--border)]/40 rounded-lg">
          <div className="text-xs text-[var(--text-muted)] mb-1">Historical Analytics</div>
          <div className="text-base font-semibold font-mono text-main">
            {isProviderMounted ? computedDual.primary : `$${status.computed_monthly_expense}`}
            <span className="text-xs font-normal font-sans text-[var(--text-muted)]"> / mo</span>
          </div>
          {isProviderMounted && computedDual.secondary && (
            <div className="text-[11px] font-mono text-[var(--text-muted)] mt-0.5">
              {computedDual.secondary} / mo
            </div>
          )}
          <div className="mt-1.5 flex items-center gap-1 text-[10px] text-[var(--text-muted)]">
            <Info className="w-3 h-3" />
            <span>Essential category filter ({status.lookback_days} days)</span>
          </div>
        </div>
      </div>
    </div>
  );
};
