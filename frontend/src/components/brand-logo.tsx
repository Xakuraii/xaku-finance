import React from "react";
import { cn } from "@/lib/utils";

interface BrandLogoProps {
  iconClassName?: string;
  textClassName?: string;
  iconOnly?: boolean;
  className?: string;
}

/** Brand mark and XakuFinance wordmark using the public SVG logo. */
export const BrandLogo: React.FC<BrandLogoProps> = ({
  iconClassName,
  textClassName,
  iconOnly = false,
  className,
}) => (
  <span className={cn("inline-flex items-center gap-2.5", className)}>
    <img
      src="/XakuFinance.svg"
      alt="XakuFinance"
      className={cn("w-10 h-10 sm:w-12 sm:h-12 object-contain shrink-0", iconClassName)}
    />
    {!iconOnly && (
      <span
        className={cn(
          "font-display font-bold tracking-tight text-[var(--text)] leading-none text-xl",
          textClassName
        )}
      >
        Xaku<span className="text-[#d49b00] dark:text-[var(--accent)]">Finance</span>
      </span>
    )}
  </span>
);
