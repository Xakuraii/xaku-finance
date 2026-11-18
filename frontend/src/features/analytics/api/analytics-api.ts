import { api } from "@/lib/api/client";
import { TagAnalyticsResponse } from "../types";

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
