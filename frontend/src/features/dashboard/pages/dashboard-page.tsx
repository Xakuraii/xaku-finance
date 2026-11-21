import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  SlidersHorizontal,
  Wallet,
  TrendingUp,
  ShieldCheck,
  Calendar,
  PieChart,
  Target,
  Clock,
  ArrowUpRight,
  ArrowDownRight,
  TrendingDown,
  Plus,
} from "lucide-react";
import {
  fetchDashboard,
  fetchDashboardLayout,
  saveDashboardLayout,
  resetDashboardLayout,
  DashboardResponse,
  WidgetLayoutItem,
} from "../api/dashboard-api";
import { DashboardLayoutDialog } from "../components/dashboard-layout-dialog";
import { CreateTransactionDrawer } from "@/features/transactions/components/create-transaction-drawer";
import {
  convertMajorToUsdAndKhr,
  formatDualAmount,
  resolveModeReadout,
  useCurrency,
} from "@/lib/currency-context";

type PeriodOption = undefined | "current_month" | "last_30_days" | "last_90_days" | "ytd";

const PERIOD_PILLS: Array<{ label: string; value: PeriodOption }> = [
  { label: "Current", value: undefined },
  { label: "Month", value: "current_month" },
  { label: "30D", value: "last_30_days" },
  { label: "90D", value: "last_90_days" },
  { label: "YTD", value: "ytd" },
];

const SPENDING_PALETTE = [
  "#F0B90B",
  "#38BDF8",
  "#10B981",
  "#A78BFA",
  "#FB923C",
];

function parseNumericAmount(val: string | undefined): number {
  if (!val) return 0;
  const cleaned = val.replace(/,/g, "");
  const parsed = parseFloat(cleaned);
  return Number.isFinite(parsed) ? parsed : 0;
}

// Reusable styled widget card
const WidgetCard: React.FC<{
  children: React.ReactNode;
  className?: string;
  accentColor?: string;
}> = ({ children, className = "", accentColor }) => (
  <div
    className={`rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5 shadow-xs transition-all hover:border-[var(--border-strong)] relative overflow-hidden ${className}`}
  >
    {accentColor && (
      <div
        className="absolute left-0 top-0 bottom-0 w-0.5 rounded-l-xl"
        style={{ background: accentColor }}
      />
    )}
    {children}
  </div>
);

const WidgetLabel: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <p className="text-xs font-medium text-[var(--text-muted)]">{children}</p>
);

const WidgetValue: React.FC<{
  children: React.ReactNode;
  color?: string;
  className?: string;
}> = ({ children, color, className = "" }) => (
  <div
    className={`text-2xl font-bold font-tabular tracking-tight mt-1 ${className}`}
    style={color ? { color } : undefined}
  >
    {children}
  </div>
);

export const DashboardPage: React.FC = () => {
  const queryClient = useQueryClient();
  const { mode, usdToKhrRate, isProviderMounted } = useCurrency();
  const [layoutOpen, setLayoutOpen] = useState(false);
  const [createTxOpen, setCreateTxOpen] = useState(false);
  const [selectedPeriod, setSelectedPeriod] = useState<PeriodOption>(undefined);

  const getDualSummary = (amountStr: string | undefined, sourceCurr: string | undefined) => {
    const src = (sourceCurr || dashboard?.currency || "USD").toUpperCase();
    return formatDualAmount(amountStr || "0.00", src, mode, usdToKhrRate);
  };

  const renderSecondaryReadout = (secondaryText: string | null) => {
    if (!isProviderMounted || !secondaryText) return null;
    return (
      <div className="text-[11px] font-mono text-[var(--text-muted)] mt-0.5">
        {secondaryText}
      </div>
    );
  };

  const { data: dashboard, isLoading, error } = useQuery<DashboardResponse>({
    queryKey: selectedPeriod ? ["dashboard-data", selectedPeriod] : ["dashboard-data"],
    queryFn: () =>
      selectedPeriod ? fetchDashboard({ period: selectedPeriod }) : fetchDashboard(),
  });

  const { data: layoutData } = useQuery<{ widgets: WidgetLayoutItem[] }>({
    queryKey: ["dashboard-layout"],
    queryFn: () => fetchDashboardLayout(),
  });

  const saveMutation = useMutation({
    mutationFn: saveDashboardLayout,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dashboard-layout"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-data"] });
    },
  });

  const resetMutation = useMutation({
    mutationFn: resetDashboardLayout,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dashboard-layout"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-data"] });
    },
  });

  if (isLoading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-8 w-48 bg-[var(--surface-raised)] rounded-lg" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-32 bg-[var(--surface-raised)] rounded-xl" />
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="h-64 bg-[var(--surface-raised)] rounded-xl lg:col-span-2" />
          <div className="h-64 bg-[var(--surface-raised)] rounded-xl" />
        </div>
      </div>
    );
  }

  if (error || !dashboard) {
    return (
      <div className="p-4 bg-[var(--negative-bg)] border border-[var(--negative-border)] rounded-xl text-[var(--negative)] text-sm">
        Failed to load dashboard data. Please try refreshing the page.
      </div>
    );
  }

  const { widget_order } = dashboard;

  const renderWidget = (key: string) => {
    switch (key) {
      case "total_balance": {
        const balanceDual = (() => {
          if (dashboard.balances && dashboard.balances.length > 0) {
            const totals = dashboard.balances.reduce(
              (acc, b) => {
                const conv = convertMajorToUsdAndKhr(
                  parseNumericAmount(b.total),
                  b.currency,
                  usdToKhrRate
                );
                return { usd: acc.usd + conv.usd, khr: acc.khr + conv.khr };
              },
              { usd: 0, khr: 0 }
            );
            return resolveModeReadout(totals.usd, totals.khr, mode);
          }
          return getDualSummary(
            dashboard.converted_total?.amount,
            dashboard.converted_total?.currency || dashboard.currency
          );
        })();

        return (
          <WidgetCard key="total_balance" accentColor="var(--accent)">
            <div className="flex items-center justify-between mb-3">
              <WidgetLabel>Account Balances</WidgetLabel>
              <div className="w-7 h-7 rounded-lg bg-[var(--accent)]/12 flex items-center justify-center">
                <Wallet className="w-3.5 h-3.5 text-gold" />
              </div>
            </div>
            <WidgetValue>
              {isProviderMounted ? (
                balanceDual.primary
              ) : (
                <>
                  {dashboard.converted_total?.amount || "0.00"}
                  <span className="text-sm font-normal text-[var(--text-muted)] ml-1.5">
                    {dashboard.converted_total?.currency || dashboard.currency}
                  </span>
                </>
              )}
            </WidgetValue>
            {renderSecondaryReadout(balanceDual.secondary)}
            <p className="text-[11px] text-[var(--text-faint)] mt-1">Consolidated available</p>
            {dashboard.balances && dashboard.balances.length > 0 && (
              <div className="pt-3 mt-2 border-t border-[var(--border)] flex flex-wrap gap-1.5">
                {dashboard.balances.map((b) => (
                  <span
                    key={b.currency}
                    className="bg-[var(--surface-raised)] border border-[var(--border)] px-2 py-0.5 rounded-md font-mono text-[11px] text-[var(--text-muted)]"
                  >
                    {b.total} {b.currency}
                  </span>
                ))}
              </div>
            )}
          </WidgetCard>
        );
      }

      case "net_worth": {
        const netWorthDual = getDualSummary(
          dashboard.net_worth?.amount,
          dashboard.net_worth?.currency || dashboard.currency
        );
        return (
          <WidgetCard key="net_worth" accentColor="var(--positive)">
            <div className="flex items-center justify-between mb-3">
              <WidgetLabel>Net Worth</WidgetLabel>
              <div className="w-7 h-7 rounded-lg bg-[var(--positive-bg)] flex items-center justify-center">
                <TrendingUp className="w-3.5 h-3.5 text-[var(--positive)]" />
              </div>
            </div>
            <WidgetValue color="var(--positive)">
              {isProviderMounted ? (
                netWorthDual.primary
              ) : (
                <>
                  {dashboard.net_worth?.amount || "0.00"}
                  <span className="text-sm font-normal text-[var(--text-muted)] ml-1.5">
                    {dashboard.net_worth?.currency || dashboard.currency}
                  </span>
                </>
              )}
            </WidgetValue>
            {renderSecondaryReadout(netWorthDual.secondary)}
            <div className="flex items-center justify-between mt-2">
              <p className="text-[11px] text-[var(--text-faint)]">
                Assets {dashboard.net_worth?.assets || "0.00"} · Liabilities{" "}
                {dashboard.net_worth?.liabilities || "0.00"}
              </p>
              <Link
                to="/app/analytics"
                className="text-[11px] text-gold hover:underline font-medium"
              >
                Trends
              </Link>
            </div>
          </WidgetCard>
        );
      }

      case "safe_to_spend": {
        const safeDual = getDualSummary(
          dashboard.safe_to_spend?.display,
          dashboard.safe_to_spend?.currency || dashboard.currency
        );
        return (
          <WidgetCard key="safe_to_spend" accentColor="var(--info)">
            <div className="flex items-center justify-between mb-3">
              <WidgetLabel>Safe-to-Spend</WidgetLabel>
              <div className="w-7 h-7 rounded-lg bg-[var(--info-bg)] flex items-center justify-center">
                <ShieldCheck className="w-3.5 h-3.5 text-[var(--info)]" />
              </div>
            </div>
            <WidgetValue
              color={
                dashboard.safe_to_spend?.is_negative
                  ? "var(--warning)"
                  : "var(--info)"
              }
            >
              {isProviderMounted ? (
                safeDual.primary
              ) : (
                <>
                  {dashboard.safe_to_spend?.display || "0.00"}
                  <span className="text-sm font-normal text-[var(--text-muted)] ml-1.5">
                    {dashboard.safe_to_spend?.currency || dashboard.currency}
                  </span>
                </>
              )}
            </WidgetValue>
            {renderSecondaryReadout(safeDual.secondary)}
            <p className="text-[11px] text-[var(--text-faint)] mt-1">
              After subtracting upcoming obligations
            </p>
          </WidgetCard>
        );
      }

      case "daily_allowance": {
        const dailyDual = getDualSummary(
          dashboard.daily_allowance?.allowance,
          dashboard.daily_allowance?.currency || dashboard.currency
        );
        return (
          <WidgetCard key="daily_allowance" accentColor="#a78bfa">
            <div className="flex items-center justify-between mb-3">
              <WidgetLabel>Daily Allowance</WidgetLabel>
              <div className="w-7 h-7 rounded-lg bg-purple-500/10 flex items-center justify-center">
                <Calendar className="w-3.5 h-3.5 text-purple-600 dark:text-purple-400" />
              </div>
            </div>
            <WidgetValue
              color={
                dashboard.daily_allowance?.state === "over_budget"
                  ? "var(--negative)"
                  : "#a78bfa"
              }
            >
              {isProviderMounted ? (
                <>
                  {dailyDual.primary}
                  <span className="text-sm font-normal text-[var(--text-muted)] ml-1">/ day</span>
                </>
              ) : (
                <>
                  {dashboard.daily_allowance?.allowance || "0.00"}
                  <span className="text-sm font-normal text-[var(--text-muted)] ml-1">/ day</span>
                </>
              )}
            </WidgetValue>
            {renderSecondaryReadout(dailyDual.secondary ? `${dailyDual.secondary} / day` : null)}
            <p className="text-[11px] text-[var(--text-faint)] mt-1">
              {dashboard.daily_allowance?.remaining_days || 0} days left in period
            </p>
          </WidgetCard>
        );
      }

      case "cash_flow": {
        const inflowStr = dashboard.cash_flow?.table?.[0]?.amount || "0.00";
        const outflowStr = dashboard.cash_flow?.table?.[1]?.amount || "0.00";
        const netStr = dashboard.cash_flow?.table?.[2]?.amount || "0.00";
        const inflowDual = getDualSummary(inflowStr, dashboard.currency);
        const outflowDual = getDualSummary(outflowStr, dashboard.currency);
        const netDual = getDualSummary(netStr, dashboard.currency);
        const inflowNum = Math.max(0, parseNumericAmount(inflowStr));
        const outflowNum = Math.abs(parseNumericAmount(outflowStr));
        const flowSum = inflowNum + outflowNum;
        const inflowPct = flowSum > 0 ? (inflowNum / flowSum) * 100 : 50;
        const outflowPct = flowSum > 0 ? (outflowNum / flowSum) * 100 : 50;
        const savingsRate = inflowNum > 0 ? ((inflowNum - outflowNum) / inflowNum) * 100 : 0;

        return (
          <WidgetCard key="cash_flow" className="lg:col-span-2">
            <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
              <div>
                <h3 className="text-sm font-semibold text-[var(--text)]">Period Cash Flow</h3>
                <p className="text-[11px] text-[var(--text-faint)] mt-0.5">
                  {dashboard.period.start} to {dashboard.period.end}
                </p>
              </div>
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-mono font-semibold bg-[var(--surface-raised)] border border-[var(--border)] text-[var(--text-muted)]">
                Savings Rate:{" "}
                <span
                  className={
                    savingsRate >= 0 ? "text-[var(--positive)]" : "text-[var(--negative)]"
                  }
                >
                  {savingsRate.toFixed(1)}%
                </span>
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4">
              <div className="p-3.5 rounded-lg bg-[var(--positive-bg)] border border-[var(--positive-border)]">
                <div className="flex items-center gap-1.5 text-xs text-[var(--positive)] font-medium mb-2">
                  <ArrowDownRight className="w-3.5 h-3.5" />
                  Inflows
                </div>
                <div className="text-base font-semibold font-tabular text-[var(--text)]">
                  {isProviderMounted ? inflowDual.primary : inflowStr}
                </div>
                {renderSecondaryReadout(inflowDual.secondary)}
              </div>
              <div className="p-3.5 rounded-lg bg-[var(--negative-bg)] border border-[var(--negative-border)]">
                <div className="flex items-center gap-1.5 text-xs text-[var(--negative)] font-medium mb-2">
                  <ArrowUpRight className="w-3.5 h-3.5" />
                  Outflows
                </div>
                <div className="text-base font-semibold font-tabular text-[var(--text)]">
                  {isProviderMounted ? outflowDual.primary : outflowStr}
                </div>
                {renderSecondaryReadout(outflowDual.secondary)}
              </div>
              <div className="p-3.5 rounded-lg bg-[var(--surface-raised)] border border-[var(--border)]">
                <div className="flex items-center gap-1.5 text-xs text-[var(--text-muted)] font-medium mb-2">
                  <TrendingDown className="w-3.5 h-3.5" />
                  Net
                </div>
                <div className="text-base font-semibold font-tabular text-[var(--text)]">
                  {isProviderMounted ? netDual.primary : netStr}
                </div>
                {renderSecondaryReadout(netDual.secondary)}
              </div>
            </div>

            {/* Proportional Cash Flow Bar */}
            <div className="space-y-1.5">
              <div className="h-2.5 w-full rounded-full bg-[var(--surface-raised)] overflow-hidden flex gap-0.5">
                <div
                  className="h-full bg-[var(--positive)] transition-all duration-500 rounded-l-full animate-xaku-bar"
                  style={{ width: `${inflowPct}%` }}
                  title={`Inflows: ${inflowPct.toFixed(1)}%`}
                />
                <div
                  className="h-full bg-[var(--negative)] transition-all duration-500 rounded-r-full animate-xaku-bar"
                  style={{ width: `${outflowPct}%` }}
                  title={`Outflows: ${outflowPct.toFixed(1)}%`}
                />
              </div>
              <div className="flex justify-between text-[10px] font-mono text-[var(--text-faint)]">
                <span>Inflow mix {inflowPct.toFixed(0)}%</span>
                <span>Outflow mix {outflowPct.toFixed(0)}%</span>
              </div>
            </div>
          </WidgetCard>
        );
      }

      case "budget_overview":
        return (
          <WidgetCard key="budget_overview">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-[var(--text)]">Budget Health</h3>
              <Link
                to="/app/budgets"
                className="text-[11px] text-gold hover:underline font-medium"
              >
                View all
              </Link>
            </div>
            {dashboard.budget_overview?.state === "empty" ? (
              <p className="text-xs text-[var(--text-faint)] py-6 text-center">
                No active budgets configured.
              </p>
            ) : (
              <div className="space-y-3.5">
                {dashboard.budget_overview?.items?.slice(0, 4).map((b) => (
                  <div key={b.id} className="space-y-1.5">
                    <div className="flex justify-between items-baseline text-xs">
                      <span className="font-medium text-[var(--text)]">{b.name}</span>
                      <span className="text-[var(--text-faint)] font-tabular">
                        {b.spent} / {b.base} {b.currency}
                      </span>
                    </div>
                    <div className="w-full h-1.5 bg-[var(--surface-raised)] rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all animate-xaku-bar ${
                          b.is_over_budget
                            ? "bg-[var(--negative)]"
                            : "bg-gradient-to-r from-[#F0B90B] to-[#FCD535]"
                        }`}
                        style={{ width: `${Math.min(100, b.percent_used)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </WidgetCard>
        );

      case "savings_progress":
        return (
          <WidgetCard key="savings_progress">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Target className="w-4 h-4 text-[var(--positive)]" />
                <h3 className="text-sm font-semibold text-[var(--text)]">Savings Goals</h3>
              </div>
              <Link
                to="/app/savings"
                className="text-[11px] text-gold hover:underline font-medium"
              >
                View all
              </Link>
            </div>
            {dashboard.savings_progress?.state === "empty" ? (
              <p className="text-xs text-[var(--text-faint)] py-6 text-center">
                No active savings goals.
              </p>
            ) : (
              <div className="space-y-3.5">
                {dashboard.savings_progress?.items?.slice(0, 4).map((g) => (
                  <div key={g.id} className="space-y-1.5">
                    <div className="flex justify-between items-baseline text-xs">
                      <span className="font-medium text-[var(--text)]">{g.name}</span>
                      <span className="text-[var(--text-faint)] font-tabular">
                        {g.contributed} / {g.target} {g.currency}
                      </span>
                    </div>
                    <div className="w-full h-1.5 bg-[var(--surface-raised)] rounded-full overflow-hidden">
                      <div
                        className="h-full bg-[var(--positive)] rounded-full transition-all"
                        style={{ width: `${Math.min(100, g.progress_percent)}%` }}
                      />
                    </div>
                    <div className="text-[10px] text-[var(--text-faint)] text-right">
                      {g.progress_percent}% complete
                    </div>
                  </div>
                ))}
              </div>
            )}
          </WidgetCard>
        );

      case "recent_transactions":
        return (
          <WidgetCard key="recent_transactions" className="lg:col-span-2">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-[var(--text-muted)]" />
                <h3 className="text-sm font-semibold text-[var(--text)]">Recent Transactions</h3>
              </div>
              <Link
                to="/app/transactions"
                className="text-[11px] text-gold hover:underline font-medium"
              >
                See all
              </Link>
            </div>
            {dashboard.recent_transactions?.state === "empty" ? (
              <p className="text-xs text-[var(--text-faint)] py-6 text-center">
                No recent transactions recorded.
              </p>
            ) : (
              <div className="divide-y divide-[var(--border)]">
                {dashboard.recent_transactions?.items?.map((tx) => (
                  <div
                    key={tx.id}
                    className="py-2.5 flex items-center justify-between gap-3 first:pt-0 last:pb-0"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-[var(--text)] truncate">
                          {tx.title}
                        </span>
                        <span
                          className={`text-[10px] px-1.5 py-0.2 rounded border capitalize shrink-0 ${
                            tx.status === "pending"
                              ? "bg-[var(--warning-bg)] border-[var(--warning-border)] text-[var(--warning)]"
                              : tx.status === "cancelled"
                              ? "bg-[var(--surface-raised)] border-[var(--border)] text-[var(--text-faint)]"
                              : "bg-[var(--positive-bg)] border-[var(--positive-border)] text-[var(--positive)]"
                          }`}
                        >
                          {tx.status}
                        </span>
                      </div>
                      <div className="text-[11px] text-[var(--text-faint)] mt-0.5">
                        {tx.occurred_on}
                        {tx.account_name && ` · ${tx.account_name}`}
                        {tx.category_name && ` · ${tx.category_name}`}
                      </div>
                    </div>
                    <div className="font-mono font-semibold text-sm ml-2 shrink-0 text-[var(--text)]">
                      {tx.amount} {tx.currency}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </WidgetCard>
        );

      case "spending_by_category": {
        const categories = dashboard.spending_by_category?.categories || [];
        const R = 42;
        const C = 2 * Math.PI * R;
        let offsetPct = 0;

        return (
          <WidgetCard key="spending_by_category">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <PieChart className="w-4 h-4 text-gold" />
                <h3 className="text-sm font-semibold text-[var(--text)]">Top Spending</h3>
              </div>
              <Link
                to="/app/analytics"
                className="text-[11px] text-gold hover:underline font-medium"
              >
                Reports
              </Link>
            </div>
            {dashboard.spending_by_category?.state === "empty" || categories.length === 0 ? (
              <p className="text-xs text-[var(--text-faint)] py-6 text-center">
                No categorized expenses this period.
              </p>
            ) : (
              <div className="space-y-4">
                {/* Mini SVG Donut Ring */}
                <div className="flex items-center gap-4 pb-3 border-b border-[var(--border)]">
                  <div className="relative w-24 h-24 shrink-0">
                    <svg viewBox="0 0 120 120" className="w-24 h-24 -rotate-90" aria-hidden="true">
                      <circle
                        cx="60"
                        cy="60"
                        r={R}
                        fill="none"
                        stroke="var(--surface-raised)"
                        strokeWidth="16"
                      />
                      {categories.slice(0, 5).map((c, i) => {
                        const pct = Math.max(0, Math.min(100, c.percentage));
                        const dashLen = (pct / 100) * C;
                        const dashOffset = -((offsetPct / 100) * C);
                        offsetPct += pct;
                        return (
                          <circle
                            key={c.category_name}
                            cx="60"
                            cy="60"
                            r={R}
                            fill="none"
                            stroke={SPENDING_PALETTE[i % SPENDING_PALETTE.length]}
                            strokeWidth="16"
                            strokeDasharray={`${dashLen} ${C - dashLen}`}
                            strokeDashoffset={dashOffset}
                            className="animate-xaku-ring transition-all duration-500"
                          />
                        );
                      })}
                    </svg>
                    <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
                      <span className="font-mono text-xs font-bold text-[var(--text)]">
                        {categories[0]?.percentage.toFixed(0)}%
                      </span>
                      <span className="text-[9px] text-[var(--text-faint)]">Top</span>
                    </div>
                  </div>
                  <div className="min-w-0">
                    <div className="text-[11px] text-[var(--text-faint)]">Period total</div>
                    <div className="font-mono text-base font-bold text-[var(--text)] truncate">
                      {dashboard.spending_by_category?.total_spending || "0.00"}{" "}
                      <span className="text-xs font-normal text-[var(--text-muted)]">
                        {dashboard.currency}
                      </span>
                    </div>
                    <div className="text-[11px] text-[var(--text-muted)] mt-0.5 truncate">
                      {categories.length} active categor{categories.length === 1 ? "y" : "ies"}
                    </div>
                  </div>
                </div>

                {/* Progress Bars */}
                <div className="space-y-3">
                  {categories.map((c, i) => {
                    const hue = SPENDING_PALETTE[i % SPENDING_PALETTE.length];
                    return (
                      <div key={c.category_name} className="space-y-1.5">
                        <div className="flex justify-between items-baseline text-xs">
                          <span className="text-[var(--text)] flex items-center gap-1.5">
                            <span
                              className="w-2 h-2 rounded-full shrink-0"
                              style={{ backgroundColor: hue }}
                            />
                            {c.category_name}
                          </span>
                          <span className="font-medium font-tabular text-[var(--text-muted)]">
                            {c.amount} ({c.percentage}%)
                          </span>
                        </div>
                        <div className="w-full h-1.5 bg-[var(--surface-raised)] rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all"
                            style={{
                              width: `${Math.min(100, c.percentage)}%`,
                              background: hue,
                              opacity: 0.9,
                            }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </WidgetCard>
        );
      }

      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-bold text-[var(--text)] tracking-tight">
            Financial Dashboard
          </h1>
          <p className="text-xs text-[var(--text-muted)] mt-1">
            {dashboard.period.start} → {dashboard.period.end}
            <span className="text-[var(--text-faint)] ml-1.5">({dashboard.period.timezone})</span>
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          {/* Period Selector Pills */}
          <div
            className="flex items-center gap-0.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-1 text-xs"
            role="group"
            aria-label="Dashboard Period Filter"
          >
            {PERIOD_PILLS.map((pill) => {
              const isActive = selectedPeriod === pill.value;
              return (
                <button
                  key={pill.label}
                  type="button"
                  onClick={() => setSelectedPeriod(pill.value)}
                  className={`px-2.5 py-1 rounded font-medium transition-colors cursor-pointer ${
                    isActive
                      ? "bg-gold shadow-xs font-semibold"
                      : "text-[var(--text-muted)] hover:text-[var(--text)]"
                  }`}
                >
                  {pill.label}
                </button>
              );
            })}
          </div>

          <button
            type="button"
            onClick={() => setCreateTxOpen(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-gold shadow-xs cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5" />
            Record Transaction
          </button>

          <button
            type="button"
            onClick={() => setLayoutOpen(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border border-[var(--border)] rounded-lg bg-[var(--surface)] hover:bg-[var(--surface-raised)] transition-colors shadow-xs text-[var(--text-muted)] hover:text-[var(--text)] cursor-pointer"
          >
            <SlidersHorizontal className="w-3.5 h-3.5" />
            Customize Layout
          </button>
        </div>
      </div>

      {/* Primary KPI Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {widget_order
          .filter((k) =>
            ["total_balance", "net_worth", "safe_to_spend", "daily_allowance"].includes(k)
          )
          .map((k) => renderWidget(k))}
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {widget_order
          .filter((k) =>
            [
              "cash_flow",
              "budget_overview",
              "savings_progress",
              "recent_transactions",
              "spending_by_category",
            ].includes(k)
          )
          .map((k) => renderWidget(k))}
      </div>

      {/* Customize Layout Modal */}
      {layoutData?.widgets && (
        <DashboardLayoutDialog
          open={layoutOpen}
          onOpenChange={setLayoutOpen}
          currentLayout={layoutData.widgets}
          onSave={async (w) => {
            await saveMutation.mutateAsync(w);
          }}
          onReset={async () => {
            await resetMutation.mutateAsync();
          }}
        />
      )}

      {/* Quick Record Transaction Drawer */}
      {createTxOpen && (
        <CreateTransactionDrawer
          isOpen={createTxOpen}
          onClose={() => setCreateTxOpen(false)}
        />
      )}
    </div>
  );
};
