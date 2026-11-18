/**
 * Client-side Money handling according to XakuFinance design specification.
 * Amounts are strictly formatted; no arithmetic is done in the frontend.
 */

export interface ParseSuccess {
  ok: true;
  amountMinor: number;
  serialized: string;
}

export interface ParseError {
  ok: false;
  reason: "invalid" | "precision" | "negative";
}

export type ParseMoneyResult = ParseSuccess | ParseError;

export function parseMoneyInput(input: string, minorUnit: number = 2): ParseMoneyResult {
  const trimmed = input.trim();
  if (!trimmed) {
    return { ok: false, reason: "invalid" };
  }

  // Check negative
  if (trimmed.startsWith("-")) {
    return { ok: false, reason: "negative" };
  }

  const parts = trimmed.split(".");
  if (parts.length > 2) {
    return { ok: false, reason: "invalid" };
  }

  const wholeStr = parts[0].replace(/,/g, "");
  if (!/^\d+$/.test(wholeStr)) {
    return { ok: false, reason: "invalid" };
  }

  let fractionStr = parts[1] || "";
  if (fractionStr.length > minorUnit) {
    return { ok: false, reason: "precision" };
  }

  if (fractionStr && !/^\d+$/.test(fractionStr)) {
    return { ok: false, reason: "invalid" };
  }

  // Pad fraction with zeroes to minorUnit
  const paddedFraction = fractionStr.padEnd(minorUnit, "0");
  const amountMinor = parseInt(wholeStr, 10) * 10 ** minorUnit + parseInt(paddedFraction || "0", 10);
  const serialized = `${wholeStr}.${paddedFraction}`;

  return {
    ok: true,
    amountMinor,
    serialized,
  };
}

export function formatMoney(
  amountMinor: number,
  currency: string = "USD",
  locale: string = "en-US",
  minorUnit: number = 2
): string {
  const divisor = 10 ** minorUnit;
  const major = amountMinor / divisor;

  const formattedNumber = new Intl.NumberFormat(locale, {
    minimumFractionDigits: minorUnit,
    maximumFractionDigits: minorUnit,
  }).format(major);

  return `${formattedNumber} ${currency}`;
}

export function formatAmountOnly(
  amountMinor: number,
  locale: string = "en-US",
  minorUnit: number = 2
): string {
  const divisor = 10 ** minorUnit;
  const major = amountMinor / divisor;

  return new Intl.NumberFormat(locale, {
    minimumFractionDigits: minorUnit,
    maximumFractionDigits: minorUnit,
  }).format(major);
}
