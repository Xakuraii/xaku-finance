export interface TagAnalyticsItem {
  tag: string;
  amount_minor: number;
  amount: string;
  count: number;
  percentage: number;
}

export interface NecessityAnalyticsItem {
  necessity: "essential" | "important" | "lifestyle" | "unplanned";
  amount_minor: number;
  amount: string;
  count: number;
  percentage: number;
}

export interface TagAnalyticsResponse {
  currency: string;
  total_expense_minor: number;
  total_expense: string;
  by_tag: TagAnalyticsItem[];
  by_necessity: NecessityAnalyticsItem[];
}
