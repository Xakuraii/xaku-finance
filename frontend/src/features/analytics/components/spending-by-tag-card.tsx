import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Tag, Sparkles, PieChart, Layers } from "lucide-react";
import { fetchTagAnalytics } from "../api/analytics-api";
import { TagAnalyticsResponse } from "../types";

interface SpendingByTagCardProps {
  initialData?: TagAnalyticsResponse;
  from?: string;
  to?: string;
  currency?: string;
}

const NECESSITY_BADGES: Record<string, { label: string; color: string; bg: string }> = {
  essential: { label: "Essential", color: "text-emerald-400", bg: "bg-emerald-500/10 border-emerald-500/20" },
  important: { label: "Important", color: "text-sky-400", bg: "bg-sky-500/10 border-sky-500/20" },
  lifestyle: { label: "Lifestyle", color: "text-purple-400", bg: "bg-purple-500/10 border-purple-500/20" },
  unplanned: { label: "Unplanned", color: "text-amber-400", bg: "bg-amber-500/10 border-amber-500/20" },
};

export const SpendingByTagCard: React.FC<SpendingByTagCardProps> = ({
  initialData,
  from,
  to,
  currency,
}) => {
  const [activeTab, setActiveTab] = useState<"tags" | "necessity">("tags");

  const { data, isLoading } = useQuery<TagAnalyticsResponse>({
    queryKey: ["analytics", "tags", from, to, currency],
    queryFn: () => fetchTagAnalytics({ from, to, currency }),
    initialData,
  });

  if (isLoading && !data) {
    return (
      <div className="rounded-xl border border-[#2b313a] bg-[#181a20] p-6 text-slate-400 animate-pulse">
        <div className="h-6 w-48 bg-slate-800 rounded mb-4" />
        <div className="space-y-3">
          <div className="h-4 bg-slate-800 rounded w-full" />
          <div className="h-4 bg-slate-800 rounded w-3/4" />
        </div>
      </div>
    );
  }

  const tagList = data?.by_tag || [];
  const necessityList = data?.by_necessity || [];
  const totalExpense = data?.total_expense || "0.00";
  const displayCurrency = data?.currency || currency || "USD";

  return (
    <div
      data-testid="spending-by-tag-card"
      className="rounded-xl border border-[#2b313a] bg-[#181a20] p-6 text-white shadow-lg relative overflow-hidden"
    >
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-4 border-b border-[#2b313a] gap-3">
        <div>
          <div className="flex items-center gap-2">
            <PieChart className="w-5 h-5 text-[#F0B90B]" />
            <h3 className="font-semibold text-lg text-slate-100">Spending Intelligence</h3>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Total expenses:{" "}
            <span className="font-medium text-slate-200">
              {totalExpense} {displayCurrency}
            </span>
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center gap-1 bg-[#0b0e11] p-1 rounded-lg border border-[#2b313a]">
          <button
            type="button"
            onClick={() => setActiveTab("tags")}
            className={`flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-md transition-all ${
              activeTab === "tags"
                ? "bg-[#F0B90B] text-black shadow-sm font-semibold"
                : "text-slate-400 hover:text-white"
            }`}
          >
            <Tag className="w-3.5 h-3.5" />
            Tags
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("necessity")}
            className={`flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-md transition-all ${
              activeTab === "necessity"
                ? "bg-[#F0B90B] text-black shadow-sm font-semibold"
                : "text-slate-400 hover:text-white"
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            Necessity
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="pt-4">
        {activeTab === "tags" ? (
          tagList.length === 0 ? (
            <div className="py-8 text-center text-slate-500 text-sm">
              <Tag className="w-8 h-8 mx-auto mb-2 text-slate-600 opacity-60" />
              No tagged expenses found in this period.
            </div>
          ) : (
            <div className="space-y-4">
              {tagList.map((item) => (
                <div key={item.tag} className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-medium text-slate-200 flex items-center gap-1.5">
                      <span className="text-slate-400">#</span>
                      {item.tag}
                      <span className="text-[10px] text-slate-500">
                        ({item.count} {item.count === 1 ? "txn" : "txns"})
                      </span>
                    </span>
                    <span className="text-slate-300 font-mono">
                      {item.amount} {displayCurrency}{" "}
                      <span className="text-slate-500">({item.percentage}%)</span>
                    </span>
                  </div>
                  <div className="h-2 w-full bg-[#0b0e11] rounded-full overflow-hidden border border-[#2b313a]/50">
                    <div
                      className="h-full bg-gradient-to-r from-[#F0B90B] to-[#FCD535] rounded-full transition-all duration-500"
                      style={{ width: `${Math.min(item.percentage, 100)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )
        ) : necessityList.length === 0 ? (
          <div className="py-8 text-center text-slate-500 text-sm">
            <Sparkles className="w-8 h-8 mx-auto mb-2 text-slate-600 opacity-60" />
            No classified expenses recorded in this period.
          </div>
        ) : (
          <div className="space-y-4">
            {necessityList.map((item) => {
              const meta = NECESSITY_BADGES[item.necessity] || {
                label: item.necessity,
                color: "text-slate-300",
                bg: "bg-slate-800 border-slate-700",
              };
              return (
                <div key={item.necessity} className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <span
                        className={`px-2 py-0.5 text-[10px] font-semibold rounded border ${meta.bg} ${meta.color}`}
                      >
                        {meta.label}
                      </span>
                      <span className="text-[10px] text-slate-500">
                        ({item.count} {item.count === 1 ? "txn" : "txns"})
                      </span>
                    </div>
                    <span className="text-slate-300 font-mono">
                      {item.amount} {displayCurrency}{" "}
                      <span className="text-slate-500">({item.percentage}%)</span>
                    </span>
                  </div>
                  <div className="h-2 w-full bg-[#0b0e11] rounded-full overflow-hidden border border-[#2b313a]/50">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        item.necessity === "essential"
                          ? "bg-emerald-400"
                          : item.necessity === "important"
                          ? "bg-sky-400"
                          : item.necessity === "lifestyle"
                          ? "bg-purple-400"
                          : "bg-amber-400"
                      }`}
                      style={{ width: `${Math.min(item.percentage, 100)}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
