import { api } from "@/lib/api/client";

export interface EmergencyFundStatus {
  target_months: number;
  designated_account_id: string | null;
  designated_account_name: string | null;
  designated_goal_id: string | null;
  designated_goal_name: string | null;
  is_override: boolean;
  monthly_essential_expense: string;
  monthly_essential_expense_minor: number;
  computed_monthly_expense: string;
  computed_monthly_expense_minor: number;
  override_monthly_expense: string | null;
  target_amount: string;
  target_amount_minor: number;
  current_savings: string;
  current_savings_minor: number;
  remaining_target: string;
  remaining_target_minor: number;
  progress_percent: number;
  currency: string;
  has_earmark_conflict: boolean;
  conflict_details: string | null;
  lookback_days: number;
}

export interface EmergencyFundConfigPayload {
  target_months?: number;
  designated_account_id?: string | null;
  designated_goal_id?: string | null;
  monthly_expense_override?: string | null;
  clear_override?: boolean;
}

export interface EmergencyFundProjection {
  target_amount_minor: number;
  current_savings_minor: number;
  remaining_target_minor: number;
  monthly_contribution_minor: number;
  currency: string;
  months_to_target: number | null;
  days_to_target: number | null;
  projected_completion_date: string | null;
}

export async function getEmergencyFundStatus(): Promise<EmergencyFundStatus> {
  return api.get<EmergencyFundStatus>("/emergency-fund/");
}

export async function updateEmergencyFundConfig(
  payload: EmergencyFundConfigPayload
): Promise<EmergencyFundStatus> {
  return api.patch<EmergencyFundStatus>("/emergency-fund/", payload);
}

export async function getEmergencyFundProjection(
  monthlyContribution: string
): Promise<EmergencyFundProjection> {
  return api.post<EmergencyFundProjection>("/emergency-fund/projection/", {
    monthly_contribution: monthlyContribution,
  });
}
