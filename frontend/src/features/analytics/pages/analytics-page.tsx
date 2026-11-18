import React, { useState } from "react";
import { SpendingByTagCard } from "../components/spending-by-tag-card";
import { NetWorthCard } from "../components/net-worth-card";
import { NetWorthChart } from "../components/net-worth-chart";
import { SafeToSpendCard } from "../components/safe-to-spend-card";
import { DailyAllowanceCard } from "../components/daily-allowance-card";
import { ReportsView } from "../components/reports-view";
import { useAuth } from "@/features/auth/auth-context";
import {
  Calendar,
  BarChart3,
  Landmark,
  PieChart,
  Sparkles,
  FileSpreadsheet,
} from "lucide-react";

export const AnalyticsPage: React.FC = () => {
  const { workspace } = useAuth();
  const [activeTab, setActiveTab] = useState<
    "net_worth" | "pacing" | "reports" | "spending"
  >("net_worth");
  const [period, setPeriod] = useState<"30d" | "this_month" | "all">("30d");

  // Calculate dates
  const now = new Date();
  let fromDate = "";
  const toDate = now.toISOString().slice(0, 10);

  if (period === "30d") {
    const d = new Date();
    d.setDate(d.getDate() - 30);
    fromDate = d.toISOString().slice(0, 10);
  } else if (period === "this_month") {
    fromDate = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-01`;
  }

  const currency = workspace?.reporting_currency || "USD";

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-[var(--border)] pb-4">
        <div>
          <h1 className="font-display text-2xl font-semibold text-main tracking-tight flex items-center gap-2">
            <BarChart3 className="w-6 h-6 text-gold" />
            Financial Intelligence
          </h1>
          <p className="text-xs text-muted mt-1">
            Historical net worth, Safe-to-Spend pacing, financial statements, and spending analytics.
          </p>
        </div>

        {/* Section Tabs */}
        <div className="flex items-center gap-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-1 text-xs">
          <button
            type="button"
            onClick={() => setActiveTab("net_worth")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded font-medium transition-colors cursor-pointer ${
              activeTab === "net_worth"
                ? "bg-gold text-black font-semibold"
                : "text-muted hover:text-main"
            }`}
          >
            <Landmark className="w-3.5 h-3.5" />
            Net Worth
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("pacing")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded font-medium transition-colors cursor-pointer ${
              activeTab === "pacing"
                ? "bg-gold text-black font-semibold"
                : "text-muted hover:text-main"
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            Safe-to-Spend
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("reports")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded font-medium transition-colors cursor-pointer ${
              activeTab === "reports"
                ? "bg-gold text-black font-semibold"
                : "text-muted hover:text-main"
            }`}
          >
            <FileSpreadsheet className="w-3.5 h-3.5" />
            Reports
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("spending")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded font-medium transition-colors cursor-pointer ${
              activeTab === "spending"
                ? "bg-gold text-black font-semibold"
                : "text-muted hover:text-main"
            }`}
          >
            <PieChart className="w-3.5 h-3.5" />
            Spending
          </button>
        </div>
      </div>

      {activeTab === "net_worth" && (
        <div className="space-y-6">
          <NetWorthCard currency={currency} />
          <NetWorthChart currency={currency} />
        </div>
      )}

      {activeTab === "pacing" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <SafeToSpendCard currency={currency} />
          <DailyAllowanceCard currency={currency} />
        </div>
      )}

      {activeTab === "reports" && <ReportsView currency={currency} />}

      {activeTab === "spending" && (
        <div className="space-y-6">
          <div className="flex justify-end">
            <div className="flex items-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-1 text-xs">
              <Calendar className="w-3.5 h-3.5 text-muted ml-2 mr-1" />
              <button
                type="button"
                onClick={() => setPeriod("30d")}
                className={`px-3 py-1 rounded font-medium transition-colors cursor-pointer ${
                  period === "30d"
                    ? "bg-gold text-black font-semibold"
                    : "text-muted hover:text-main"
                }`}
              >
                Last 30 Days
              </button>
              <button
                type="button"
                onClick={() => setPeriod("this_month")}
                className={`px-3 py-1 rounded font-medium transition-colors cursor-pointer ${
                  period === "this_month"
                    ? "bg-gold text-black font-semibold"
                    : "text-muted hover:text-main"
                }`}
              >
                This Month
              </button>
              <button
                type="button"
                onClick={() => setPeriod("all")}
                className={`px-3 py-1 rounded font-medium transition-colors cursor-pointer ${
                  period === "all"
                    ? "bg-gold text-black font-semibold"
                    : "text-muted hover:text-main"
                }`}
              >
                All Time
              </button>
            </div>
          </div>

          <SpendingByTagCard
            from={fromDate || undefined}
            to={toDate}
            currency={currency}
          />
        </div>
      )}
    </div>
  );
};
