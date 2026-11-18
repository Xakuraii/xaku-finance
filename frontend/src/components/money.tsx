import React from "react";
import { formatAmountOnly } from "@/lib/money";

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

  return (
    <span className={`font-tabular inline-flex items-center gap-1 ${colorClass} ${className}`}>
      <span>
        {signStr}
        {formatted}
      </span>
      <span className="text-muted text-xs tracking-wider font-normal">{currency}</span>
    </span>
  );
};
