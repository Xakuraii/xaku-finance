import React, { useState } from "react";
import {
  reauth,
  setupTwoFactor,
  confirmTwoFactor,
  TwoFactorSetupResponse,
} from "../api/2fa-api";
import { Shield, Copy, Check, Download, AlertCircle, ArrowRight, X } from "lucide-react";
import { ApiError } from "@/lib/api/client";

interface TwoFactorSetupDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const TwoFactorSetupDialog: React.FC<TwoFactorSetupDialogProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [step, setStep] = useState<"password" | "scan" | "codes">("password");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [setupData, setSetupData] = useState<TwoFactorSetupResponse | null>(null);
  const [recoveryCodes, setRecoveryCodes] = useState<string[]>([]);
  const [copiedSecret, setCopiedSecret] = useState(false);
  const [copiedCodes, setCopiedCodes] = useState(false);
  const [acknowledged, setAcknowledged] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  if (!isOpen) return null;

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);
    try {
      await reauth(password);
      const setup = await setupTwoFactor();
      setSetupData(setup);
      setStep("scan");
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

  const handleConfirmCode = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);
    try {
      const res = await confirmTwoFactor(code.trim());
      setRecoveryCodes(res.recovery_codes);
      setStep("codes");
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Invalid verification code. Please check your authenticator app.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const copySecret = () => {
    if (!setupData) return;
    navigator.clipboard.writeText(setupData.secret);
    setCopiedSecret(true);
    setTimeout(() => setCopiedSecret(false), 2000);
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

  const handleFinish = () => {
    onSuccess();
    onClose();
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
            <Shield className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-main">Set Up Two-Factor Authentication</h2>
            <p className="text-xs text-muted">Protect your financial workspace with TOTP 2FA</p>
          </div>
        </div>

        {error && (
          <div className="mb-4 flex items-center gap-2 rounded-xl bg-red-500/10 border border-red-500/20 p-3 text-xs text-negative">
            <AlertCircle className="w-4 h-4 shrink-0 text-negative" />
            <span>{error}</span>
          </div>
        )}

        {step === "password" && (
          <form onSubmit={handlePasswordSubmit} className="space-y-4">
            <p className="text-xs text-muted leading-relaxed">
              For security, please confirm your current account password to begin two-factor setup.
            </p>
            <div>
              <label className="block text-xs font-medium text-muted mb-1">Current Password</label>
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
                className="px-3.5 py-2 rounded-xl border border-[var(--border)] text-xs font-medium text-main hover:bg-[var(--surface-raised)] transition-colors"
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

        {step === "scan" && setupData && (
          <div className="space-y-4">
            <p className="text-xs text-muted leading-relaxed">
              Scan this QR code using Google Authenticator, 1Password, Authy, or any TOTP app.
            </p>

            <div className="flex justify-center p-4 rounded-xl bg-white border border-[var(--border)]">
              <div
                className="w-48 h-48 flex items-center justify-center [&_svg]:w-full [&_svg]:h-full"
                dangerouslySetInnerHTML={{ __html: setupData.qr_svg }}
              />
            </div>

            <div className="space-y-1">
              <div className="text-[11px] text-muted">Or enter secret key manually:</div>
              <div className="flex items-center justify-between p-2 rounded-lg bg-[var(--surface-raised)] border border-[var(--border)] text-xs font-mono text-main">
                <span className="truncate select-all">{setupData.secret}</span>
                <button
                  type="button"
                  onClick={copySecret}
                  className="ml-2 p-1 rounded hover:bg-[var(--border)] transition-colors text-muted hover:text-main"
                  title="Copy secret"
                >
                  {copiedSecret ? <Check className="w-3.5 h-3.5 text-gold" /> : <Copy className="w-3.5 h-3.5" />}
                </button>
              </div>
            </div>

            <form onSubmit={handleConfirmCode} className="space-y-3 pt-2">
              <div>
                <label className="block text-xs font-medium text-muted mb-1">
                  Enter 6-digit confirmation code:
                </label>
                <input
                  type="text"
                  required
                  autoFocus
                  autoComplete="one-time-code"
                  maxLength={6}
                  value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                  placeholder="123456"
                  className="w-full text-center text-lg tracking-widest font-mono rounded-lg bg-[var(--surface-raised)] border border-[var(--border)] px-3 py-2 text-main focus:border-[var(--accent)] focus:outline-none transition-colors"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-3.5 py-2 rounded-xl border border-[var(--border)] text-xs font-medium text-main hover:bg-[var(--surface-raised)] transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isLoading || code.length !== 6}
                  className="px-4 py-2 rounded-xl bg-gold text-xs font-semibold text-black hover:opacity-90 transition-opacity cursor-pointer disabled:opacity-50"
                >
                  {isLoading ? "Activating..." : "Enable 2FA"}
                </button>
              </div>
            </form>
          </div>
        )}

        {step === "codes" && (
          <div className="space-y-4">
            <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs">
              Two-factor authentication is now active! Save your emergency recovery codes below.
            </div>

            <p className="text-xs text-muted leading-relaxed">
              If you lose access to your authenticator app, these codes are the <strong>only way</strong> to access your account. Each code can be used once.
            </p>

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

            <div className="flex items-start gap-2 pt-2">
              <input
                type="checkbox"
                id="ack-recovery"
                checked={acknowledged}
                onChange={(e) => setAcknowledged(e.target.checked)}
                className="mt-0.5 rounded border-[var(--border)] text-gold focus:ring-gold"
              />
              <label htmlFor="ack-recovery" className="text-xs text-muted cursor-pointer">
                I have copied or downloaded my emergency recovery codes and understand they cannot be shown again.
              </label>
            </div>

            <button
              type="button"
              disabled={!acknowledged}
              onClick={handleFinish}
              className="w-full py-2.5 rounded-xl bg-gold text-xs font-semibold text-black hover:opacity-90 transition-opacity cursor-pointer disabled:opacity-50"
            >
              Done & Return to Settings
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
