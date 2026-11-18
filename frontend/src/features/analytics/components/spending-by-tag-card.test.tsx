import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SpendingByTagCard } from "./spending-by-tag-card";
import { TagAnalyticsResponse } from "../types";

const mockData: TagAnalyticsResponse = {
  currency: "USD",
  total_expense_minor: 20000,
  total_expense: "200.00",
  by_tag: [
    { tag: "home", amount_minor: 15000, amount: "150.00", count: 2, percentage: 75.0 },
    { tag: "work", amount_minor: 5000, amount: "50.00", count: 1, percentage: 25.0 },
  ],
  by_necessity: [
    { necessity: "essential", amount_minor: 10000, amount: "100.00", count: 1, percentage: 50.0 },
    { necessity: "lifestyle", amount_minor: 5000, amount: "50.00", count: 1, percentage: 25.0 },
    { necessity: "important", amount_minor: 5000, amount: "50.00", count: 1, percentage: 25.0 },
  ],
};

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("SpendingByTagCard", () => {
  it("renders tag breakdowns correctly with minor unit formatting", () => {
    renderWithClient(<SpendingByTagCard initialData={mockData} />);

    expect(screen.getByText(/Spending Intelligence/i)).toBeInTheDocument();
    expect(screen.getByText(/200\.00 USD/)).toBeInTheDocument();
    expect(screen.getByText("home")).toBeInTheDocument();
    expect(screen.getByText(/150\.00 USD/)).toBeInTheDocument();
    expect(screen.getByText("work")).toBeInTheDocument();
    expect(screen.getByText(/^50\.00 USD/)).toBeInTheDocument();
  });

  it("switches to necessity view when clicking the Necessity tab", () => {
    renderWithClient(<SpendingByTagCard initialData={mockData} />);

    const necessityTab = screen.getByRole("button", { name: /necessity/i });
    fireEvent.click(necessityTab);

    expect(screen.getByText(/Essential/i)).toBeInTheDocument();
    expect(screen.getByText(/Lifestyle/i)).toBeInTheDocument();
    expect(screen.getByText(/Important/i)).toBeInTheDocument();
    expect(screen.getByText(/100.00 USD/i)).toBeInTheDocument();
  });
});
