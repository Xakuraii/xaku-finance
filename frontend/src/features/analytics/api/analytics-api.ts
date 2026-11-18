import { api } from "@/lib/api/client";
import {
  DailyAllowanceResponse,
  NetWorthHistoryResponse,
  NetWorthResponse,
  RecurringObligation,
  SafeToSpendResponse,
  TagAnalyticsResponse,
} from "../types";

export interface AnalyticsFilterParams {
  from?: string;
  to?: string;
  currency?: string;
}

export async function fetchTagAnalytics(
  params?: AnalyticsFilterParams
): Promise<TagAnalyticsResponse> {
  const qp = new URLSearchParams();
  if (params?.from) qp.append("from", params.from);
  if (params?.to) qp.append("to", params.to);
  if (params?.currency) qp.append("currency", params.currency);

  const qs = qp.toString();
  const url = qs ? `/api/v1/tags/analytics/?${qs}` : "/api/v1/tags/analytics/";
  return api.get<TagAnalyticsResponse>(url);
}

export async function fetchNetWorth(params?: {
  as_of?: string;
  currency?: string;
}): Promise<NetWorthResponse> {
  const qp = new URLSearchParams();
  if (params?.as_of) qp.append("as_of", params.as_of);
  if (params?.currency) qp.append("currency", params.currency);

  const qs = qp.toString();
  const url = qs ? `/api/v1/net-worth/?${qs}` : "/api/v1/net-worth/";
  return api.get<NetWorthResponse>(url);
}

export async function fetchNetWorthHistory(params?: {
  from?: string;
  to?: string;
  granularity?: "month" | "week" | "day";
  currency?: string;
}): Promise<NetWorthHistoryResponse> {
  const qp = new URLSearchParams();
  if (params?.from) qp.append("from", params.from);
  if (params?.to) qp.append("to", params.to);
  if (params?.granularity) qp.append("granularity", params.granularity);
  if (params?.currency) qp.append("currency", params.currency);

  const qs = qp.toString();
  const url = qs ? `/api/v1/net-worth/history/?${qs}` : "/api/v1/net-worth/history/";
  return api.get<NetWorthHistoryResponse>(url);
}

export async function fetchSafeToSpend(params?: {
  horizon?: string;
  horizon_days?: number;
  currency?: string;
}): Promise<SafeToSpendResponse> {
  const qp = new URLSearchParams();
  if (params?.horizon) qp.append("horizon", params.horizon);
  if (params?.horizon_days) qp.append("horizon_days", String(params.horizon_days));
  if (params?.currency) qp.append("currency", params.currency);

  const qs = qp.toString();
  const url = qs ? `/api/v1/safe-to-spend/?${qs}` : "/api/v1/safe-to-spend/";
  return api.get<SafeToSpendResponse>(url);
}

export async function fetchDailyAllowance(params?: {
  period?: string;
  currency?: string;
}): Promise<DailyAllowanceResponse> {
  const qp = new URLSearchParams();
  if (params?.period) qp.append("period", params.period);
  if (params?.currency) qp.append("currency", params.currency);

  const qs = qp.toString();
  const url = qs ? `/api/v1/daily-allowance/?${qs}` : "/api/v1/daily-allowance/";
  return api.get<DailyAllowanceResponse>(url);
}

export async function fetchRecurringObligations(): Promise<RecurringObligation[]> {
  const res = await api.get<RecurringObligation[] | { results: RecurringObligation[] }>(
    "/api/v1/recurring-obligations/"
  );
  return Array.isArray(res) ? res : res.results;
}

export async function createRecurringObligation(
  payload: Partial<RecurringObligation> & { name: string; amount: string; next_due_date: string }
): Promise<RecurringObligation> {
  return api.post<RecurringObligation>("/api/v1/recurring-obligations/", payload);
}

export async function deleteRecurringObligation(id: string): Promise<void> {
  return api.delete(`/api/v1/recurring-obligations/${id}/`);
}
