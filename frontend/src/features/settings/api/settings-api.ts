import { api } from "@/lib/api/client";

export interface UserProfileData {
  id: string;
  email: string;
  is_email_verified: boolean;
  display_name: string;
  avatar_url: string;
  timezone: string;
  locale: string;
  reporting_currency: string;
  week_start: number;
  theme: "light" | "dark" | "system";
  created_at: string;
}

export interface WorkspaceSettingsData {
  id: string;
  name: string;
  reporting_currency: string;
  timezone: string;
  week_start: number;
  ledger_seq: number;
  created_at: string;
  updated_at: string;
}

export interface WorkspaceSummaryData {
  id: string;
  name: string;
  reporting_currency: string;
  timezone: string;
  week_start: number;
  ledger_seq: number;
  accounts_count: number;
  transactions_count: number;
  budgets_count: number;
  savings_goals_count: number;
  debts_count: number;
  created_at: string;
}

export async function getMe(): Promise<UserProfileData> {
  return api.get<UserProfileData>("/api/v1/me/");
}

export async function updateMe(
  payload: Partial<Omit<UserProfileData, "id" | "email" | "is_email_verified" | "created_at">>
): Promise<UserProfileData> {
  return api.patch<UserProfileData>("/api/v1/me/", payload);
}

export async function getWorkspaceSettings(): Promise<WorkspaceSettingsData> {
  return api.get<WorkspaceSettingsData>("/api/v1/workspace/");
}

export async function updateWorkspaceSettings(
  payload: Partial<Pick<WorkspaceSettingsData, "name" | "reporting_currency" | "timezone" | "week_start">>
): Promise<WorkspaceSettingsData> {
  return api.patch<WorkspaceSettingsData>("/api/v1/workspace/", payload);
}

export async function getWorkspaceSummary(): Promise<WorkspaceSummaryData> {
  return api.get<WorkspaceSummaryData>("/api/v1/workspace/summary/");
}
