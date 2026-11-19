import React, { useState } from "react";
import { disableTwoFactor } from "../api/2fa-api";
import { AlertTriangle, AlertCircle, X } from "lucide-react";
import { ApiError } from "@/lib/api/client";

interface TwoFactorDisableDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const TwoFactorDisableDialog: React.FC<TwoFactorDisableDialogProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      await disableTwoFactor(password, code.trim());
      onSuccess();
      onClose();
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Failed to disable two-factor authentication. Please check your credentials.");
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
          <div className="p-2.5 rounded-xl bg-red-500/10 border border-red-500/30 text-negative">
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-main">Disable Two-Factor Authentication</h2>
            <p className="text-xs text-muted">Remove the secondary security requirement</p>
          </div>
        </div>

        <div className="mb-4 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-xs text-negative leading-relaxed">
          Disabling 2FA reduces your account security. Anyone with your password will be able to sign in without an authenticator code.
        </div>

        {error && (
          <div className="mb-4 flex items-center gap-2 rounded-xl bg-red-500/10 border border-red-500/20 p-3 text-xs text-negative">
            <AlertCircle className="w-4 h-4 shrink-0 text-negative" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
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

          <div>
            <label className="block text-xs font-medium text-muted mb-1">
              Current Authenticator or Recovery Code
            </label>
            <input
              type="text"
              required
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="6-digit code or recovery code"
              className="w-full rounded-lg bg-[var(--surface-raised)] border border-[var(--border)] px-3 py-2 text-sm text-main font-mono focus:border-[var(--accent)] focus:outline-none transition-colors"
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
              disabled={isLoading || !password || !code}
              className="px-4 py-2 rounded-xl bg-negative text-xs font-semibold text-white hover:opacity-90 transition-opacity cursor-pointer disabled:opacity-50"
            >
              {isLoading ? "Disabling..." : "Disable 2FA"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
