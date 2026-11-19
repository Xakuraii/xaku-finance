import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { DataExportDialog } from "./data-export-dialog";
import * as twoFactorApi from "@/features/auth/api/2fa-api";
import * as privacyApi from "../api/privacy-api";

describe("DataExportDialog", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("handles password reauth, scope selection, and export job creation", async () => {
    const reauthSpy = vi.spyOn(twoFactorApi, "reauth").mockResolvedValue({ reauth_expires_in: 600 });
    const createExportSpy = vi.spyOn(privacyApi, "createExport").mockResolvedValue({
      id: "job-123",
      scope: "all",
      format: "json",
      status: "completed",
      file_size_bytes: 4096,
      download_url: "/api/v1/exports/job-123/download/",
      download_expires_at: "2026-11-20T00:00:00Z",
      completed_at: "2026-11-19T00:00:00Z",
      created_at: "2026-11-19T00:00:00Z",
    });

    const onSuccess = vi.fn();
    const onClose = vi.fn();

    render(<DataExportDialog isOpen={true} onClose={onClose} onSuccess={onSuccess} />);

    // Step 1: Reauth
    expect(screen.getByText("Export Workspace Data")).toBeInTheDocument();
    const passwordInput = screen.getByPlaceholderText("••••••••••••");
    fireEvent.change(passwordInput, { target: { value: "password123" } });

    const continueBtn = screen.getByRole("button", { name: /continue/i });
    fireEvent.click(continueBtn);

    await waitFor(() => {
      expect(reauthSpy).toHaveBeenCalledWith("password123");
      expect(screen.getByText("Export Scope")).toBeInTheDocument();
    });

    // Step 2: Trigger export
    const generateBtn = screen.getByRole("button", { name: "Generate & Download" });
    fireEvent.click(generateBtn);

    await waitFor(() => {
      expect(createExportSpy).toHaveBeenCalledWith({ scope: "all", format: "json" });
      expect(screen.getByText("Your export archive has been generated successfully!")).toBeInTheDocument();
      expect(screen.getByText("Download Archive File")).toBeInTheDocument();
    });

    expect(onSuccess).toHaveBeenCalled();
  });
});
