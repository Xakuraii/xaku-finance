import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BudgetCard } from "./budget-card";
import { Budget } from "../types";

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

const mockBudgetWithRollover: Budget = {
  id: "bdg-1",
  name: "Monthly Groceries",
  category: { id: "cat-1", name: "Groceries", kind: "expense" },
  currency: "USD",
  period_type: "monthly",
  base_amount_minor: 20000,
  base_amount: "200.00",
  rollover_enabled: true,
  rollover_cap_minor: null,
  rollover_cap: null,
  is_flexible: true,
  warn_at_percent: "80.00",
  alert_at_percent: "100.00",
  is_archived: false,
  starts_on: "2026-11-01",
  created_at: "2026-11-01T00:00:00Z",
  updated_at: "2026-11-01T00:00:00Z",
  current_period: {
    id: "per-1",
    period_start: "2026-11-01",
    period_end: "2026-11-30",
    base_amount_minor: 20000,
    base_amount: "200.00",
    rollover_in_minor: 6000,
    rollover_in: "60.00",
    spent_minor: 14000,
    spent: "140.00",
    rollover_out_minor: 0,
    rollover_out: "0.00",
    total_available_minor: 26000,
    total_available: "260.00",
    remaining_minor: 12000,
    remaining: "120.00",
    spent_percentage: 53.8,
    status: "open",
    health_status: "on_track",
  },
};

const mockOverBudget: Budget = {
  ...mockBudgetWithRollover,
  id: "bdg-2",
  name: "Dining Out",
  current_period: {
    ...mockBudgetWithRollover.current_period!,
    id: "per-2",
    spent_minor: 28000,
    spent: "280.00",
    remaining_minor: -2000,
    remaining: "-20.00",
    spent_percentage: 107.7,
    health_status: "over_budget",
  },
};

describe("BudgetCard", () => {
  it("renders budget progress, amounts, and rollover pill correctly", () => {
    renderWithClient(<BudgetCard budget={mockBudgetWithRollover} />);

    expect(screen.getByText("Monthly Groceries")).toBeInTheDocument();
    expect(screen.getByText("Groceries")).toBeInTheDocument();
    expect(screen.getByText("140.00")).toBeInTheDocument();
    expect(screen.getByText(/260.00 USD/i)).toBeInTheDocument();
    expect(screen.getByText(/120.00 USD left/i)).toBeInTheDocument();
    expect(screen.getByTestId("rollover-pill")).toBeInTheDocument();
    expect(screen.getByText(/\+60.00 USD rollover/i)).toBeInTheDocument();
    expect(screen.getByTestId("badge-on-track")).toBeInTheDocument();
  });

  it("renders over-budget warning and bar when actual exceeds available", () => {
    renderWithClient(<BudgetCard budget={mockOverBudget} />);

    expect(screen.getByText("Dining Out")).toBeInTheDocument();
    expect(screen.getByText("280.00")).toBeInTheDocument();
    expect(screen.getByText(/-20.00 USD over/i)).toBeInTheDocument();
    expect(screen.getByTestId("badge-over-budget")).toBeInTheDocument();
  });
});
