import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { TransferDialog } from "./transfer-dialog";
import { Account } from "@/features/accounts/types";

const mockAccounts: Account[] = [
  {
    id: "acc-1",
    name: "Primary Checking",
    account_type: "checking",
    currency: "USD",
    nature: "asset",
    balance_minor: 100000,
    balance: "1000.00",
    balance_display: "$1,000.00",
    is_spendable: true,
    allows_negative_balance: false,
    display_order: 0,
    opened_on: "2026-11-01",
    is_archived: false,
    created_at: "2026-11-01T00:00:00Z",
    updated_at: "2026-11-01T00:00:00Z",
  },
  {
    id: "acc-2",
    name: "Savings KHR",
    account_type: "savings",
    currency: "KHR",
    nature: "asset",
    balance_minor: 0,
    balance: "0.00",
    balance_display: "0.00 ៛",
    is_spendable: false,
    allows_negative_balance: false,
    display_order: 1,
    opened_on: "2026-11-01",
    is_archived: false,
    created_at: "2026-11-01T00:00:00Z",
    updated_at: "2026-11-01T00:00:00Z",
  },
];

const renderWithClient = (ui: React.ReactElement) => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  );
};

describe("TransferDialog", () => {
  it("renders transfer form when open", () => {
    renderWithClient(
      <TransferDialog
        open={true}
        onOpenChange={vi.fn()}
        accounts={mockAccounts}
      />
    );

    expect(screen.getByText("Internal Account Transfer")).toBeInTheDocument();
    expect(screen.getByText("From Account")).toBeInTheDocument();
    expect(screen.getByText("To Account")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Execute Transfer" })).toBeInTheDocument();
  });

  it("displays currency conversion inputs when accounts have different currencies", () => {
    renderWithClient(
      <TransferDialog
        open={true}
        onOpenChange={vi.fn()}
        accounts={mockAccounts}
      />
    );

    // Initial state has acc-1 (USD) and acc-2 (KHR) selected
    expect(
      screen.getByText(/Currency Conversion \(USD → KHR\)/)
    ).toBeInTheDocument();
    expect(screen.getByPlaceholderText("4050.00")).toBeInTheDocument();
  });

  it("shows error if transfer amount is zero or negative", () => {
    renderWithClient(
      <TransferDialog
        open={true}
        onOpenChange={vi.fn()}
        accounts={mockAccounts}
      />
    );

    const amountInput = screen.getByPlaceholderText("100.00");
    fireEvent.change(amountInput, { target: { value: "0" } });

    const submitBtn = screen.getByRole("button", { name: "Execute Transfer" });
    fireEvent.click(submitBtn);

    expect(
      screen.getByText("Transfer amount must be greater than zero.")
    ).toBeInTheDocument();
  });
});
