import { api } from "@/lib/api/client";
import { Account, CreateAccountInput } from "./types";

export async function getAccounts(includeArchived: boolean = false): Promise<Account[]> {
  const url = includeArchived ? "/api/v1/accounts/?include_archived=true" : "/api/v1/accounts/";
  return api.get<Account[]>(url);
}

export async function getAccount(id: string): Promise<Account> {
  return api.get<Account>(`/api/v1/accounts/${id}/`);
}

export async function createAccount(data: CreateAccountInput): Promise<Account> {
  return api.post<Account>("/api/v1/accounts/", data);
}

export async function archiveAccount(
  id: string,
  data: { reason: string; acknowledge_balance?: boolean }
): Promise<Account> {
  return api.post<Account>(`/api/v1/accounts/${id}/archive/`, data);
}

export async function restoreAccount(id: string): Promise<Account> {
  return api.post<Account>(`/api/v1/accounts/${id}/restore/`);
}
