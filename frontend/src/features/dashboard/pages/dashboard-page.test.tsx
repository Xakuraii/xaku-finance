import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { DashboardPage } from "./dashboard-page";
import * as dashboardApi from "../api/dashboard-api";

const mockDashboardData: dashboardApi.DashboardResponse = {
  period: {
    start: "2026-11-01",
    end: "2026-11-30",
    timezone: "UTC",
  },
  widget_order: [
    "total_balance",
    "net_worth",
    "safe_to_spend",
    "daily_allowance",
    "cash_flow",
    "budget_overview",
    "savings_progress",
    "recent_transactions",
    "spending_by_category",
  ],
  currency: "USD",
  balances: [{ currency: "USD", total: "2850.00" }],
  converted_total: {
    amount: "2850.00",
    currency: "USD",
    rate_policy: "period_end",
    rates_used: [],
  },
  net_worth: {
    amount: "2850.00",
    currency: "USD",
    assets: "2850.00",
    liabilities: "0.00",
    change: null,
    breakdown: { assets: [], liabilities: [] },
  },
  safe_to_spend: {
    display: "2850.00",
    raw: "2850.00",
    is_negative: false,
    currency: "USD",
    components: {
      spendable_cash: "2850.00",
      pending_outflows: "0.00",
      reserved_obligations: "0.00",
      planned_savings: "0.00",
    },
  },
  daily_allowance: {
    allowance: "45.00",
    remaining_days: 15,
    flexible_remaining: "675.00",
    currency: "USD",
    state: "ok",
    explanation: "675.00 USD remaining across 15 days.",
  },
  cash_flow: {
    table: [
      { item: "Operating Inflows", amount: "3000.00" },
      { item: "Operating Outflows", amount: "-150.00" },
      { item: "Net Cash Flow", amount: "2850.00" },
    ],
  },
  budget_overview: {
    state: "ok",
    items: [
      {
        id: "b-1",
        name: "Groceries Budget",
        category_name: "Groceries",
        spent: "150.00",
        base: "400.00",
        remaining: "250.00",
        percent_used: 37.5,
        is_over_budget: false,
        currency: "USD",
      },
    ],
  },
  savings_progress: {
    state: "ok",
    items: [
      {
        id: "g-1",
        name: "Vacation",
        target: "1000.00",
        contributed: "200.00",
        progress_percent: 20.0,
        target_date: "2027-05-01",
        currency: "USD",
      },
    ],
  },
  recent_transactions: {
    state: "ok",
    items: [
      {
        id: "tx-1",
        title: "Weekly Groceries",
        amount: "150.00",
        currency: "USD",
        account_name: "Main Checking",
        category_name: "Groceries",
        occurred_on: "2026-11-10",
        status: "completed",
      },
    ],
  },
  spending_by_category: {
    state: "ok",
    categories: [
      {
        category_name: "Groceries",
        amount: "150.00",
        percentage: 100.0,
      },
    ],
    total_spending: "150.00",
  },
};

const mockLayoutData = {
  widgets: [
    { key: "total_balance", title: "Account Balances", enabled: true },
    { key: "net_worth", title: "Net Worth", enabled: true },
    { key: "safe_to_spend", title: "Safe-to-Spend", enabled: true },
    { key: "daily_allowance", title: "Daily Allowance", enabled: true },
  ],
};

describe("DashboardPage", () => {
  it("renders financial dashboard and active widgets", async () => {
    vi.spyOn(dashboardApi, "fetchDashboard").mockResolvedValue(mockDashboardData);
    vi.spyOn(dashboardApi, "fetchDashboardLayout").mockResolvedValue(mockLayoutData);

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <DashboardPage />
        </MemoryRouter>
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Financial Dashboard")).toBeInTheDocument();
    });

    expect(screen.getByText("Account Balances")).toBeInTheDocument();
    expect(screen.getByText("Net Worth")).toBeInTheDocument();
    expect(screen.getByText("Safe-to-Spend")).toBeInTheDocument();
    expect(screen.getByText("Daily Allowance")).toBeInTheDocument();
    expect(screen.getByText("Period Cash Flow")).toBeInTheDocument();
    expect(screen.getByText("Budget Health")).toBeInTheDocument();
    expect(screen.getByText("Savings Goals")).toBeInTheDocument();
    expect(screen.getByText("Recent Transactions")).toBeInTheDocument();
  });

  it("opens customize layout modal when clicking customize button", async () => {
    vi.spyOn(dashboardApi, "fetchDashboard").mockResolvedValue(mockDashboardData);
    vi.spyOn(dashboardApi, "fetchDashboardLayout").mockResolvedValue(mockLayoutData);

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <DashboardPage />
        </MemoryRouter>
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Financial Dashboard")).toBeInTheDocument();
    });

    const customizeBtn = screen.getByRole("button", { name: /customize layout/i });
    fireEvent.click(customizeBtn);

    expect(screen.getByText("Customize Dashboard")).toBeInTheDocument();
    expect(screen.getByText("Reset to defaults")).toBeInTheDocument();
    expect(screen.getByText("Save Layout")).toBeInTheDocument();
  });
});
