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

// ==========================================
// Safe-to-Spend & Daily Allowance Types
// ==========================================

export interface SafeToSpendHorizon {
  start: string;
  end: string;
  label: string;
}

export interface SafeToSpendComponents {
  spendable_balance: string;
  pending_outflows: string;
  reserved_bills: string;
  planned_savings: string;
}

export interface SafeToSpendAccount {
  id: string;
  name: string;
  included: boolean;
  balance: string;
  reason: string;
}

export interface SafeToSpendExcludedAccount {
  id: string;
  name: string;
  reason: string;
}

export interface SafeToSpendResponse {
  currency: string;
  display: string;
  raw: string;
  is_negative: boolean;
  horizon: SafeToSpendHorizon;
  components: SafeToSpendComponents;
  accounts: SafeToSpendAccount[];
  excluded_accounts: SafeToSpendExcludedAccount[];
  notes: string[];
}

export interface DailyAllowanceBudgetItem {
  id: string;
  name: string;
  remaining: string;
  flexible?: boolean;
  reason?: string;
}

export interface DailyAllowanceResponse {
  currency: string;
  period: {
    start: string;
    end: string;
    timezone: string;
  };
  remaining_days: number;
  flexible_remaining: string;
  allowance: string;
  state: "ok" | "over_budget" | "period_ended";
  explanation: string;
  budgets: DailyAllowanceBudgetItem[];
  excluded: DailyAllowanceBudgetItem[];
}

export interface RecurringObligation {
  id: string;
  name: string;
  kind: "bill" | "subscription" | "reserved" | "savings_plan";
  amount_minor: number;
  amount: string;
  currency_code: string;
  account?: string | null;
  category?: string | null;
  cadence: "weekly" | "monthly" | "quarterly" | "yearly" | "one_off";
  next_due_date: string;
  is_reserved: boolean;
  auto_post: boolean;
  is_active: boolean;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}
