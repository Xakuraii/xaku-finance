import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { DebtCard } from "./debt-card";
import { Liability } from "../api/debts-api";

const mockLiability: Liability = {
  id: "debt-1",
  name: "Auto Financing",
  liability_type: "personal_loan",
  currency: "USD",
  original_principal: "15000.00",
  original_principal_minor: 1500000,
  outstanding_principal: "9000.00",
  outstanding_principal_minor: 900000,
  paid_principal: "6000.00",
  paid_principal_minor: 600000,
  progress_percent: 40.0,
  interest_rate: "5.5000",
  interest_type: "simple",
  lender: "Ally Auto",
  due_day: 15,
  next_due_date: "2026-12-15",
  linked_account_id: "acc-1",
  linked_account_name: "Checking",
  ledger_account_id: "ledger-1",
  status: "active",
  is_archived: false,
  notes: null,
  created_at: "2026-11-18T00:00:00Z",
  updated_at: "2026-11-18T00:00:00Z",
};

describe("DebtCard", () => {
  const queryClient = new QueryClient();

  const renderComponent = (liability = mockLiability, onRepay = vi.fn()) => {
    return render(
      <QueryClientProvider client={queryClient}>
        <DebtCard liability={liability} onRepay={onRepay} />
      </QueryClientProvider>
    );
  };

  it("renders liability name, outstanding, original principal, and interest rate", () => {
    renderComponent();
    expect(screen.getByText("Auto Financing")).toBeInTheDocument();
    expect(screen.getByText("$9000.00")).toBeInTheDocument();
    expect(screen.getByText("$15000.00 USD")).toBeInTheDocument();
    expect(screen.getByText("5.5% APR")).toBeInTheDocument();
    expect(screen.getByText("Ally Auto")).toBeInTheDocument();
    expect(screen.getByText("40.0% repaid")).toBeInTheDocument();
  });

  it("shows paid off pill when outstanding is zero", () => {
    const paidOffLiability: Liability = {
      ...mockLiability,
      outstanding_principal: "0.00",
      outstanding_principal_minor: 0,
      paid_principal: "15000.00",
      paid_principal_minor: 1500000,
      progress_percent: 100.0,
      status: "paid_off",
    };
    renderComponent(paidOffLiability);
    expect(screen.getByTestId("paid-off-pill")).toBeInTheDocument();
    expect(screen.getByText("Paid Off")).toBeInTheDocument();
  });

  it("triggers onRepay when record repayment button is clicked", () => {
    const handleRepay = vi.fn();
    renderComponent(mockLiability, handleRepay);

    const btn = screen.getByTestId("repay-btn-debt-1");
    fireEvent.click(btn);
    expect(handleRepay).toHaveBeenCalledWith(mockLiability);
  });
});
