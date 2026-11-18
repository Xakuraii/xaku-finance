import { api } from "@/lib/api/client";
import {
  Budget,
  BudgetOverview,
  BudgetPeriod,
  CreateBudgetPayload,
} from "../types";

export async function fetchBudgets(): Promise<Budget[]> {
  return api.get<Budget[]>("/api/v1/budgets/");
}

export async function fetchBudgetOverview(currency?: string): Promise<BudgetOverview> {
  const url = currency
    ? `/api/v1/budgets/overview/?currency=${encodeURIComponent(currency)}`
    : "/api/v1/budgets/overview/";
  return api.get<BudgetOverview>(url);
}

export async function createBudget(payload: CreateBudgetPayload): Promise<Budget> {
  return api.post<Budget>("/api/v1/budgets/", payload);
}

export async function closeBudgetPeriod(
  budgetId: string
): Promise<{ closed_period: BudgetPeriod; next_period?: BudgetPeriod | null }> {
  return api.post<{ closed_period: BudgetPeriod; next_period?: BudgetPeriod | null }>(
    `/api/v1/budgets/${budgetId}/close_period/`
  );
}

export async function archiveBudget(budgetId: string): Promise<Budget> {
  return api.post<Budget>(`/api/v1/budgets/${budgetId}/archive/`);
}
