import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { NotificationBell } from "./notification-bell";
import * as notificationsApi from "../api/notifications-api";

const mockNotifications: notificationsApi.NotificationItem[] = [
  {
    id: "notif-1",
    category: "budget",
    severity: "warning",
    title: "Budget Warning: Groceries",
    body: "You have used 82% of your Groceries budget.",
    data: {},
    dedupe_key: "budget:1:80",
    read_at: null,
    created_at: "2026-11-18T10:00:00Z",
  },
  {
    id: "notif-2",
    category: "bill",
    severity: "info",
    title: "Upcoming Payment: Electric",
    body: "Electric bill is due in 2 days.",
    data: {},
    dedupe_key: "bill:2",
    read_at: "2026-11-18T09:00:00Z",
    created_at: "2026-11-18T08:00:00Z",
  },
];

describe("NotificationBell", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    vi.restoreAllMocks();
  });

  it("renders bell without badge when unread count is zero", async () => {
    vi.spyOn(notificationsApi, "getUnreadCount").mockResolvedValue({ unread_count: 0 });

    render(
      <QueryClientProvider client={queryClient}>
        <NotificationBell />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Notifications" })).toBeInTheDocument();
    });

    expect(screen.queryByTestId("notification-badge")).not.toBeInTheDocument();
  });

  it("displays unread count badge and accessible label when unread > 0", async () => {
    vi.spyOn(notificationsApi, "getUnreadCount").mockResolvedValue({ unread_count: 3 });

    render(
      <QueryClientProvider client={queryClient}>
        <NotificationBell />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: "3 unread notifications" })
      ).toBeInTheDocument();
    });

    const badge = screen.getByTestId("notification-badge");
    expect(badge).toHaveTextContent("3");
  });

  it("opens notification drawer when bell is clicked and displays notifications", async () => {
    vi.spyOn(notificationsApi, "getUnreadCount").mockResolvedValue({ unread_count: 1 });
    vi.spyOn(notificationsApi, "getNotifications").mockResolvedValue(mockNotifications);
    const markReadSpy = vi
      .spyOn(notificationsApi, "markNotificationRead")
      .mockResolvedValue({ success: true });

    render(
      <QueryClientProvider client={queryClient}>
        <NotificationBell />
      </QueryClientProvider>
    );

    const bellBtn = await screen.findByRole("button", { name: "1 unread notification" });
    fireEvent.click(bellBtn);

    await waitFor(() => {
      expect(screen.getByText("Notifications")).toBeInTheDocument();
      expect(screen.getByText("Budget Warning: Groceries")).toBeInTheDocument();
    });

    expect(screen.getByText("Upcoming Payment: Electric")).toBeInTheDocument();
    expect(screen.getByText("Mark read")).toBeInTheDocument();

    const markReadBtn = screen.getByText("Mark read");
    fireEvent.click(markReadBtn);

    await waitFor(() => {
      expect(markReadSpy).toHaveBeenCalledWith("notif-1");
    });
  });
});
