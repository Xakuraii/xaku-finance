import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { AccountDeletionDialog } from "./account-deletion-dialog";
import * as privacyApi from "../api/privacy-api";

describe("AccountDeletionDialog", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("requires typing DELETE and password to schedule deletion", async () => {
    const deleteSpy = vi.spyOn(privacyApi, "requestAccountDeletion").mockResolvedValue({
      status: "requested",
      execute_after: "2026-11-26T00:00:00Z",
      backup_expiry_date: "2026-12-26",
      consequences: ["All accounts permanently deleted"],
    });

    const onSuccess = vi.fn();
    const onClose = vi.fn();

    render(
      <AccountDeletionDialog
        isOpen={true}
        onClose={onClose}
        onSuccess={onSuccess}
        twoFactorEnabled={false}
      />
    );

    expect(screen.getByText("Request Account Deletion")).toBeInTheDocument();
    expect(screen.getAllByText(/7-day grace period/i).length).toBeGreaterThan(0);

    const passwordInput = screen.getByPlaceholderText("••••••••••••");
    const confirmInput = screen.getByPlaceholderText("DELETE");
    const submitBtn = screen.getByRole("button", { name: "Schedule Account Deletion" });

    // Disabled initially
    expect(submitBtn).toBeDisabled();

    fireEvent.change(passwordInput, { target: { value: "password123" } });
    fireEvent.change(confirmInput, { target: { value: "DELETE" } });

    expect(submitBtn).not.toBeDisabled();
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(deleteSpy).toHaveBeenCalledWith({
        password: "password123",
        confirm: "DELETE",
        code: undefined,
      });
      expect(onSuccess).toHaveBeenCalled();
      expect(onClose).toHaveBeenCalled();
    });
  });
});
