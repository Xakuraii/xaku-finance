import { api } from "@/lib/api/client";

export type NotificationCategory =
  | "security"
  | "budget"
  | "bill"
  | "savings"
  | "report"
  | "system";

export type NotificationSeverity = "info" | "warning" | "critical";

export interface NotificationItem {
  id: string;
  category: NotificationCategory;
  severity: NotificationSeverity;
  title: string;
  body: string;
  data: Record<string, unknown>;
  dedupe_key: string;
  read_at: string | null;
  created_at: string;
}

export interface NotificationPreferenceItem {
  id: string;
  category: NotificationCategory;
  in_app: boolean;
  email: boolean;
  threshold_percent?: number;
  quiet_hours_start?: string | null;
  quiet_hours_end?: string | null;
  digest?: string;
  locked: boolean;
  updated_at: string;
}

export interface GetNotificationsParams {
  unread?: boolean;
  category?: string;
  limit?: number;
}

export async function getNotifications(
  params?: GetNotificationsParams
): Promise<NotificationItem[]> {
  const query = new URLSearchParams();
  if (params?.unread) query.set("unread", "true");
  if (params?.category) query.set("category", params.category);
  if (params?.limit) query.set("limit", params.limit.toString());

  const qs = query.toString();
  return api.get<NotificationItem[]>(`/api/v1/notifications/${qs ? `?${qs}` : ""}`);
}

export async function getUnreadCount(): Promise<{ unread_count: number }> {
  return api.get<{ unread_count: number }>("/api/v1/notifications/unread-count/");
}

export async function markNotificationRead(id: string): Promise<{ success: boolean }> {
  return api.post<{ success: boolean }>(`/api/v1/notifications/${id}/read/`, {});
}

export async function markAllNotificationsRead(): Promise<{ updated_count: number }> {
  return api.post<{ updated_count: number }>("/api/v1/notifications/read-all/", {});
}

export async function getNotificationPreferences(): Promise<NotificationPreferenceItem[]> {
  return api.get<NotificationPreferenceItem[]>("/api/v1/notification-preferences/");
}

export async function updateNotificationPreferences(
  preferences: Partial<NotificationPreferenceItem>[]
): Promise<NotificationPreferenceItem[]> {
  return api.put<NotificationPreferenceItem[]>("/api/v1/notification-preferences/", preferences);
}
