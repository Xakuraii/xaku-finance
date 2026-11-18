import { api } from "@/lib/api/client";
import {
  NetWorthHistoryResponse,
  NetWorthResponse,
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
