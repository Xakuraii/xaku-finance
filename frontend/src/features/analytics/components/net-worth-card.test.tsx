import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { NetWorthCard } from "./net-worth-card";
import { NetWorthResponse } from "../types";

const mockNetWorth: NetWorthResponse = {
  as_of: "2026-11-18",
  currency: "USD",
  assets: "7000.00",
  liabilities: "2000.00",
  net_worth: "5000.00",
  change: {
    amount: "500.00",
    since: "2026-10-31",
    direction: "up",
  },
  breakdown: {
    assets: [
      {
        account_id: "acc-1",
        name: "Main Checking",
        kind: "asset",
        currency: "USD",
        native_amount: "5000.00",
        amount: "5000.00",
      },
      {
        account_id: "acc-2",
        name: "Savings",
        kind: "asset",
        currency: "USD",
        native_amount: "2000.00",
        amount: "2000.00",
      },
    ],
    liabilities: [
      {
        liability_id: "liab-1",
        name: "Car Loan",
        kind: "liability",
        currency: "USD",
        native_amount: "2000.00",
        amount: "2000.00",
        outstanding: "2000.00",
      },
    ],
  },
  fx_effect: "0.00",
  rate_policy: "period_end",
  rates_used: [],
  ledger_seq: 42,
  computed_from: "ledger",
  conversion_unavailable: false,
};

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("NetWorthCard", () => {
  it("renders headline net worth, assets, liabilities and change", () => {
    renderWithClient(<NetWorthCard initialData={mockNetWorth} />);

    expect(screen.getByText("Net Worth")).toBeInTheDocument();
    expect(screen.getByText("5000.00")).toBeInTheDocument();
    expect(screen.getByText(/7000\.00/)).toBeInTheDocument();
    expect(screen.getByText(/2000\.00/)).toBeInTheDocument();
    expect(screen.getByText(/\+500\.00 USD/)).toBeInTheDocument();
    expect(screen.getByText(/since 2026-10-31/)).toBeInTheDocument();
  });

  it("toggles asset and liability breakdown drawer when clicked", () => {
    renderWithClient(<NetWorthCard initialData={mockNetWorth} />);

    const toggleButton = screen.getByRole("button", {
      name: /view asset & liability breakdown/i,
    });
    expect(toggleButton).toBeInTheDocument();

    // Initially breakdown items are hidden
    expect(screen.queryByText("Main Checking")).not.toBeInTheDocument();

    // Click toggle button
    fireEvent.click(toggleButton);

    // Now breakdown items are visible
    expect(screen.getByText("Main Checking")).toBeInTheDocument();
    expect(screen.getByText("Savings")).toBeInTheDocument();
    expect(screen.getByText("Car Loan")).toBeInTheDocument();
  });
});
