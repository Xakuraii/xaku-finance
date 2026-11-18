import { api } from "@/lib/api/client";
import {
  CreateTransactionInput,
  Transaction,
  TransactionAudit,
  UpdateTransactionInput,
} from "./types";

export interface TransactionFilters {
  account_id?: string;
  category_id?: string;
  status?: string;
  from?: string;
  to?: string;
  tag?: string;
  q?: string;
  include_archived?: boolean;
}

export interface PaginatedResponse<T> {
  results: T[];
  next_cursor: string | null;
  has_more: boolean;
}

export async function getTransactions(
  filters: TransactionFilters = {}
): Promise<PaginatedResponse<Transaction>> {
  const params = new URLSearchParams();
  if (filters.account_id) params.set("account_id", filters.account_id);
  if (filters.category_id) params.set("category_id", filters.category_id);
  if (filters.status) params.set("status", filters.status);
  if (filters.from) params.set("from", filters.from);
  if (filters.to) params.set("to", filters.to);
  if (filters.tag) params.set("tag", filters.tag);
  if (filters.q) params.set("q", filters.q);
  if (filters.include_archived) params.set("include_archived", "true");

  const queryStr = params.toString() ? `?${params.toString()}` : "";
  return api.get<PaginatedResponse<Transaction>>(`/api/v1/transactions/${queryStr}`);
}

export async function getTransaction(id: string): Promise<Transaction> {
  return api.get<Transaction>(`/api/v1/transactions/${id}/`);
}

export async function createTransaction(data: CreateTransactionInput): Promise<Transaction> {
  return api.post<Transaction>("/api/v1/transactions/", data);
}

export async function updateTransaction(
  id: string,
  data: UpdateTransactionInput
): Promise<Transaction> {
  return api.patch<Transaction>(`/api/v1/transactions/${id}/`, data);
}

export async function archiveTransaction(
  id: string,
  reason: string
): Promise<Transaction> {
  return api.post<Transaction>(`/api/v1/transactions/${id}/archive/`, { reason });
}

export async function restoreTransaction(id: string): Promise<Transaction> {
  return api.post<Transaction>(`/api/v1/transactions/${id}/restore/`);
}

export async function getTransactionAudit(id: string): Promise<TransactionAudit[]> {
  return api.get<TransactionAudit[]>(`/api/v1/transactions/${id}/audit/`);
}
