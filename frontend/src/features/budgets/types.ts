export interface BudgetCategory {
  id: string;
  name: string;
  kind: string;
  icon?: string | null;
  color?: string | null;
}

export type HealthStatus = "on_track" | "warning" | "alert" | "over_budget";

export interface BudgetPeriod {
  id: string;
  period_start: string;
  period_end: string;
  base_amount_minor: number;
  base_amount: string;
  rollover_in_minor: number;
  rollover_in: string;
  spent_minor: number;
  spent: string;
  rollover_out_minor: number;
  rollover_out: string;
  total_available_minor: number;
  total_available: string;
  remaining_minor: number;
  remaining: string;
  spent_percentage: number;
  status: "open" | "closed";
  health_status: HealthStatus;
  computed_at?: string | null;
}

export interface Budget {
  id: string;
  name: string;
  category: BudgetCategory;
  currency: string;
  period_type: "monthly" | "weekly" | "custom";
  base_amount_minor: number;
  base_amount: string;
  rollover_enabled: boolean;
  rollover_cap_minor?: number | null;
  rollover_cap?: string | null;
  is_flexible: boolean;
  warn_at_percent: string;
  alert_at_percent: string;
  is_archived: boolean;
  starts_on: string;
  ends_on?: string | null;
  current_period?: BudgetPeriod | null;
  created_at: string;
  updated_at: string;
}

export interface BudgetOverviewItem {
  id: string;
  name: string;
  category: BudgetCategory;
  spent: string;
  spent_minor: number;
  total_available: string;
  total_available_minor: number;
  remaining: string;
  remaining_minor: number;
  spent_percentage: number;
  health_status: HealthStatus;
  is_flexible: boolean;
}

export interface BudgetOverview {
  currency: string;
  total_budgeted_minor: number;
  total_budgeted: string;
  total_spent_minor: number;
  total_spent: string;
  total_remaining_minor: number;
  total_remaining: string;
  budgets: BudgetOverviewItem[];
}

export interface CreateBudgetPayload {
  name: string;
  category_id: string;
  amount: string;
  currency: string;
  period_type?: "monthly" | "weekly" | "custom";
  rollover_enabled?: boolean;
  rollover_cap?: string | null;
  is_flexible?: boolean;
  warn_at_percent?: number;
  alert_at_percent?: number;
  starts_on?: string | null;
  ends_on?: string | null;
}
