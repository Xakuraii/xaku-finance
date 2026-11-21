import React from "react";
import { formatAmountOnly } from "@/lib/money";
import {
  convertMajorToUsdAndKhr,
  formatKhr,
  formatUsd,
  useCurrency,
} from "@/lib/currency-context";

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

  const majorSigned = amountMinor / 10 ** minorUnit;
  const { usd, khr } = convertMajorToUsdAndKhr(Math.abs(majorSigned), currency, usdToKhrRate);
  const usdStr = `${signStr}${formatUsd(usd)}`;
  const khrStr = `${signStr}${formatKhr(khr)}`;

  if (isProviderMounted) {
    if (mode === "KHR") {
      return (
        <span className={`font-tabular inline-flex flex-wrap items-center gap-1.5 ${colorClass} ${className}`}>
          <span>{khrStr}</span>
          <span className="text-[11px] font-mono font-normal px-1.5 py-0.5 rounded bg-[var(--surface-raised)] border border-[var(--border)] text-[var(--text-muted)]">
            {usdStr}
          </span>
        </span>
      );
    }

    if (mode === "BOTH") {
      return (
        <span className={`font-tabular inline-flex flex-wrap items-center gap-1.5 ${colorClass} ${className}`}>
          <span>{usdStr}</span>
          <span className="text-[11px] font-mono font-normal px-1.5 py-0.5 rounded bg-[var(--surface-raised)] border border-[var(--border)] text-[var(--text-muted)]">
            {khrStr}
          </span>
        </span>
      );
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
      {isProviderMounted && mode === "USD" && currency.toUpperCase() === "KHR" && (
        <span className="text-[11px] font-mono font-normal px-1.5 py-0.5 rounded bg-[var(--surface-raised)] border border-[var(--border)] text-[var(--text-muted)]">
          ≈ {usdStr}
        </span>
      )}
    </span>
  );
};
