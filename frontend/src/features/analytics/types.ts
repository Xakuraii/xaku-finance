export interface TagAnalyticsItem {
  tag: string;
  amount_minor: number;
  amount: string;
  count: number;
  percentage: number;
}

export interface NecessityAnalyticsItem {
  necessity: "essential" | "important" | "lifestyle" | "unplanned";
  amount_minor: number;
  amount: string;
  count: number;
  percentage: number;
}

export interface TagAnalyticsResponse {
  currency: string;
  total_expense_minor: number;
  total_expense: string;
  by_tag: TagAnalyticsItem[];
  by_necessity: NecessityAnalyticsItem[];
}

// ==========================================
// Net Worth Types
// ==========================================

export interface NetWorthRateUsed {
  pair: string;
  rate: string;
  date: string;
}

export interface NetWorthChange {
  amount: string;
  since: string;
  direction: "up" | "down" | "flat";
}

export interface NetWorthBreakdownItem {
  account_id?: string | null;
  liability_id?: string | null;
  name: string;
  kind: "asset" | "liability";
  currency: string;
  native_amount: string;
  amount: string;
  outstanding?: string | null;
}

export interface NetWorthBreakdown {
  assets: NetWorthBreakdownItem[];
  liabilities: NetWorthBreakdownItem[];
}

export interface NetWorthResponse {
  as_of: string;
  currency: string;
  assets: string;
  liabilities: string;
  net_worth: string;
  change: NetWorthChange | null;
  breakdown: NetWorthBreakdown;
  fx_effect: string;
  rate_policy: string;
  rates_used: NetWorthRateUsed[];
  ledger_seq: number;
  computed_from: "ledger" | "snapshot";
  conversion_unavailable: boolean;
}

export interface NetWorthHistoryPoint {
  date: string;
  assets: string;
  liabilities: string;
  net_worth: string;
  stale: boolean;
}

export interface NetWorthHistoryResponse {
  currency: string;
  from: string;
  to: string;
  granularity: "month" | "week" | "day";
  series: NetWorthHistoryPoint[];
  table: Array<{
    date: string;
    assets: string;
    liabilities: string;
    net_worth: string;
  }>;
}
