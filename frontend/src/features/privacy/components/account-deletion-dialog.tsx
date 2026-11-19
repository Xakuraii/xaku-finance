import React, { useState } from "react";
import { requestAccountDeletion } from "../api/privacy-api";
import { AlertCircle, X, ShieldAlert } from "lucide-react";
import { ApiError } from "@/lib/api/client";

interface AccountDeletionDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  twoFactorEnabled?: boolean;
}

export const AccountDeletionDialog: React.FC<AccountDeletionDialogProps> = ({
  isOpen,
  onClose,
  onSuccess,
  twoFactorEnabled,
}) => {
  const [password, setPassword] = useState("");
  const [confirmText, setConfirmText] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (confirmText !== "DELETE") {
      setError("Please type DELETE in all uppercase to confirm.");
      return;
    }

    setError(null);
    setIsLoading(true);

    try {
      await requestAccountDeletion({
        password,
        confirm: confirmText.trim(),
        code: twoFactorEnabled ? code.trim() : undefined,
      });
      onSuccess();
      onClose();
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Failed to schedule account deletion. Please check your credentials.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 overflow-y-auto">
      <div className="w-full max-w-md rounded-2xl border border-destructive/40 bg-[var(--surface)] p-6 shadow-2xl relative transition-all">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-muted hover:text-main hover:bg-[var(--surface-raised)] transition-colors"
          aria-label="Close"
        >
          <X className="w-4 h-4" />
        </button>

        <div className="flex items-center gap-3 mb-4">
          <div className="p-2.5 rounded-xl bg-destructive/10 border border-destructive/30 text-destructive">
            <ShieldAlert className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-main">Request Account Deletion</h2>
            <p className="text-xs text-muted">7-day grace period with automatic backup expiration</p>
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-destructive/10 border border-destructive/20 text-xs text-destructive space-y-2 mb-4 leading-relaxed">
          <p className="font-semibold">Important Consequences:</p>
          <ul className="list-disc pl-4 space-y-1 text-[11px]">
            <li>All accounts, transactions, budgets, goals, and debts will be permanently deleted after 7 days.</li>
            <li>All active sessions on other devices will be revoked immediately.</li>
            <li>Encrypted database backups containing records expire automatically within 30 days.</li>
            <li>You can cancel this request at any time before the 7-day grace period expires.</li>
          </ul>
        </div>

        {error && (
          <div className="mb-4 flex items-center gap-2 rounded-xl bg-destructive/10 border border-destructive/20 p-3 text-xs text-destructive">
            <AlertCircle className="w-4 h-4 shrink-0 text-destructive" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-muted mb-1">Confirm Account Password</label>
            <input
              type="password"
              required
              autoFocus
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••••••"
              className="w-full rounded-lg bg-[var(--surface-raised)] border border-[var(--border)] px-3 py-2 text-sm text-main focus:border-destructive focus:outline-none transition-colors"
            />
          </div>

          {twoFactorEnabled && (
            <div>
              <label className="block text-xs font-medium text-muted mb-1">
                Two-Factor Security Code or Recovery Code
              </label>
              <input
                type="text"
                required
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="6-digit code"
                className="w-full font-mono rounded-lg bg-[var(--surface-raised)] border border-[var(--border)] px-3 py-2 text-sm text-main focus:border-destructive focus:outline-none transition-colors"
              />
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-muted mb-1">
              Type <strong className="text-destructive font-mono">DELETE</strong> to confirm
            </label>
            <input
              type="text"
              required
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              placeholder="DELETE"
              className="w-full font-mono tracking-wider rounded-lg bg-[var(--surface-raised)] border border-[var(--border)] px-3 py-2 text-sm text-main focus:border-destructive focus:outline-none transition-colors"
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
              disabled={isLoading || confirmText !== "DELETE" || !password}
              className="px-4 py-2 rounded-xl bg-destructive text-xs font-semibold text-white hover:opacity-90 transition-opacity cursor-pointer disabled:opacity-50"
            >
              {isLoading ? "Scheduling Deletion..." : "Schedule Account Deletion"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
