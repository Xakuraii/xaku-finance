import { api } from "@/lib/api/client";

export interface WidgetLayoutItem {
  key: string;
  title: string;
  enabled: boolean;
}

export interface DashboardBalanceItem {
  currency: string;
  total: string;
}

export interface DashboardConvertedTotal {
  amount: string;
  currency: string;
  rate_policy: string;
  rates_used: Array<{ pair: string; rate: string; date: string }>;
}

export interface DashboardResponse {
  period: {
    start: string;
    end: string;
    timezone: string;
  };
  widget_order: string[];
  currency: string;
  balances?: DashboardBalanceItem[];
  converted_total?: DashboardConvertedTotal;
  net_worth?: {
    amount: string;
    currency: string;
    assets: string;
    liabilities: string;
    change?: {
      amount: string;
      direction: string;
      percent: number;
    } | null;
    breakdown: {
      assets: Array<{ name: string; amount: string; currency: string }>;
      liabilities: Array<{ name: string; amount: string; currency: string }>;
    };
  };
  safe_to_spend?: {
    display: string;
    raw: string;
    is_negative: boolean;
    currency: string;
    components: {
      spendable_cash: string;
      pending_outflows: string;
      reserved_obligations: string;
      planned_savings: string;
    };
    notes?: string[];
  };
  daily_allowance?: {
    allowance: string;
    remaining_days: number;
    flexible_remaining: string;
    currency: string;
    state: "ok" | "over_budget";
    explanation: string;
  };
  cash_flow?: {
    inflows?: string;
    outflows?: string;
    net_cash_flow?: string;
    table?: Array<{ item: string; amount: string }>;
  };
  budget_overview?: {
    state: string;
    reason?: string;
    items: Array<{
      id: string;
      name: string;
      category_name: string | null;
      spent: string;
      base: string;
      remaining: string;
      percent_used: number;
      is_over_budget: boolean;
      currency: string;
    }>;
  };
  savings_progress?: {
    state: string;
    reason?: string;
    items: Array<{
      id: string;
      name: string;
      target: string;
      contributed: string;
      progress_percent: number;
      target_date: string | null;
      currency: string;
    }>;
  };
  recent_transactions?: {
    state: string;
    reason?: string;
    items: Array<{
      id: string;
      title: string;
      amount: string;
      currency: string;
      account_name: string | null;
      category_name: string | null;
      occurred_on: string;
      status: string;
    }>;
  };
  spending_by_category?: {
    state: string;
    reason?: string;
    categories: Array<{
      category_name: string;
      amount: string;
      percentage: number;
    }>;
    total_spending?: string;
  };
}

export async function fetchDashboard(params?: {
  period?: string;
  start?: string;
  end?: string;
  currency?: string;
  as_of?: string;
}): Promise<DashboardResponse> {
  const qp = new URLSearchParams();
  if (params?.period) qp.append("period", params.period);
  if (params?.start) qp.append("start", params.start);
  if (params?.end) qp.append("end", params.end);
  if (params?.currency) qp.append("currency", params.currency);
  if (params?.as_of) qp.append("as_of", params.as_of);

  const qs = qp.toString();
  const url = qs ? `/api/v1/dashboard/?${qs}` : "/api/v1/dashboard/";
  return api.get<DashboardResponse>(url);
}

export async function fetchDashboardLayout(): Promise<{ widgets: WidgetLayoutItem[] }> {
  return api.get<{ widgets: WidgetLayoutItem[] }>("/api/v1/dashboard/layout/");
}

export async function saveDashboardLayout(
  widgets: WidgetLayoutItem[]
): Promise<{ widgets: WidgetLayoutItem[] }> {
  return api.put<{ widgets: WidgetLayoutItem[] }>("/api/v1/dashboard/layout/", { widgets });
}

export async function resetDashboardLayout(): Promise<{ widgets: WidgetLayoutItem[] }> {
  return api.post<{ widgets: WidgetLayoutItem[] }>("/api/v1/dashboard/layout/reset/", {});
}
