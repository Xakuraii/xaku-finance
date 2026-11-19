import React, { useState } from "react";
import { createExport, DataExportItem } from "../api/privacy-api";
import { reauth } from "@/features/auth/api/2fa-api";
import { Download, AlertCircle, X, ArrowRight, Check } from "lucide-react";
import { ApiError } from "@/lib/api/client";

interface DataExportDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const DataExportDialog: React.FC<DataExportDialogProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [step, setStep] = useState<"auth" | "options" | "success">("auth");
  const [password, setPassword] = useState("");
  const [scope, setScope] = useState<"all" | "transactions" | "accounts" | "budgets">("all");
  const [format, setFormat] = useState<"json" | "csv">("json");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [completedJob, setCompletedJob] = useState<DataExportItem | null>(null);

  if (!isOpen) return null;

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);
    try {
      await reauth(password);
      setStep("options");
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Failed to verify password. Please try again.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleExportSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);
    try {
      const job = await createExport({ scope, format });
      setCompletedJob(job);
      setStep("success");
      onSuccess();
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Failed to generate export. Please try again.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 overflow-y-auto">
      <div className="w-full max-w-md rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6 shadow-2xl relative transition-all">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-muted hover:text-main hover:bg-[var(--surface-raised)] transition-colors"
          aria-label="Close"
        >
          <X className="w-4 h-4" />
        </button>

        <div className="flex items-center gap-3 mb-5">
          <div className="p-2.5 rounded-xl bg-gold/10 border border-gold/30 text-gold">
            <Download className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-main">Export Workspace Data</h2>
            <p className="text-xs text-muted">Generate a complete portable archive of your financial records</p>
          </div>
        </div>

        {error && (
          <div className="mb-4 flex items-center gap-2 rounded-xl bg-red-500/10 border border-red-500/20 p-3 text-xs text-negative">
            <AlertCircle className="w-4 h-4 shrink-0 text-negative" />
            <span>{error}</span>
          </div>
        )}

        {step === "auth" && (
          <form onSubmit={handlePasswordSubmit} className="space-y-4">
            <p className="text-xs text-muted leading-relaxed">
              For your privacy, exporting workspace data requires recent password confirmation.
            </p>
            <div>
              <label className="block text-xs font-medium text-muted mb-1">Account Password</label>
              <input
                type="password"
                required
                autoFocus
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full rounded-lg bg-[var(--surface-raised)] border border-[var(--border)] px-3 py-2 text-sm text-main focus:border-[var(--accent)] focus:outline-none transition-colors"
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="px-3.5 py-2 rounded-xl border border-[var(--border)] text-xs font-medium text-main hover:bg-[var(--surface-raised)] transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isLoading || !password}
                className="px-4 py-2 rounded-xl bg-gold text-xs font-semibold text-black hover:opacity-90 transition-opacity flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
              >
                {isLoading ? "Verifying..." : "Continue"}
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </form>
        )}

        {step === "options" && (
          <form onSubmit={handleExportSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-muted mb-1">Export Scope</label>
              <select
                value={scope}
                onChange={(e) => setScope(e.target.value as any)}
                className="w-full rounded-lg bg-[var(--surface-raised)] border border-[var(--border)] px-3 py-2 text-sm text-main focus:border-[var(--accent)] focus:outline-none transition-colors"
              >
                <option value="all">All Data (Accounts, Transactions, Budgets, Goals, Debts)</option>
                <option value="transactions">Transactions Only</option>
                <option value="accounts">Accounts Only</option>
                <option value="budgets">Budgets Only</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-muted mb-1">Format</label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setFormat("json")}
                  className={`p-3 rounded-xl border text-left transition-colors cursor-pointer ${
                    format === "json"
                      ? "border-gold bg-gold/5 text-main font-medium"
                      : "border-[var(--border)] bg-[var(--surface-raised)] text-muted hover:text-main"
                  }`}
                >
                  <div className="font-semibold text-xs text-main">JSON</div>
                  <div className="text-[11px] text-muted">Complete nested data with metadata</div>
                </button>

                <button
                  type="button"
                  onClick={() => setFormat("csv")}
                  className={`p-3 rounded-xl border text-left transition-colors cursor-pointer ${
                    format === "csv"
                      ? "border-gold bg-gold/5 text-main font-medium"
                      : "border-[var(--border)] bg-[var(--surface-raised)] text-muted hover:text-main"
                  }`}
                >
                  <div className="font-semibold text-xs text-main">CSV</div>
                  <div className="text-[11px] text-muted">Tabular spreadsheet compatible</div>
                </button>
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="px-3.5 py-2 rounded-xl border border-[var(--border)] text-xs font-medium text-main hover:bg-[var(--surface-raised)] transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isLoading}
                className="px-4 py-2 rounded-xl bg-gold text-xs font-semibold text-black hover:opacity-90 transition-opacity flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
              >
                {isLoading ? "Generating Export..." : "Generate & Download"}
              </button>
            </div>
          </form>
        )}

        {step === "success" && completedJob && (
          <div className="space-y-4">
            <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs flex items-center gap-2">
              <Check className="w-4 h-4 shrink-0" />
              <span>Your export archive has been generated successfully!</span>
            </div>

            <div className="p-3 rounded-xl bg-[var(--surface-raised)] border border-[var(--border)] space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-muted">Scope:</span>
                <span className="font-semibold text-main capitalize">{completedJob.scope}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted">Format:</span>
                <span className="font-semibold text-main uppercase">{completedJob.format}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted">Size:</span>
                <span className="font-mono text-main">{(completedJob.file_size_bytes / 1024).toFixed(1)} KB</span>
              </div>
            </div>

            {completedJob.download_url && (
              <a
                href={completedJob.download_url}
                download
                className="w-full py-2.5 rounded-xl bg-gold text-xs font-semibold text-black hover:opacity-90 transition-opacity flex items-center justify-center gap-2"
              >
                <Download className="w-4 h-4" />
                <span>Download Archive File</span>
              </a>
            )}

            <button
              type="button"
              onClick={onClose}
              className="w-full py-2 rounded-xl border border-[var(--border)] text-xs font-medium text-muted hover:text-main hover:bg-[var(--surface-raised)] transition-colors cursor-pointer"
            >
              Close
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
