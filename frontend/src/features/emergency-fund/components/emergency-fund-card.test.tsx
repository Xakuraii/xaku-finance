import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { EmergencyFundCard } from "./emergency-fund-card";
import { EmergencyFundStatus } from "../api/emergency-fund-api";

const mockStatus: EmergencyFundStatus = {
  target_months: 6,
  designated_account_id: "acc-1",
  designated_account_name: "Safety Stash",
  designated_goal_id: null,
  designated_goal_name: null,
  is_override: false,
  monthly_essential_expense: "300.00",
  monthly_essential_expense_minor: 30000,
  computed_monthly_expense: "300.00",
  computed_monthly_expense_minor: 30000,
  override_monthly_expense: null,
  target_amount: "1800.00",
  target_amount_minor: 180000,
  current_savings: "1200.00",
  current_savings_minor: 120000,
  remaining_target: "600.00",
  remaining_target_minor: 60000,
  progress_percent: 66.7,
  currency: "USD",
  has_earmark_conflict: false,
  conflict_details: null,
  lookback_days: 90,
};

describe("EmergencyFundCard", () => {
  it("renders target, current savings, and progress", () => {
    const onConfigure = vi.fn();
    render(<EmergencyFundCard status={mockStatus} onConfigure={onConfigure} />);

    expect(screen.getByText("Emergency Fund Safety Net")).toBeInTheDocument();
    expect(screen.getByText("$1200.00")).toBeInTheDocument();
    expect(screen.getByText("of $1800.00 target")).toBeInTheDocument();
    expect(screen.getByText("66.7%")).toBeInTheDocument();
    expect(screen.getByText("Remaining needed: $600.00")).toBeInTheDocument();
    expect(screen.getByTestId("expense-source-badge")).toHaveTextContent("90-Day Lookback");
  });

  it("displays manual override badge when is_override is true", () => {
    const overrideStatus: EmergencyFundStatus = {
      ...mockStatus,
      is_override: true,
      override_monthly_expense: "400.00",
      monthly_essential_expense: "400.00",
    };
    render(<EmergencyFundCard status={overrideStatus} onConfigure={vi.fn()} />);

    expect(screen.getByTestId("expense-source-badge")).toHaveTextContent("Manual Override");
  });

  it("shows conflict alert when has_earmark_conflict is true", () => {
    const conflictStatus: EmergencyFundStatus = {
      ...mockStatus,
      has_earmark_conflict: true,
      conflict_details: "Designated account has $1500.00 earmarked to other goals.",
    };
    render(<EmergencyFundCard status={conflictStatus} onConfigure={vi.fn()} />);

    expect(screen.getByTestId("conflict-alert")).toBeInTheDocument();
    expect(
      screen.getByText(/Designated account has \$1500\.00 earmarked to other goals\./)
    ).toBeInTheDocument();
  });

  it("calls onConfigure when configure button is clicked", () => {
    const onConfigure = vi.fn();
    render(<EmergencyFundCard status={mockStatus} onConfigure={onConfigure} />);

    const configBtn = screen.getByRole("button", { name: /Configure/i });
    fireEvent.click(configBtn);
    expect(onConfigure).toHaveBeenCalledTimes(1);
  });
});
