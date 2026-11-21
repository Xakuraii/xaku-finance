import React from "react";
import { formatAmountOnly } from "@/lib/money";
import { formatDualAmount, useCurrency } from "@/lib/currency-context";

export interface MoneyProps {
  amountMinor: number;
  currency?: string;
  minorUnit?: number;
  showSign?: boolean;
  className?: string;
  colored?: boolean;
}

export const MoneyDisplay: React.FC<MoneyProps> = ({
  amountMinor,
  currency = "USD",
  minorUnit = 2,
  showSign = false,
  className = "",
  colored = false,
}) => {
  const { mode, usdToKhrRate, isProviderMounted } = useCurrency();
  const isPositive = amountMinor > 0;
  const isNegative = amountMinor < 0;

  let signStr = "";
  if (showSign) {
    if (isPositive) signStr = "+";
    else if (isNegative) signStr = "-";
  }

  const absAmount = Math.abs(amountMinor);
  const formatted = formatAmountOnly(absAmount, "en-US", minorUnit);

  let colorClass = "text-main";
  if (colored) {
    if (isPositive) colorClass = "text-positive";
    else if (isNegative) colorClass = "text-negative";
  }

  const majorValue = amountMinor / 10 ** minorUnit;
  const dual = formatDualAmount(majorValue, currency, mode, usdToKhrRate);

  let secondaryBadge: string | null = null;
  if (isProviderMounted) {
    if (mode === "BOTH") {
      secondaryBadge =
        currency.toUpperCase() === "KHR" ? dual.usdFormatted : dual.khrFormatted;
    } else if (mode === "KHR" && currency.toUpperCase() !== "KHR") {
      secondaryBadge = dual.khrFormatted;
    } else if (mode === "USD" && currency.toUpperCase() === "KHR") {
      secondaryBadge = dual.usdFormatted;
    }
  }

  return (
    <span className={`font-tabular inline-flex flex-wrap items-center gap-1.5 ${colorClass} ${className}`}>
      <span className="inline-flex items-center gap-1">
        <span>
          {signStr}
          {formatted}
        </span>
        <span className="text-muted text-xs tracking-wider font-normal">{currency}</span>
      </span>
      {secondaryBadge && (
        <span className="text-[11px] font-mono font-normal px-1.5 py-0.5 rounded bg-[var(--surface-raised)] border border-[var(--border)] text-[var(--text-muted)]">
          ≈ {secondaryBadge}
        </span>
      )}
    </span>
  );
};
