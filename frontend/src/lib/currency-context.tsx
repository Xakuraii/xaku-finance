import React, { createContext, useContext, useEffect, useState } from "react";

export type CurrencyDisplayMode = "USD" | "KHR" | "BOTH";

export const DEFAULT_USD_TO_KHR = 4100;

export function parseNumeric(raw: string | number | undefined | null): number {
  if (typeof raw === "number") return Number.isFinite(raw) ? raw : 0;
  if (!raw) return 0;
  const cleaned = String(raw).replace(/[^0-9.-]/g, "");
  const parsed = parseFloat(cleaned);
  return Number.isFinite(parsed) ? parsed : 0;
}

export function convertMajorToUsdAndKhr(
  amount: number,
  sourceCurrency: string = "USD",
  rate: number = DEFAULT_USD_TO_KHR
): { usd: number; khr: number } {
  if (!Number.isFinite(amount)) {
    return { usd: 0, khr: 0 };
  }
  const safeRate = rate > 0 ? rate : DEFAULT_USD_TO_KHR;
  const code = (sourceCurrency || "USD").toUpperCase();

  if (code === "KHR") {
    return {
      usd: amount / safeRate,
      khr: amount,
    };
  }

  return {
    usd: amount,
    khr: amount * safeRate,
  };
}

export function formatUsd(usdAmount: number): string {
  const safe = Number.isFinite(usdAmount) ? usdAmount : 0;
  const abs = Math.abs(safe);
  const formatted = new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(abs);
  return `${safe < 0 ? "-" : ""}$${formatted}`;
}

export function formatKhr(khrAmount: number): string {
  const safe = Number.isFinite(khrAmount) ? khrAmount : 0;
  const abs = Math.round(Math.abs(safe));
  const formatted = new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 0,
  }).format(abs);
  return `${safe < 0 ? "-" : ""}${formatted} ៛`;
}

/**
 * Resolve exact Primary + Secondary currency readouts from USD & KHR sums/equivalents:
 * - KHR mode: Khmer Riel primary, US Dollar secondary
 * - BOTH mode: Combined USD primary, Combined Khmer Riel secondary
 * - USD mode: US Dollar primary, (optional KHR secondary only if explicitly requested or native KHR)
 */
export function resolveModeReadout(
  usdTotal: number,
  khrTotal: number,
  mode: CurrencyDisplayMode,
  options?: { sourceCurrency?: string; showSecondaryInUsd?: boolean }
): {
  primary: string;
  secondary: string | null;
  usdFormatted: string;
  khrFormatted: string;
} {
  const usdFormatted = formatUsd(usdTotal);
  const khrFormatted = formatKhr(khrTotal);
  const src = (options?.sourceCurrency || "USD").toUpperCase();

  if (mode === "KHR") {
    return {
      primary: khrFormatted,
      secondary: usdFormatted,
      usdFormatted,
      khrFormatted,
    };
  }

  if (mode === "BOTH") {
    return {
      primary: usdFormatted,
      secondary: khrFormatted,
      usdFormatted,
      khrFormatted,
    };
  }

  return {
    primary: usdFormatted,
    secondary: options?.showSecondaryInUsd || src === "KHR" ? khrFormatted : null,
    usdFormatted,
    khrFormatted,
  };
}

export function formatDualAmount(
  rawAmount: string | number,
  sourceCurrency: string = "USD",
  mode: CurrencyDisplayMode = "BOTH",
  rate: number = DEFAULT_USD_TO_KHR
): {
  primary: string;
  secondary: string | null;
  usdFormatted: string;
  khrFormatted: string;
} {
  const numeric = parseNumeric(rawAmount);
  const src = (sourceCurrency || "USD").toUpperCase();
  const { usd, khr } = convertMajorToUsdAndKhr(numeric, src, rate);
  return resolveModeReadout(usd, khr, mode, { sourceCurrency: src });
}

export interface CurrencyContextValue {
  mode: CurrencyDisplayMode;
  setMode: (mode: CurrencyDisplayMode) => void;
  usdToKhrRate: number;
  setUsdToKhrRate: (rate: number) => void;
  isProviderMounted: boolean;
}

const FALLBACK_CURRENCY_CONTEXT: CurrencyContextValue = {
  mode: "USD",
  setMode: () => {},
  usdToKhrRate: DEFAULT_USD_TO_KHR,
  setUsdToKhrRate: () => {},
  isProviderMounted: false,
};

const CurrencyContext = createContext<CurrencyContextValue>(FALLBACK_CURRENCY_CONTEXT);

const MODE_STORAGE_KEY = "xaku_currency_mode";
const RATE_STORAGE_KEY = "xaku_usd_khr_rate";

export const CurrencyProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [mode, setModeState] = useState<CurrencyDisplayMode>(() => {
    try {
      const saved = localStorage.getItem(MODE_STORAGE_KEY);
      if (saved === "USD" || saved === "KHR" || saved === "BOTH") {
        return saved;
      }
    } catch {
      // ignore storage errors
    }
    return "BOTH";
  });

  const [usdToKhrRate, setUsdToKhrRateState] = useState<number>(() => {
    try {
      const saved = localStorage.getItem(RATE_STORAGE_KEY);
      const parsed = saved ? parseFloat(saved) : NaN;
      if (Number.isFinite(parsed) && parsed > 0) {
        return parsed;
      }
    } catch {
      // ignore storage errors
    }
    return DEFAULT_USD_TO_KHR;
  });

  useEffect(() => {
    try {
      localStorage.setItem(MODE_STORAGE_KEY, mode);
    } catch {
      // ignore storage errors
    }
  }, [mode]);

  useEffect(() => {
    try {
      localStorage.setItem(RATE_STORAGE_KEY, String(usdToKhrRate));
    } catch {
      // ignore storage errors
    }
  }, [usdToKhrRate]);

  const setMode = (nextMode: CurrencyDisplayMode) => {
    setModeState(nextMode);
  };

  const setUsdToKhrRate = (nextRate: number) => {
    if (Number.isFinite(nextRate) && nextRate > 0) {
      setUsdToKhrRateState(nextRate);
    }
  };

  return (
    <CurrencyContext.Provider
      value={{
        mode,
        setMode,
        usdToKhrRate,
        setUsdToKhrRate,
        isProviderMounted: true,
      }}
    >
      {children}
    </CurrencyContext.Provider>
  );
};

export function useCurrency(): CurrencyContextValue {
  return useContext(CurrencyContext);
}
