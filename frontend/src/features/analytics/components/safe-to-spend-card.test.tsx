import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SafeToSpendCard } from "./safe-to-spend-card";
import { SafeToSpendResponse } from "../types";

const mockSTS: SafeToSpendResponse = {
  currency: "USD",
  display: "1000.00",
  raw: "1000.00",
  is_negative: false,
  horizon: {
    start: "2026-11-18",
    end: "2026-11-30",
    label: "to end of month",
  },
  components: {
    spendable_balance: "2000.00",
    pending_outflows: "-200.00",
    reserved_bills: "-300.00",
    planned_savings: "-500.00",
  },
  accounts: [
    {
      id: "acc-1",
      name: "Main Checking",
      included: true,
      balance: "2000.00",
      reason: "spendable",
    },
  ],
  excluded_accounts: [
    {
      id: "acc-2",
      name: "Emergency Savings",
      reason: "not_spendable",
    },
  ],
  notes: ["Pending transactions are not yet deducted from balances."],
};

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("SafeToSpendCard", () => {
  it("renders headline figure and 4-part equation components", () => {
    renderWithClient(<SafeToSpendCard initialData={mockSTS} />);

    expect(screen.getByText("Safe-to-Spend")).toBeInTheDocument();
    expect(screen.getByText("1000.00")).toBeInTheDocument();
    expect(screen.getByText("2000.00")).toBeInTheDocument();
    expect(screen.getByText("-200.00")).toBeInTheDocument();
    expect(screen.getByText("-300.00")).toBeInTheDocument();
    expect(screen.getByText("-500.00")).toBeInTheDocument();
  });

  it("toggles accounts drawer when clicking details button", () => {
    renderWithClient(<SafeToSpendCard initialData={mockSTS} />);

    const btn = screen.getByRole("button", {
      name: /how this is calculated & account inclusion/i,
    });
    expect(screen.queryByText("Main Checking")).not.toBeInTheDocument();

    fireEvent.click(btn);

    expect(screen.getByText("Main Checking")).toBeInTheDocument();
    expect(screen.getByText("Emergency Savings")).toBeInTheDocument();
    expect(
      screen.getByText(/Pending transactions are not yet deducted from balances/i)
    ).toBeInTheDocument();
  });
});
