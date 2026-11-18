import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReportsView } from "./reports-view";
import { ReportResponse } from "../types";

const mockReport: ReportResponse = {
  period: { start: "2026-11-01", end: "2026-11-30" },
  currency: "USD",
  totals: {
    income: "3000.00",
    expense: "500.00",
    net: "2500.00",
  },
  series: [
    { period: "2026-11", income: "3000.00", expense: "500.00", net: "2500.00" },
  ],
  table: [
    { period: "2026-11", income: "3000.00", expense: "500.00", net: "2500.00" },
  ],
  rate_policy: "transaction_date",
  rates_used: [],
  generated_from: "ledger",
  reconciliation: {
    ledger_income: "3000.00",
    reported_income: "3000.00",
    difference: "0.00",
    ledger_expense: "500.00",
    reported_expense: "500.00",
    checked_at: "2026-11-18T12:00:00Z",
  },
};

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("ReportsView", () => {
  it("renders statement controls and ledger reconciliation banner", () => {
    renderWithClient(<ReportsView initialData={mockReport} />);

    expect(screen.getByText("Income vs Expense")).toBeInTheDocument();
    expect(screen.getByText("Cash Flow Statement")).toBeInTheDocument();
    expect(screen.getByText("Category Breakdown")).toBeInTheDocument();
    expect(screen.getByText(/Double-Entry Ledger Integrity:/i)).toBeInTheDocument();
    expect(screen.getByText(/difference: 0\.00 USD/i)).toBeInTheDocument();
  });
});
