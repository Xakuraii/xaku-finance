import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SavingsGoalCard } from "./savings-goal-card";
import { SavingsGoal } from "../api/savings-api";

const mockGoal: SavingsGoal = {
  id: "goal-1",
  name: "Japan Vacation",
  target_amount: "3000.00",
  target_amount_minor: 300000,
  currency: "USD",
  target_date: "2027-06-01",
  linked_account_id: "acc-1",
  linked_account_name: "Checking",
  strategy: "linked_account",
  status: "active",
  notes: "Tokyo & Kyoto",
  is_archived: false,
  achieved_at: null,
  current_amount: "1500.00",
  current_amount_minor: 150000,
  progress_percent: 50.0,
  is_overfunded: false,
  overfunded_amount_minor: 0,
  unallocated_capacity: 100000,
  allocations: [],
  created_at: "2026-11-18T00:00:00Z",
  updated_at: "2026-11-18T00:00:00Z",
};

describe("SavingsGoalCard", () => {
  const queryClient = new QueryClient();

  const renderComponent = (goal = mockGoal, onContribute = vi.fn()) => {
    return render(
      <QueryClientProvider client={queryClient}>
        <SavingsGoalCard goal={goal} onContribute={onContribute} />
      </QueryClientProvider>
    );
  };

  it("renders goal name, target, and current progress", () => {
    renderComponent();
    expect(screen.getByText("Japan Vacation")).toBeInTheDocument();
    expect(screen.getByText("1500.00")).toBeInTheDocument();
    expect(screen.getByText("Target: 3000.00 USD")).toBeInTheDocument();
    expect(screen.getByText("50.0% funded")).toBeInTheDocument();
    expect(screen.getByText("Capacity: $1000.00 available")).toBeInTheDocument();
  });

  it("shows overfunded pill when is_overfunded is true", () => {
    const overfundedGoal: SavingsGoal = {
      ...mockGoal,
      current_amount: "3500.00",
      current_amount_minor: 350000,
      progress_percent: 100.0,
      is_overfunded: true,
      overfunded_amount_minor: 50000,
    };
    renderComponent(overfundedGoal);
    expect(screen.getByTestId("overfunded-pill")).toBeInTheDocument();
    expect(screen.getByText("+500.00 Over")).toBeInTheDocument();
  });

  it("triggers onContribute when contribute button is clicked", () => {
    const handleContribute = vi.fn();
    renderComponent(mockGoal, handleContribute);

    const btn = screen.getByTestId("contribute-btn-goal-1");
    fireEvent.click(btn);
    expect(handleContribute).toHaveBeenCalledWith(mockGoal);
  });
});
