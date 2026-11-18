import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ColumnMappingStep } from "./column-mapping-step";
import { ColumnMapping } from "../types";

describe("ColumnMappingStep", () => {
  const headers = ["TxnDate", "TxnAmount", "Payee", "Notes"];

  it("disables the next button when required fields are unmapped", () => {
    const mapping: ColumnMapping = { date: "", amount: "", title: "" };
    render(
      <ColumnMappingStep
        headers={headers}
        mapping={mapping}
        onChange={vi.fn()}
        onNext={vi.fn()}
        onBack={vi.fn()}
      />
    );

    const nextBtn = screen.getByTestId("mapping-next-btn");
    expect(nextBtn).toBeDisabled();
  });

  it("enables the next button when all required fields are mapped", () => {
    const mapping: ColumnMapping = {
      date: "TxnDate",
      amount: "TxnAmount",
      title: "Payee",
    };
    render(
      <ColumnMappingStep
        headers={headers}
        mapping={mapping}
        onChange={vi.fn()}
        onNext={vi.fn()}
        onBack={vi.fn()}
      />
    );

    const nextBtn = screen.getByTestId("mapping-next-btn");
    expect(nextBtn).toBeEnabled();
  });

  it("calls onChange when a column dropdown is changed", () => {
    const onChange = vi.fn();
    const mapping: ColumnMapping = { date: "", amount: "", title: "" };

    render(
      <ColumnMappingStep
        headers={headers}
        mapping={mapping}
        onChange={onChange}
        onNext={vi.fn()}
        onBack={vi.fn()}
      />
    );

    const dateSelect = screen.getByTestId("select-date-column");
    fireEvent.change(dateSelect, { target: { value: "TxnDate" } });

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ date: "TxnDate" })
    );
  });
});
