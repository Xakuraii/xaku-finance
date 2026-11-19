import { api } from "@/lib/api/client";

export interface DataExportItem {
  id: string;
  scope: "all" | "transactions" | "accounts" | "budgets";
  format: "json" | "csv" | "zip";
  status: "pending" | "processing" | "completed" | "failed" | "cancelled";
  file_size_bytes: number;
  download_url: string | null;
  download_expires_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface DataMapCategory {
  category: string;
  description: string;
  purpose: string;
  lawful_basis: string;
  retention: string;
  shared_with_third_parties: boolean;
}

export interface DeletionRequestResponse {
  status: "requested" | "cancelled" | "executed";
  execute_after: string;
  backup_expiry_date: string;
  consequences: string[];
}

export async function getDataMap(): Promise<DataMapCategory[]> {
  return api.get<DataMapCategory[]>("/api/v1/privacy/data-map/");
}

export async function getExports(): Promise<DataExportItem[]> {
  return api.get<DataExportItem[]>("/api/v1/exports/");
}

export async function createExport(payload: {
  scope?: "all" | "transactions" | "accounts" | "budgets";
  format?: "json" | "csv" | "zip";
}): Promise<DataExportItem> {
  return api.post<DataExportItem>("/api/v1/exports/", payload);
}

export async function cancelExport(id: string): Promise<DataExportItem> {
  return api.post<DataExportItem>(`/api/v1/exports/${id}/cancel/`);
}

export async function requestAccountDeletion(payload: {
  password: string;
  confirm: string;
  code?: string;
}): Promise<DeletionRequestResponse> {
  return api.post<DeletionRequestResponse>("/api/v1/privacy/deletion-requests/", payload);
}

export async function getCurrentDeletionRequest(): Promise<DeletionRequestResponse | null> {
  try {
    return await api.get<DeletionRequestResponse>("/api/v1/privacy/deletion-requests/current/");
  } catch {
    return null;
  }
}

export async function cancelAccountDeletion(): Promise<void> {
  return api.delete<void>("/api/v1/privacy/deletion-requests/current/");
}
