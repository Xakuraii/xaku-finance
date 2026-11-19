import React from "react";
import { ArrowLeft, ArrowRight, Table2 } from "lucide-react";
import { ColumnMapping } from "../types";

interface ColumnMappingStepProps {
  headers: string[];
  mapping: ColumnMapping;
  onChange: (mapping: ColumnMapping) => void;
  onNext: () => void;
  onBack: () => void;
}

export const ColumnMappingStep: React.FC<ColumnMappingStepProps> = ({
  headers,
  mapping,
  onChange,
  onNext,
  onBack,
}) => {
  const handleChange = (field: keyof ColumnMapping, value: string) => {
    onChange({
      ...mapping,
      [field]: value,
    });
  };

  const isValid = Boolean(mapping.date && mapping.amount && mapping.title);

  return (
    <div data-testid="column-mapping-step" className="space-y-5">
      <div>
        <h4 className="font-semibold text-main flex items-center gap-2">
          <Table2 className="w-5 h-5 text-gold" />
          Map CSV Columns
        </h4>
        <p className="text-xs text-muted mt-1">
          Match your file headers to XakuFinance transaction fields.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 bg-[var(--surface-raised)] p-4 rounded-xl border border-[var(--border)]">
        <div>
          <label className="block text-xs font-medium text-main mb-1">
            Date Column <span className="text-gold">*</span>
          </label>
          <select
            data-testid="select-date-column"
            value={mapping.date}
            onChange={(e) => handleChange("date", e.target.value)}
            className="w-full bg-[var(--surface)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-main focus:outline-none focus:border-[var(--accent)]"
          >
            <option value="">Select column...</option>
            {headers.map((h) => (
              <option key={h} value={h}>
                {h}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-xs font-medium text-main mb-1">
            Amount Column <span className="text-gold">*</span>
          </label>
          <select
            data-testid="select-amount-column"
            value={mapping.amount}
            onChange={(e) => handleChange("amount", e.target.value)}
            className="w-full bg-[var(--surface)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-main focus:outline-none focus:border-[var(--accent)]"
          >
            <option value="">Select column...</option>
            {headers.map((h) => (
              <option key={h} value={h}>
                {h}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-xs font-medium text-main mb-1">
            Title / Description Column <span className="text-gold">*</span>
          </label>
          <select
            data-testid="select-title-column"
            value={mapping.title}
            onChange={(e) => handleChange("title", e.target.value)}
            className="w-full bg-[var(--surface)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-main focus:outline-none focus:border-[var(--accent)]"
          >
            <option value="">Select column...</option>
            {headers.map((h) => (
              <option key={h} value={h}>
                {h}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-xs font-medium text-main mb-1">
            Category Column (Optional)
          </label>
          <select
            data-testid="select-category-column"
            value={mapping.category || ""}
            onChange={(e) => handleChange("category", e.target.value)}
            className="w-full bg-[var(--surface)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-main focus:outline-none focus:border-[var(--accent)]"
          >
            <option value="">None (leave uncategorized)</option>
            {headers.map((h) => (
              <option key={h} value={h}>
                {h}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="flex items-center justify-between pt-4 border-t border-[var(--border)]">
        <button
          type="button"
          onClick={onBack}
          className="flex items-center gap-1.5 px-4 py-2 text-xs font-medium text-muted hover:text-main rounded-lg transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back
        </button>

        <button
          type="button"
          data-testid="mapping-next-btn"
          disabled={!isValid}
          onClick={onNext}
          className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg bg-[#F0B90B] text-black hover:bg-[#FCD535] transition-all disabled:opacity-40"
        >
          Proceed to Review
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
