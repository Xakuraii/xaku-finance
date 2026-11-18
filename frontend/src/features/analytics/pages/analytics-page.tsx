import React, { useState } from "react";
import { SpendingByTagCard } from "../components/spending-by-tag-card";
import { useAuth } from "@/features/auth/auth-context";
import { Calendar, BarChart3 } from "lucide-react";

export const AnalyticsPage: React.FC = () => {
  const { workspace } = useAuth();
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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-[var(--border)] pb-4">
        <div>
          <h1 className="font-display text-2xl font-semibold text-main tracking-tight flex items-center gap-2">
            <BarChart3 className="w-6 h-6 text-gold" />
            Spending Analytics
          </h1>
          <p className="text-xs text-muted mt-1">
            Categorize financial outflows by built-in tags and necessity classifications.
          </p>
        </div>

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

      {/* Main Analytics Card */}
      <SpendingByTagCard
        from={fromDate || undefined}
        to={toDate}
        currency={workspace?.reporting_currency || "USD"}
      />
    </div>
  );
};
