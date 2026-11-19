import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { LoginPage } from "./login-page";
import * as authContext from "../auth-context";

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe("LoginPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    mockNavigate.mockReset();
  });

  it("handles 2FA challenge and completes verification", async () => {
    const loginMock = vi.fn().mockResolvedValue({
      mfa_required: true,
      mfa_token: "challenge-token-xyz",
      methods: ["totp", "recovery_code"],
      expires_in: 300,
    });
    const complete2FAMock = vi.fn().mockResolvedValue(undefined);

    vi.spyOn(authContext, "useAuth").mockReturnValue({
      user: null,
      workspace: null,
      isAuthenticated: false,
      isLoading: false,
      login: loginMock,
      complete2FALogin: complete2FAMock,
      register: vi.fn(),
      logout: vi.fn(),
    });

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    // Initial password form
    const emailInput = screen.getByPlaceholderText("you@example.com");
    const passwordInput = screen.getByPlaceholderText("••••••••••••");
    fireEvent.change(emailInput, { target: { value: "test@example.com" } });
    fireEvent.change(passwordInput, { target: { value: "password123" } });

    const submitBtn = screen.getByRole("button", { name: "Sign In to Workspace" });
    fireEvent.click(submitBtn);

    // Should transition to 2FA challenge screen
    await waitFor(() => {
      expect(loginMock).toHaveBeenCalledWith("test@example.com", "password123");
      expect(screen.getByText("Two-Factor Verification")).toBeInTheDocument();
      expect(screen.getByPlaceholderText("123456")).toBeInTheDocument();
    });

    // Enter 2FA code
    const codeInput = screen.getByPlaceholderText("123456");
    fireEvent.change(codeInput, { target: { value: "654321" } });

    const verifyBtn = screen.getByRole("button", { name: "Verify & Continue" });
    fireEvent.click(verifyBtn);

    await waitFor(() => {
      expect(complete2FAMock).toHaveBeenCalledWith("challenge-token-xyz", "654321");
      expect(mockNavigate).toHaveBeenCalledWith("/app/accounts");
    });
  });
});
