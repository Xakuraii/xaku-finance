import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { SplitEditor } from "./split-editor";

describe("SplitEditor", () => {
  it("blocks submit when splits do not sum to the total", async () => {
    render(
      <SplitEditor
        total={10000}
        currency="USD"
        value={[{ amount: 6000 }, { amount: 3900 }]}
        onChange={vi.fn()}
        onSave={vi.fn()}
      />
    );

    expect(screen.getByText(/1.00 USD unallocated/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /save transaction/i })).toBeDisabled();
  });

  it("enables submit when splits exactly equal the total", async () => {
    render(
      <SplitEditor
        total={10000}
        currency="USD"
        value={[{ amount: 6000 }, { amount: 4000 }]}
        onChange={vi.fn()}
        onSave={vi.fn()}
      />
    );

    expect(screen.queryByText(/unallocated/i)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /save transaction/i })).toBeEnabled();
  });
});
