import React from "react";
import { Plus, Trash2, AlertCircle } from "lucide-react";
import { formatMoney } from "@/lib/money";

export interface SplitItem {
  category_id?: string;
  amount: number | string; // in minor units if number, or decimal string
  memo?: string;
}

export interface SplitEditorProps {
  total: number; // in minor units
  currency: string;
  value: SplitItem[];
  onChange: (splits: SplitItem[]) => void;
  categories?: { id: string; name: string }[];
  onSave?: () => void;
  isSaving?: boolean;
}

export const SplitEditor: React.FC<SplitEditorProps> = ({
  total,
  currency,
  value,
  onChange,
  categories = [],
  onSave,
  isSaving = false,
}) => {
  // Convert all split amounts to minor units for calculation
  const sumMinor = value.reduce((sum, item) => {
    let minor = 0;
    if (typeof item.amount === "number") {
      minor = item.amount;
    } else if (typeof item.amount === "string") {
      const parsed = parseFloat(item.amount);
      if (!isNaN(parsed)) {
        minor = Math.round(parsed * 100);
      }
    }
    return sum + minor;
  }, 0);

  const diffMinor = total - sumMinor;
  const isBalanced = diffMinor === 0;

  const handleAddSplit = () => {
    const nextAmount = Math.max(0, diffMinor);
    onChange([
      ...value,
      {
        category_id: categories[0]?.id || "",
        amount: nextAmount,
        memo: "",
      },
    ]);
  };

  const handleRemoveSplit = (index: number) => {
    onChange(value.filter((_, i) => i !== index));
  };

  const handleUpdateSplit = (index: number, updates: Partial<SplitItem>) => {
    const updated = value.map((item, i) => (i === index ? { ...item, ...updates } : item));
    onChange(updated);
  };

  return (
    <div className="space-y-3 rounded-lg border border-[var(--border)] bg-[var(--surface-raised)] p-4">
      <div className="flex items-center justify-between text-xs font-medium text-main border-b border-[var(--border)] pb-2">
        <span>Split Allocations</span>
        <span className="font-tabular text-muted">
          Total: {formatMoney(total, currency)}
        </span>
      </div>

      <div className="space-y-2">
        {value.map((split, idx) => {
          const splitAmount =
            typeof split.amount === "number"
              ? (split.amount / 100).toFixed(2)
              : String(split.amount || "");

          return (
            <div key={idx} className="flex items-center gap-2">
              <select
                value={split.category_id || ""}
                onChange={(e) => handleUpdateSplit(idx, { category_id: e.target.value })}
                className="flex-1 rounded bg-[var(--surface)] border border-[var(--border)] px-2.5 py-1.5 text-xs text-main focus:border-[var(--accent)] focus:outline-none"
              >
                <option value="">Select Category</option>
                {categories.map((cat) => (
                  <option key={cat.id} value={cat.id}>
                    {cat.name}
                  </option>
                ))}
              </select>

              <div className="relative w-28">
                <input
                  type="text"
                  placeholder="0.00"
                  value={splitAmount}
                  onChange={(e) => {
                    const parsed = parseFloat(e.target.value);
                    const minor = isNaN(parsed) ? 0 : Math.round(parsed * 100);
                    handleUpdateSplit(idx, { amount: minor });
                  }}
                  className="w-full rounded bg-[var(--surface)] border border-[var(--border)] px-2.5 py-1.5 text-xs text-main font-tabular focus:border-[var(--accent)] focus:outline-none"
                />
              </div>

              <input
                type="text"
                placeholder="Memo"
                value={split.memo || ""}
                onChange={(e) => handleUpdateSplit(idx, { memo: e.target.value })}
                className="w-32 rounded bg-[var(--surface)] border border-[var(--border)] px-2.5 py-1.5 text-xs text-main focus:border-[var(--accent)] focus:outline-none"
              />

              <button
                type="button"
                onClick={() => handleRemoveSplit(idx)}
                className="text-muted hover:text-negative cursor-pointer p-1"
                aria-label="Remove split"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          );
        })}
      </div>

      <div className="flex items-center justify-between pt-2">
        <button
          type="button"
          onClick={handleAddSplit}
          className="inline-flex items-center gap-1 text-xs text-gold hover:underline cursor-pointer"
        >
          <Plus className="w-3.5 h-3.5" />
          Add Split Line
        </button>

        {!isBalanced && (
          <div className="flex items-center gap-1.5 text-xs text-warning">
            <AlertCircle className="w-3.5 h-3.5 shrink-0" />
            <span className="font-tabular font-medium">
              {formatMoney(Math.abs(diffMinor), currency)} {diffMinor > 0 ? "unallocated" : "over-allocated"}
            </span>
          </div>
        )}
      </div>

      {onSave && (
        <div className="pt-2 border-t border-[var(--border)] flex justify-end">
          <button
            type="button"
            onClick={onSave}
            disabled={!isBalanced || isSaving}
            className="rounded bg-gold px-4 py-2 text-xs font-semibold cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed shadow-xs"
          >
            {isSaving ? "Saving..." : "Save Transaction"}
          </button>
        </div>
      )}
    </div>
  );
};
