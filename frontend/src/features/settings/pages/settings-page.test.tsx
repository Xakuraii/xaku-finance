import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { SettingsPage } from "./settings-page";
import * as settingsApi from "../api/settings-api";
import * as notificationsApi from "@/features/notifications/api/notifications-api";

const mockMe: settingsApi.UserProfileData = {
  id: "user-1",
  email: "alex@example.com",
  is_email_verified: true,
  display_name: "Alex Trader",
  avatar_url: "",
  timezone: "UTC",
  locale: "en-US",
  reporting_currency: "USD",
  week_start: 1,
  theme: "system",
  created_at: "2026-11-01T00:00:00Z",
};

const mockWs: settingsApi.WorkspaceSettingsData = {
  id: "ws-1",
  name: "Alex Wealth Holdings",
  reporting_currency: "USD",
  timezone: "UTC",
  week_start: 1,
  ledger_seq: 142,
  created_at: "2026-11-01T00:00:00Z",
  updated_at: "2026-11-18T12:00:00Z",
};

const mockSummary: settingsApi.WorkspaceSummaryData = {
  id: "ws-1",
  name: "Alex Wealth Holdings",
  reporting_currency: "USD",
  timezone: "UTC",
  week_start: 1,
  ledger_seq: 142,
  accounts_count: 4,
  transactions_count: 58,
  budgets_count: 5,
  savings_goals_count: 2,
  debts_count: 1,
  created_at: "2026-11-01T00:00:00Z",
};

const mockPrefs: notificationsApi.NotificationPreferenceItem[] = [
  {
    id: "pref-1",
    category: "security",
    in_app: true,
    email: true,
    locked: true,
    updated_at: "2026-11-01T00:00:00Z",
  },
  {
    id: "pref-2",
    category: "budget",
    in_app: true,
    email: false,
    locked: false,
    updated_at: "2026-11-01T00:00:00Z",
  },
];

describe("SettingsPage", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    vi.restoreAllMocks();
  });

  it("renders profile settings and saves updates", async () => {
    vi.spyOn(settingsApi, "getMe").mockResolvedValue(mockMe);
    vi.spyOn(settingsApi, "getWorkspaceSettings").mockResolvedValue(mockWs);
    vi.spyOn(settingsApi, "getWorkspaceSummary").mockResolvedValue(mockSummary);
    vi.spyOn(notificationsApi, "getNotificationPreferences").mockResolvedValue(mockPrefs);
    const updateMeSpy = vi
      .spyOn(settingsApi, "updateMe")
      .mockResolvedValue({ ...mockMe, display_name: "Alex Pro" });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <SettingsPage />
        </MemoryRouter>
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Settings & Preferences")).toBeInTheDocument();
      expect(screen.getByDisplayValue("Alex Trader")).toBeInTheDocument();
    });

    const nameInput = screen.getByDisplayValue("Alex Trader");
    fireEvent.change(nameInput, { target: { value: "Alex Pro" } });

    const saveBtn = screen.getByRole("button", { name: /save profile/i });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(updateMeSpy).toHaveBeenCalled();
    });
  });

  it("switches to workspace tab and displays diagnostics", async () => {
    vi.spyOn(settingsApi, "getMe").mockResolvedValue(mockMe);
    vi.spyOn(settingsApi, "getWorkspaceSettings").mockResolvedValue(mockWs);
    vi.spyOn(settingsApi, "getWorkspaceSummary").mockResolvedValue(mockSummary);
    vi.spyOn(notificationsApi, "getNotificationPreferences").mockResolvedValue(mockPrefs);

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <SettingsPage />
        </MemoryRouter>
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Settings & Preferences")).toBeInTheDocument();
    });

    const wsTab = screen.getByRole("button", { name: "Workspace" });
    fireEvent.click(wsTab);

    await waitFor(() => {
      expect(screen.getByText("Workspace Configuration")).toBeInTheDocument();
      expect(screen.getByDisplayValue("Alex Wealth Holdings")).toBeInTheDocument();
      expect(screen.getByText("Workspace Diagnostics")).toBeInTheDocument();
    });

    expect(screen.getByText("142")).toBeInTheDocument(); // ledger sequence
  });

  it("switches to notifications tab and displays preference toggles", async () => {
    vi.spyOn(settingsApi, "getMe").mockResolvedValue(mockMe);
    vi.spyOn(settingsApi, "getWorkspaceSettings").mockResolvedValue(mockWs);
    vi.spyOn(settingsApi, "getWorkspaceSummary").mockResolvedValue(mockSummary);
    vi.spyOn(notificationsApi, "getNotificationPreferences").mockResolvedValue(mockPrefs);

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <SettingsPage />
        </MemoryRouter>
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Settings & Preferences")).toBeInTheDocument();
    });

    const notifTab = screen.getByRole("button", { name: "Notifications" });
    fireEvent.click(notifTab);

    await waitFor(() => {
      expect(screen.getByText("Delivery Channels")).toBeInTheDocument();
      expect(screen.getByText("Security notifications are locked to active")).toBeInTheDocument();
    });
  });

  it("switches to security tab and displays two-factor settings", async () => {
    vi.spyOn(settingsApi, "getMe").mockResolvedValue({
      ...mockMe,
      two_factor_enabled: false,
    });
    vi.spyOn(settingsApi, "getWorkspaceSettings").mockResolvedValue(mockWs);
    vi.spyOn(settingsApi, "getWorkspaceSummary").mockResolvedValue(mockSummary);
    vi.spyOn(notificationsApi, "getNotificationPreferences").mockResolvedValue(mockPrefs);

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <SettingsPage />
        </MemoryRouter>
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Settings & Preferences")).toBeInTheDocument();
    });

    const secTab = screen.getByRole("button", { name: "Security" });
    fireEvent.click(secTab);

    await waitFor(() => {
      expect(screen.getByText("Two-Factor Authentication (TOTP)")).toBeInTheDocument();
      expect(screen.getByText("Enable Two-Factor Authentication")).toBeInTheDocument();
      expect(screen.getByText("Disabled")).toBeInTheDocument();
    });
  });

  it("switches to privacy tab and displays export and transparency map", async () => {
    vi.spyOn(settingsApi, "getMe").mockResolvedValue(mockMe);
    vi.spyOn(settingsApi, "getWorkspaceSettings").mockResolvedValue(mockWs);
    vi.spyOn(settingsApi, "getWorkspaceSummary").mockResolvedValue(mockSummary);
    vi.spyOn(notificationsApi, "getNotificationPreferences").mockResolvedValue(mockPrefs);

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <SettingsPage />
        </MemoryRouter>
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Settings & Preferences")).toBeInTheDocument();
    });

    const privTab = screen.getByRole("button", { name: "Privacy & Data" });
    fireEvent.click(privTab);

    await waitFor(() => {
      expect(screen.getByText("Data Export & Portability")).toBeInTheDocument();
      expect(screen.getByText("Data Transparency Map")).toBeInTheDocument();
      expect(screen.getByText("Danger Zone: Account Deletion")).toBeInTheDocument();
    });
  });
});
