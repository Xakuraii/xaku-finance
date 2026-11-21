import React, { createContext, useContext, useEffect, useState } from "react";

export type CurrencyDisplayMode = "USD" | "KHR" | "BOTH";

export const DEFAULT_USD_TO_KHR = 4100;

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
  const numeric =
    typeof rawAmount === "number"
      ? rawAmount
      : parseFloat(String(rawAmount || "0").replace(/,/g, "")) || 0;
  const src = (sourceCurrency || "USD").toUpperCase();
  const { usd, khr } = convertMajorToUsdAndKhr(numeric, src, rate);
  const usdFormatted = formatUsd(usd);
  const khrFormatted = formatKhr(khr);

  if (mode === "KHR") {
    return {
      primary: khrFormatted,
      secondary: src === "USD" ? usdFormatted : null,
      usdFormatted,
      khrFormatted,
    };
  }

  if (mode === "BOTH") {
    return {
      primary: src === "KHR" ? khrFormatted : usdFormatted,
      secondary: src === "KHR" ? usdFormatted : khrFormatted,
      usdFormatted,
      khrFormatted,
    };
  }

  return {
    primary: usdFormatted,
    secondary: src === "KHR" ? khrFormatted : null,
    usdFormatted,
    khrFormatted,
  };
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
