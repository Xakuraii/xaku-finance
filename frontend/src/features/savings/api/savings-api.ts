import { api } from "@/lib/api/client";

export interface SavingsAllocation {
  id: string;
  account_id: string;
  account_name: string;
  allocated_minor: number;
  allocated_amount: string;
  currency_code: string;
}

export interface SavingsGoal {
  id: string;
  name: string;
  target_amount: string;
  target_amount_minor: number;
  currency: string;
  target_date: string | null;
  linked_account_id: string | null;
  linked_account_name: string | null;
  strategy: "linked_account" | "earmark";
  status: "active" | "achieved" | "paused" | "archived";
  notes: string | null;
  is_archived: boolean;
  achieved_at: string | null;
  current_amount: string;
  current_amount_minor: number;
  progress_percent: number;
  is_overfunded: boolean;
  overfunded_amount_minor: number;
  unallocated_capacity: number;
  allocations: SavingsAllocation[];
  created_at: string;
  updated_at: string;
}

export interface CreateSavingsGoalPayload {
  name: string;
  target_amount: string;
  currency: string;
  target_date?: string | null;
  linked_account_id?: string | null;
  strategy?: "linked_account" | "earmark";
  notes?: string | null;
}

export interface SavingsContribution {
  id: string;
  goal_id: string;
  goal_name: string;
  account_id: string;
  account_name: string;
  transfer_transaction_id: string | null;
  kind: "transfer_in" | "earmark" | "adjustment" | "withdrawal";
  amount: string;
  amount_minor: number;
  currency: string;
  occurred_on: string;
  note: string | null;
  created_at: string;
}

export interface RecordContributionPayload {
  kind: "transfer_in" | "earmark" | "adjustment" | "withdrawal";
  amount: string;
  account_id: string;
  transfer_transaction_id?: string | null;
  occurred_on?: string | null;
  note?: string | null;
}

export interface GoalProjection {
  goal_id: string;
  currency: string;
  target_amount_minor: number;
  current_amount_minor: number;
  remaining_amount_minor: number;
  target_date: string | null;
  days_remaining: number | null;
  months_remaining: number | null;
  required_monthly_contribution: string | null;
  projected_completion_date: string | null;
}

export async function fetchSavingsGoals(includeArchived = false): Promise<SavingsGoal[]> {
  const url = includeArchived
    ? "/api/v1/savings-goals/?include_archived=true"
    : "/api/v1/savings-goals/";
  return await api.get<SavingsGoal[]>(url);
}

export async function createSavingsGoal(payload: CreateSavingsGoalPayload): Promise<SavingsGoal> {
  return await api.post<SavingsGoal>("/api/v1/savings-goals/", payload);
}

export async function updateSavingsGoal(
  id: string,
  payload: Partial<CreateSavingsGoalPayload> & { status?: string }
): Promise<SavingsGoal> {
  return await api.patch<SavingsGoal>(`/api/v1/savings-goals/${id}/`, payload);
}

export async function archiveSavingsGoal(id: string): Promise<SavingsGoal> {
  return await api.post<SavingsGoal>(`/api/v1/savings-goals/${id}/archive/`);
}

export async function restoreSavingsGoal(id: string): Promise<SavingsGoal> {
  return await api.post<SavingsGoal>(`/api/v1/savings-goals/${id}/restore/`);
}

export async function fetchSavingsContributions(goalId: string): Promise<SavingsContribution[]> {
  return await api.get<SavingsContribution[]>(`/api/v1/savings-goals/${goalId}/contributions/`);
}

export async function recordSavingsContribution(
  goalId: string,
  payload: RecordContributionPayload
): Promise<SavingsContribution> {
  return await api.post<SavingsContribution>(
    `/api/v1/savings-goals/${goalId}/contributions/`,
    payload
  );
}

export async function fetchSavingsProjection(goalId: string): Promise<GoalProjection> {
  return await api.get<GoalProjection>(`/api/v1/savings-goals/${goalId}/projection/`);
}
