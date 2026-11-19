import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { TwoFactorSetupDialog } from "./two-factor-setup-dialog";
import * as twoFactorApi from "../api/2fa-api";

describe("TwoFactorSetupDialog", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("completes full 2FA enrollment wizard through password, scan, and recovery codes", async () => {
    const reauthSpy = vi.spyOn(twoFactorApi, "reauth").mockResolvedValue({ reauth_expires_in: 600 });
    const setupSpy = vi.spyOn(twoFactorApi, "setupTwoFactor").mockResolvedValue({
      secret: "JBSWY3DPEHPK3PXP",
      otpauth_uri: "otpauth://totp/XakuFinance:alex@example.com?secret=JBSWY3DPEHPK3PXP",
      qr_svg: "<svg data-testid='qr-svg'></svg>",
    });
    const confirmSpy = vi.spyOn(twoFactorApi, "confirmTwoFactor").mockResolvedValue({
      enabled: true,
      recovery_codes: ["A1B2-C3D4", "E5F6-G7H8"],
    });

    const onSuccess = vi.fn();
    const onClose = vi.fn();

    render(
      <TwoFactorSetupDialog isOpen={true} onClose={onClose} onSuccess={onSuccess} />
    );

    // Step 1: Password confirmation
    expect(screen.getByText("Set Up Two-Factor Authentication")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("••••••••••••")).toBeInTheDocument();

    const passwordInput = screen.getByPlaceholderText("••••••••••••");
    fireEvent.change(passwordInput, { target: { value: "MySecretPass123" } });

    const continueBtn = screen.getByRole("button", { name: /continue/i });
    fireEvent.click(continueBtn);

    await waitFor(() => {
      expect(reauthSpy).toHaveBeenCalledWith("MySecretPass123");
      expect(setupSpy).toHaveBeenCalled();
      expect(screen.getByText("JBSWY3DPEHPK3PXP")).toBeInTheDocument();
    });

    // Step 2: Confirmation code
    const codeInput = screen.getByPlaceholderText("123456");
    fireEvent.change(codeInput, { target: { value: "654321" } });

    const enableBtn = screen.getByRole("button", { name: "Enable 2FA" });
    fireEvent.click(enableBtn);

    await waitFor(() => {
      expect(confirmSpy).toHaveBeenCalledWith("654321");
      expect(screen.getByText("Two-factor authentication is now active! Save your emergency recovery codes below.")).toBeInTheDocument();
      expect(screen.getByText("A1B2-C3D4")).toBeInTheDocument();
      expect(screen.getByText("E5F6-G7H8")).toBeInTheDocument();
    });

    // Step 3: Acknowledge & Done
    const doneBtn = screen.getByRole("button", { name: "Done & Return to Settings" });
    expect(doneBtn).toBeDisabled();

    const checkbox = screen.getByRole("checkbox");
    fireEvent.click(checkbox);
    expect(doneBtn).not.toBeDisabled();

    fireEvent.click(doneBtn);
    expect(onSuccess).toHaveBeenCalled();
    expect(onClose).toHaveBeenCalled();
  });
});
