import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  SlidersHorizontal,
  Wallet,
  TrendingUp,
  ShieldCheck,
  Calendar,
  ArrowRight,
  PieChart,
  Target,
  Clock,
  AlertTriangle,
  ArrowUpRight,
  ArrowDownRight,
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

export const DashboardPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [layoutOpen, setLayoutOpen] = useState(false);

  const { data: dashboard, isLoading, error } = useQuery<DashboardResponse>({
    queryKey: ["dashboard-data"],
    queryFn: () => fetchDashboard(),
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
      <div className="p-6 max-w-7xl mx-auto space-y-6 animate-pulse">
        <div className="h-8 w-48 bg-muted rounded"></div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="h-32 bg-muted rounded-xl"></div>
          <div className="h-32 bg-muted rounded-xl"></div>
          <div className="h-32 bg-muted rounded-xl"></div>
          <div className="h-32 bg-muted rounded-xl"></div>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="h-64 bg-muted rounded-xl lg:col-span-2"></div>
          <div className="h-64 bg-muted rounded-xl"></div>
        </div>
      </div>
    );
  }

  if (error || !dashboard) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-xl text-destructive text-sm">
          Failed to load dashboard data. Please try refreshing the page.
        </div>
      </div>
    );
  }

  const { widget_order } = dashboard;

  const renderWidget = (key: string) => {
    switch (key) {
      case "total_balance":
        return (
          <div key="total_balance" className="bg-card border border-border p-5 rounded-xl shadow-sm space-y-3">
            <div className="flex items-center justify-between text-muted-foreground">
              <span className="text-xs font-semibold uppercase tracking-wider">Account Balances</span>
              <Wallet className="w-4 h-4 text-primary" />
            </div>
            <div>
              <div className="text-2xl font-bold tracking-tight">
                {dashboard.converted_total?.amount || "0.00"}{" "}
                <span className="text-sm font-normal text-muted-foreground">
                  {dashboard.converted_total?.currency || dashboard.currency}
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">Consolidated Available</p>
            </div>
            {dashboard.balances && dashboard.balances.length > 0 && (
              <div className="pt-2 border-t border-border flex flex-wrap gap-2 text-xs">
                {dashboard.balances.map((b) => (
                  <span key={b.currency} className="bg-muted px-2 py-0.5 rounded font-mono text-[11px]">
                    {b.total} {b.currency}
                  </span>
                ))}
              </div>
            )}
          </div>
        );

      case "net_worth":
        return (
          <div key="net_worth" className="bg-card border border-border p-5 rounded-xl shadow-sm space-y-3">
            <div className="flex items-center justify-between text-muted-foreground">
              <span className="text-xs font-semibold uppercase tracking-wider">Net Worth</span>
              <TrendingUp className="w-4 h-4 text-emerald-500" />
            </div>
            <div>
              <div className="text-2xl font-bold tracking-tight text-emerald-600 dark:text-emerald-400">
                {dashboard.net_worth?.amount || "0.00"}{" "}
                <span className="text-sm font-normal text-muted-foreground">
                  {dashboard.net_worth?.currency || dashboard.currency}
                </span>
              </div>
              <div className="flex items-center justify-between mt-1">
                <span className="text-xs text-muted-foreground">
                  Assets {dashboard.net_worth?.assets || "0.00"} • Liab {dashboard.net_worth?.liabilities || "0.00"}
                </span>
                <Link to="/app/analytics" className="text-xs text-primary hover:underline flex items-center gap-0.5">
                  Trends <ArrowRight className="w-3 h-3" />
                </Link>
              </div>
            </div>
          </div>
        );

      case "safe_to_spend":
        return (
          <div key="safe_to_spend" className="bg-card border border-border p-5 rounded-xl shadow-sm space-y-3">
            <div className="flex items-center justify-between text-muted-foreground">
              <span className="text-xs font-semibold uppercase tracking-wider">Safe-to-Spend</span>
              <ShieldCheck className="w-4 h-4 text-blue-500" />
            </div>
            <div>
              <div
                className={`text-2xl font-bold tracking-tight ${
                  dashboard.safe_to_spend?.is_negative ? "text-amber-500" : "text-blue-600 dark:text-blue-400"
                }`}
              >
                {dashboard.safe_to_spend?.display || "0.00"}{" "}
                <span className="text-sm font-normal text-muted-foreground">
                  {dashboard.safe_to_spend?.currency || dashboard.currency}
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">
                Spendable cash minus upcoming obligations
              </p>
            </div>
          </div>
        );

      case "daily_allowance":
        return (
          <div key="daily_allowance" className="bg-card border border-border p-5 rounded-xl shadow-sm space-y-3">
            <div className="flex items-center justify-between text-muted-foreground">
              <span className="text-xs font-semibold uppercase tracking-wider">Daily Allowance</span>
              <Calendar className="w-4 h-4 text-purple-500" />
            </div>
            <div>
              <div
                className={`text-2xl font-bold tracking-tight ${
                  dashboard.daily_allowance?.state === "over_budget"
                    ? "text-destructive"
                    : "text-purple-600 dark:text-purple-400"
                }`}
              >
                {dashboard.daily_allowance?.allowance || "0.00"}{" "}
                <span className="text-sm font-normal text-muted-foreground">/ day</span>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">
                {dashboard.daily_allowance?.remaining_days || 0} days left in period
              </p>
            </div>
          </div>
        );

      case "cash_flow":
        return (
          <div key="cash_flow" className="bg-card border border-border p-5 rounded-xl shadow-sm lg:col-span-2 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold">Period Cash Flow</h3>
              <span className="text-xs text-muted-foreground">
                {dashboard.period.start} to {dashboard.period.end}
              </span>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div className="p-3 bg-accent/30 rounded-lg">
                <div className="flex items-center gap-1 text-xs text-emerald-600 dark:text-emerald-400 font-medium">
                  <ArrowDownRight className="w-3.5 h-3.5" /> Inflows
                </div>
                <div className="text-base font-semibold mt-1">
                  {dashboard.cash_flow?.table?.[0]?.amount || "0.00"}
                </div>
              </div>
              <div className="p-3 bg-accent/30 rounded-lg">
                <div className="flex items-center gap-1 text-xs text-rose-600 dark:text-rose-400 font-medium">
                  <ArrowUpRight className="w-3.5 h-3.5" /> Outflows
                </div>
                <div className="text-base font-semibold mt-1">
                  {dashboard.cash_flow?.table?.[1]?.amount || "0.00"}
                </div>
              </div>
              <div className="p-3 bg-accent/30 rounded-lg">
                <div className="text-xs text-muted-foreground font-medium">Net Cash Flow</div>
                <div className="text-base font-semibold mt-1">
                  {dashboard.cash_flow?.table?.[2]?.amount || "0.00"}
                </div>
              </div>
            </div>
          </div>
        );

      case "budget_overview":
        return (
          <div key="budget_overview" className="bg-card border border-border p-5 rounded-xl shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold">Budget Health</h3>
              <Link to="/app/budgets" className="text-xs text-primary hover:underline flex items-center gap-0.5">
                All <ArrowRight className="w-3 h-3" />
              </Link>
            </div>
            {dashboard.budget_overview?.state === "empty" ? (
              <p className="text-xs text-muted-foreground py-4 text-center">
                No active budgets configured.
              </p>
            ) : (
              <div className="space-y-3">
                {dashboard.budget_overview?.items?.slice(0, 4).map((b) => (
                  <div key={b.id} className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span className="font-medium">{b.name}</span>
                      <span className="text-muted-foreground">
                        {b.spent} / {b.base} {b.currency}
                      </span>
                    </div>
                    <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${
                          b.is_over_budget ? "bg-destructive" : "bg-primary"
                        }`}
                        style={{ width: `${Math.min(100, b.percent_used)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        );

      case "savings_progress":
        return (
          <div key="savings_progress" className="bg-card border border-border p-5 rounded-xl shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <Target className="w-4 h-4 text-primary" />
                <h3 className="text-sm font-semibold">Savings Goals</h3>
              </div>
              <Link to="/app/savings" className="text-xs text-primary hover:underline flex items-center gap-0.5">
                View <ArrowRight className="w-3 h-3" />
              </Link>
            </div>
            {dashboard.savings_progress?.state === "empty" ? (
              <p className="text-xs text-muted-foreground py-4 text-center">
                No active savings goals.
              </p>
            ) : (
              <div className="space-y-3">
                {dashboard.savings_progress?.items?.slice(0, 4).map((g) => (
                  <div key={g.id} className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span className="font-medium">{g.name}</span>
                      <span className="text-muted-foreground">
                        {g.contributed} / {g.target} {g.currency} ({g.progress_percent}%)
                      </span>
                    </div>
                    <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden">
                      <div
                        className="h-full bg-emerald-500 rounded-full transition-all"
                        style={{ width: `${Math.min(100, g.progress_percent)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        );

      case "recent_transactions":
        return (
          <div key="recent_transactions" className="bg-card border border-border p-5 rounded-xl shadow-sm lg:col-span-2 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <Clock className="w-4 h-4 text-muted-foreground" />
                <h3 className="text-sm font-semibold">Recent Transactions</h3>
              </div>
              <Link to="/app/transactions" className="text-xs text-primary hover:underline flex items-center gap-0.5">
                See all <ArrowRight className="w-3 h-3" />
              </Link>
            </div>
            {dashboard.recent_transactions?.state === "empty" ? (
              <p className="text-xs text-muted-foreground py-6 text-center">
                No recent transactions recorded.
              </p>
            ) : (
              <div className="divide-y divide-border">
                {dashboard.recent_transactions?.items?.map((tx) => (
                  <div key={tx.id} className="py-2.5 flex items-center justify-between text-xs first:pt-0 last:pb-0">
                    <div>
                      <div className="font-medium text-foreground">{tx.title}</div>
                      <div className="text-[11px] text-muted-foreground">
                        {tx.occurred_on} • {tx.account_name || "Account"} {tx.category_name && `• ${tx.category_name}`}
                      </div>
                    </div>
                    <div className="font-mono font-medium">
                      {tx.amount} {tx.currency}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        );

      case "spending_by_category":
        return (
          <div key="spending_by_category" className="bg-card border border-border p-5 rounded-xl shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <PieChart className="w-4 h-4 text-primary" />
                <h3 className="text-sm font-semibold">Top Spending</h3>
              </div>
              <Link to="/app/analytics" className="text-xs text-primary hover:underline flex items-center gap-0.5">
                Reports <ArrowRight className="w-3 h-3" />
              </Link>
            </div>
            {dashboard.spending_by_category?.state === "empty" ? (
              <p className="text-xs text-muted-foreground py-6 text-center">
                No categorized expenses this period.
              </p>
            ) : (
              <div className="space-y-2.5">
                {dashboard.spending_by_category?.categories?.map((c) => (
                  <div key={c.category_name} className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span>{c.category_name}</span>
                      <span className="font-medium">{c.amount} ({c.percentage}%)</span>
                    </div>
                    <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden">
                      <div
                        className="h-full bg-primary/80 rounded-full"
                        style={{ width: `${Math.min(100, c.percentage)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Financial Dashboard</h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Overview for {dashboard.period.start} to {dashboard.period.end} ({dashboard.period.timezone})
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setLayoutOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border border-border rounded-lg bg-card hover:bg-muted transition-colors shadow-sm"
          >
            <SlidersHorizontal className="w-3.5 h-3.5 text-muted-foreground" />
            Customize Layout
          </button>
        </div>
      </div>

      {/* Primary KPI Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {widget_order.filter((k) =>
          ["total_balance", "net_worth", "safe_to_spend", "daily_allowance"].includes(k)
        ).map((k) => renderWidget(k))}
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {widget_order.filter((k) =>
          ["cash_flow", "budget_overview", "savings_progress", "recent_transactions", "spending_by_category"].includes(k)
        ).map((k) => renderWidget(k))}
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
    </div>
  );
};
