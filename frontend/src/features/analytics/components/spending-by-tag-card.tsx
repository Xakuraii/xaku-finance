import React, { useMemo, useState } from "react";
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

const NECESSITY_BADGES: Record<string, { label: string; color: string; bg: string; hex: string }> = {
  essential: {
    label: "Essential",
    color: "text-emerald-600 dark:text-emerald-400",
    bg: "bg-emerald-500/10 border-emerald-500/20",
    hex: "#10B981",
  },
  important: {
    label: "Important",
    color: "text-sky-600 dark:text-sky-400",
    bg: "bg-sky-500/10 border-sky-500/20",
    hex: "#38BDF8",
  },
  lifestyle: {
    label: "Lifestyle",
    color: "text-purple-600 dark:text-purple-400",
    bg: "bg-purple-500/10 border-purple-500/20",
    hex: "#A78BFA",
  },
  unplanned: {
    label: "Unplanned",
    color: "text-amber-600 dark:text-amber-400",
    bg: "bg-amber-500/10 border-amber-500/20",
    hex: "#F59E0B",
  },
};

const TAG_PALETTE = ["#F0B90B", "#38BDF8", "#10B981", "#A78BFA", "#F43F5E", "#FB923C"];

export const SpendingByTagCard: React.FC<SpendingByTagCardProps> = ({
  initialData,
  from,
  to,
  currency,
}) => {
  const [activeTab, setActiveTab] = useState<"tags" | "necessity">("tags");
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  const { data, isLoading } = useQuery<TagAnalyticsResponse>({
    queryKey: ["analytics", "tags", from, to, currency],
    queryFn: () => fetchTagAnalytics({ from, to, currency }),
    initialData,
  });

  const tagList = data?.by_tag || [];
  const necessityList = data?.by_necessity || [];
  const totalExpense = data?.total_expense || "0.00";
  const displayCurrency = data?.currency || currency || "USD";

  const donutSlices = useMemo(() => {
    const items = activeTab === "tags" ? tagList : necessityList;
    const R = 60;
    const C = 2 * Math.PI * R;
    let cumulative = 0;
    return items.slice(0, 6).map((item, idx) => {
      const pct = Math.max(0, Math.min(100, item.percentage));
      const dashLen = (pct / 100) * C;
      const offset = -((cumulative / 100) * C);
      cumulative += pct;
      const color =
        activeTab === "tags"
          ? TAG_PALETTE[idx % TAG_PALETTE.length]
          : NECESSITY_BADGES[(item as typeof necessityList[number]).necessity]?.hex ||
            TAG_PALETTE[idx % TAG_PALETTE.length];
      return { idx, pct, color, dashArray: `${dashLen} ${C - dashLen}`, dashOffset: offset };
    });
  }, [activeTab, tagList, necessityList]);

  if (isLoading && !data) {
    return (
      <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 text-muted animate-pulse">
        <div className="h-6 w-48 bg-[var(--surface-raised)] rounded mb-4" />
        <div className="space-y-3">
          <div className="h-4 bg-[var(--surface-raised)] rounded w-full" />
          <div className="h-4 bg-[var(--surface-raised)] rounded w-3/4" />
        </div>
      </div>
    );
  }

  const activeCount = activeTab === "tags" ? tagList.length : necessityList.length;
  const topSlicePct =
    hoveredIdx !== null && donutSlices[hoveredIdx]
      ? donutSlices[hoveredIdx].pct
      : donutSlices[0]?.pct ?? 0;

  return (
    <div
      data-testid="spending-by-tag-card"
      className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 text-main shadow-xs relative overflow-hidden transition-colors"
    >
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-4 border-b border-[var(--border)] gap-3">
        <div>
          <div className="flex items-center gap-2">
            <PieChart className="w-5 h-5 text-gold" />
            <h3 className="font-semibold text-lg text-main">Spending Intelligence</h3>
          </div>
          <p className="text-xs text-muted mt-0.5">
            Total expenses:{" "}
            <span className="font-semibold text-main font-tabular">
              {totalExpense} {displayCurrency}
            </span>
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center gap-1 bg-[var(--surface-raised)] p-1 rounded-lg border border-[var(--border)]">
          <button
            type="button"
            onClick={() => {
              setActiveTab("tags");
              setHoveredIdx(null);
            }}
            className={`flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-md transition-all cursor-pointer ${
              activeTab === "tags"
                ? "bg-gold shadow-xs font-semibold"
                : "text-muted hover:text-main"
            }`}
          >
            <Tag className="w-3.5 h-3.5" />
            Tags
          </button>
          <button
            type="button"
            onClick={() => {
              setActiveTab("necessity");
              setHoveredIdx(null);
            }}
            className={`flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-md transition-all cursor-pointer ${
              activeTab === "necessity"
                ? "bg-gold shadow-xs font-semibold"
                : "text-muted hover:text-main"
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            Necessity
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="pt-5">
        {activeCount === 0 ? (
          activeTab === "tags" ? (
            <div className="py-8 text-center text-muted text-sm">
              <Tag className="w-8 h-8 mx-auto mb-2 opacity-50 text-gold" />
              No tagged expenses found in this period.
            </div>
          ) : (
            <div className="py-8 text-center text-muted text-sm">
              <Sparkles className="w-8 h-8 mx-auto mb-2 opacity-50 text-gold" />
              No classified expenses recorded in this period.
            </div>
          )
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-[190px_1fr] gap-6 items-center">
            {/* SVG Donut Summary */}
            <div className="relative flex items-center justify-center mx-auto">
              <svg
                viewBox="0 0 180 180"
                className="w-40 h-40 -rotate-90"
                role="img"
                aria-label="Spending Concentration Donut"
              >
                <circle
                  cx="90"
                  cy="90"
                  r="60"
                  fill="none"
                  stroke="var(--surface-raised)"
                  strokeWidth="22"
                />
                {donutSlices.map((s) => (
                  <circle
                    key={s.idx}
                    cx="90"
                    cy="90"
                    r="60"
                    fill="none"
                    stroke={s.color}
                    strokeWidth={hoveredIdx === s.idx ? 26 : 22}
                    strokeDasharray={s.dashArray}
                    strokeDashoffset={s.dashOffset}
                    className="animate-xaku-ring transition-all duration-300 cursor-pointer"
                    onMouseEnter={() => setHoveredIdx(s.idx)}
                    onMouseLeave={() => setHoveredIdx(null)}
                  />
                ))}
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center text-center pointer-events-none">
                <span className="font-mono text-lg font-bold text-main">
                  {topSlicePct.toFixed(0)}%
                </span>
                <span className="text-[10px] text-muted">
                  {hoveredIdx !== null ? "Selected share" : "Top share"}
                </span>
              </div>
            </div>

            {/* Bars */}
            {activeTab === "tags" ? (
              <div className="space-y-4 animate-xaku-fade-up">
                {tagList.map((item, idx) => (
                  <div
                    key={item.tag}
                    className="space-y-1.5"
                    onMouseEnter={() => setHoveredIdx(idx)}
                    onMouseLeave={() => setHoveredIdx(null)}
                  >
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-medium text-main flex items-center gap-1.5">
                        <span
                          className="w-2 h-2 rounded-full shrink-0"
                          style={{ backgroundColor: TAG_PALETTE[idx % TAG_PALETTE.length] }}
                        />
                        <span className="text-gold font-semibold">#</span>
                        {item.tag}
                        <span className="text-[10px] text-muted">
                          ({item.count} {item.count === 1 ? "txn" : "txns"})
                        </span>
                      </span>
                      <span className="text-main font-tabular font-medium">
                        {item.amount} {displayCurrency}{" "}
                        <span className="text-muted text-[11px]">({item.percentage}%)</span>
                      </span>
                    </div>
                    <div className="h-2 w-full bg-[var(--surface-raised)] rounded-full overflow-hidden border border-[var(--border)]">
                      <div
                        className="h-full rounded-full transition-all duration-500"
                        style={{
                          width: `${Math.min(item.percentage, 100)}%`,
                          backgroundColor: TAG_PALETTE[idx % TAG_PALETTE.length],
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="space-y-4">
                {necessityList.map((item, idx) => {
                  const meta = NECESSITY_BADGES[item.necessity] || {
                    label: item.necessity,
                    color: "text-muted",
                    bg: "bg-[var(--surface-raised)] border-[var(--border)]",
                    hex: "#F59E0B",
                  };
                  return (
                    <div
                      key={item.necessity}
                      className="space-y-1.5"
                      onMouseEnter={() => setHoveredIdx(idx)}
                      onMouseLeave={() => setHoveredIdx(null)}
                    >
                      <div className="flex items-center justify-between text-xs">
                        <div className="flex items-center gap-2">
                          <span
                            className={`px-2 py-0.5 text-[10px] font-semibold rounded border ${meta.bg} ${meta.color}`}
                          >
                            {meta.label}
                          </span>
                          <span className="text-[10px] text-muted">
                            ({item.count} {item.count === 1 ? "txn" : "txns"})
                          </span>
                        </div>
                        <span className="text-main font-tabular font-medium">
                          {item.amount} {displayCurrency}{" "}
                          <span className="text-muted text-[11px]">({item.percentage}%)</span>
                        </span>
                      </div>
                      <div className="h-2 w-full bg-[var(--surface-raised)] rounded-full overflow-hidden border border-[var(--border)]">
                        <div
                          className={`h-full rounded-full transition-all duration-500 ${
                            item.necessity === "essential"
                              ? "bg-emerald-500"
                              : item.necessity === "important"
                              ? "bg-sky-500"
                              : item.necessity === "lifestyle"
                              ? "bg-purple-500"
                              : "bg-amber-500"
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
        )}
      </div>
    </div>
  );
};
