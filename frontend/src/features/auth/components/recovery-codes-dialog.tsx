import React, { useState } from "react";
import { regenerateRecoveryCodes } from "../api/2fa-api";
import { KeyRound, Copy, Check, Download, AlertCircle, X } from "lucide-react";
import { ApiError } from "@/lib/api/client";

interface RecoveryCodesDialogProps {
  isOpen: boolean;
  onClose: () => void;
}

export const RecoveryCodesDialog: React.FC<RecoveryCodesDialogProps> = ({
  isOpen,
  onClose,
}) => {
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [recoveryCodes, setRecoveryCodes] = useState<string[]>([]);
  const [copiedCodes, setCopiedCodes] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      const res = await regenerateRecoveryCodes(password, code.trim());
      setRecoveryCodes(res.recovery_codes);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Failed to regenerate recovery codes. Please check your credentials.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const copyAllCodes = () => {
    navigator.clipboard.writeText(recoveryCodes.join("\n"));
    setCopiedCodes(true);
    setTimeout(() => setCopiedCodes(false), 2000);
  };

  const downloadCodes = () => {
    const text = `XakuFinance 2FA Emergency Recovery Codes\nGenerated: ${new Date().toISOString()}\n\n` +
      recoveryCodes.map((c, i) => `${i + 1}. ${c}`).join("\n") +
      "\n\nStore these in a safe place. Each code can only be used once.";
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `xakufinance-recovery-codes-${new Date().toISOString().slice(0, 10)}.txt`;
    link.click();
    URL.revokeObjectURL(url);
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
            <KeyRound className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-main">Emergency Recovery Codes</h2>
            <p className="text-xs text-muted">Generate a new set of single-use recovery codes</p>
          </div>
        </div>

        {error && (
          <div className="mb-4 flex items-center gap-2 rounded-xl bg-red-500/10 border border-red-500/20 p-3 text-xs text-negative">
            <AlertCircle className="w-4 h-4 shrink-0 text-negative" />
            <span>{error}</span>
          </div>
        )}

        {recoveryCodes.length === 0 ? (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-400 leading-relaxed">
              Generating new recovery codes immediately revokes all of your previous recovery codes.
            </div>

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
                className="px-4 py-2 rounded-xl bg-gold text-xs font-semibold text-black hover:opacity-90 transition-opacity cursor-pointer disabled:opacity-50"
              >
                {isLoading ? "Generating..." : "Generate New Codes"}
              </button>
            </div>
          </form>
        ) : (
          <div className="space-y-4">
            <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-400 leading-relaxed">
              10 new recovery codes generated! Your old recovery codes are no longer valid.
            </div>

            <div className="grid grid-cols-2 gap-2 p-3 rounded-xl bg-[var(--surface-raised)] border border-[var(--border)] font-mono text-xs text-main">
              {recoveryCodes.map((c, i) => (
                <div key={i} className="py-1 px-2 rounded bg-[var(--surface)] text-center tracking-wider border border-[var(--border)]">
                  {c}
                </div>
              ))}
            </div>

            <div className="flex gap-2">
              <button
                type="button"
                onClick={copyAllCodes}
                className="flex-1 py-2 px-3 rounded-xl border border-[var(--border)] bg-[var(--surface-raised)] hover:bg-[var(--surface)] text-xs font-medium text-main flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
              >
                {copiedCodes ? <Check className="w-3.5 h-3.5 text-gold" /> : <Copy className="w-3.5 h-3.5" />}
                {copiedCodes ? "Copied!" : "Copy All"}
              </button>
              <button
                type="button"
                onClick={downloadCodes}
                className="flex-1 py-2 px-3 rounded-xl border border-[var(--border)] bg-[var(--surface-raised)] hover:bg-[var(--surface)] text-xs font-medium text-main flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
              >
                <Download className="w-3.5 h-3.5" />
                Download (.txt)
              </button>
            </div>

            <button
              type="button"
              onClick={onClose}
              className="w-full py-2.5 rounded-xl bg-gold text-xs font-semibold text-black hover:opacity-90 transition-opacity cursor-pointer"
            >
              Done
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
