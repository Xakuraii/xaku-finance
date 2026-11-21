import React, { useState, useEffect } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../auth-context";
import {
  AlertCircle,
  ArrowLeft,
  Sparkles,
  Check,
  ShieldCheck,
  KeyRound,
  Eye,
  EyeOff,
} from "lucide-react";
import { ApiError } from "@/lib/api/client";
import { AnimatedThemeToggler } from "@/components/ui/animated-theme-toggler";
import { GoogleAuthButton } from "../components/google-auth-button";

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { login, loginWithGoogle, complete2FALogin } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [demoFilled, setDemoFilled] = useState(false);

  // 2FA Challenge state
  const [mfaChallenge, setMfaChallenge] = useState<{
    mfaToken: string;
    expiresIn?: number;
  } | null>(null);
  const [twoFactorCode, setTwoFactorCode] = useState("");
  const [useRecoveryCode, setUseRecoveryCode] = useState(false);

  useEffect(() => {
    if (searchParams.get("demo") === "true") {
      fillDemoCredentials();
    }
  }, [searchParams]);

  const fillDemoCredentials = () => {
    setEmail("demo@xakufinance.local");
    setPassword("DemoPass123456");
    setDemoFilled(true);
    setTimeout(() => setDemoFilled(false), 2000);
  };

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      const result = await login(email.trim(), password);
      if (result.mfa_required && result.mfa_token) {
        setMfaChallenge({
          mfaToken: result.mfa_token,
          expiresIn: result.expires_in,
        });
        setTwoFactorCode("");
      } else {
        navigate("/app/accounts");
      }
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage("Invalid email or password.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleGoogleToken = async (idToken: string) => {
    if (!loginWithGoogle) return;
    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      const result = await loginWithGoogle(idToken);
      if (result.mfa_required && result.mfa_token) {
        setMfaChallenge({
          mfaToken: result.mfa_token,
          expiresIn: result.expires_in,
        });
        setTwoFactorCode("");
      } else {
        navigate("/app/accounts");
      }
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage("Google sign-in failed. Please verify your OAuth configuration.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handle2FASubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!mfaChallenge) return;
    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      await complete2FALogin(mfaChallenge.mfaToken, twoFactorCode.trim());
      navigate("/app/accounts");
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage("Invalid verification code. Please check your authenticator or recovery codes.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const cancelMfa = () => {
    setMfaChallenge(null);
    setTwoFactorCode("");
    setErrorMessage(null);
  };

  return (
    <div className="min-h-screen flex flex-col justify-between p-5 sm:p-8 bg-[var(--bg)] text-[var(--text)] relative overflow-hidden transition-colors">
      {/* Subtle Ambient Institutional Glow */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-32 left-1/2 -translate-x-1/2 w-[520px] h-[320px] rounded-full bg-[var(--accent)]/8 blur-[130px]" />
        <div className="absolute -bottom-32 right-1/4 w-[380px] h-[260px] rounded-full bg-[var(--positive)]/6 blur-[130px]" />
      </div>

      {/* Minimal Top Bar */}
      <div className="relative z-10 flex items-center justify-between max-w-5xl w-full mx-auto">
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-xs text-muted hover:text-main px-3 py-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface)]/90 backdrop-blur-sm hover:bg-[var(--surface-raised)] transition-all"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Home</span>
        </Link>

        <AnimatedThemeToggler variant="circle" />
      </div>

      {/* Centered Auth Card */}
      <div className="relative z-10 w-full max-w-[430px] mx-auto my-auto py-6 animate-xaku-fade-up">
        <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-7 sm:p-8 shadow-2xl shadow-black/10 dark:shadow-black/45 space-y-6 relative overflow-hidden transition-colors">
          <div className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-transparent via-[var(--accent)] to-transparent opacity-80" />
          {!mfaChallenge ? (
            <>
              <div className="text-center space-y-2.5">
                <Link to="/" className="inline-flex items-center gap-2 group mb-0.5">
                  <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#F0B90B] to-[#D9A600] flex items-center justify-center text-black font-bold shadow-sm group-hover:scale-105 transition-transform">
                    <span className="font-display text-base">X</span>
                  </div>
                  <span className="font-display font-bold tracking-tight text-lg text-main">
                    XakuFinance
                  </span>
                </Link>
                <h1 className="font-display text-2xl font-bold tracking-tight text-main">
                  Welcome Back
                </h1>
                <p className="text-xs text-muted">
                  Sign in to inspect your USD &amp; Khmer Riel double-entry ledger.
                </p>
              </div>

                {/* Real Google Gmail OAuth Sign-In */}
                <GoogleAuthButton
                  onSuccessToken={handleGoogleToken}
                  label="Continue with Google"
                  mode="signin"
                  disabled={isSubmitting}
                />

                <div className="relative flex items-center">
                  <div className="flex-grow border-t border-[var(--border)]" />
                  <span className="shrink mx-3 text-[11px] text-faint font-medium">
                    or continue with email
                  </span>
                  <div className="flex-grow border-t border-[var(--border)]" />
                </div>

                {/* Demo Credentials Quick-Fill Pill */}
                <div className="flex items-center justify-between p-2.5 rounded-xl border border-[var(--accent)]/30 bg-[var(--accent)]/8 text-xs">
                  <div className="space-y-0.5 min-w-0">
                    <div className="font-medium text-main flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5 text-gold shrink-0" />
                      Demo Workspace
                    </div>
                    <div className="text-[11px] text-muted truncate font-mono">
                      demo@xakufinance.local
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={fillDemoCredentials}
                    className="px-2.5 py-1 rounded-lg bg-gold text-[11px] font-semibold hover:opacity-90 transition-opacity cursor-pointer flex items-center gap-1 shrink-0"
                  >
                    {demoFilled ? <Check className="w-3 h-3" /> : null}
                    {demoFilled ? "Filled!" : "Fill Demo"}
                  </button>
                </div>

                {errorMessage && (
                  <div className="flex items-center gap-2 rounded-xl bg-[var(--negative-bg)] border border-[var(--negative-border)] p-3 text-xs text-[var(--negative)]">
                    <AlertCircle className="w-4 h-4 shrink-0" />
                    <span>{errorMessage}</span>
                  </div>
                )}

                <form onSubmit={handlePasswordSubmit} className="space-y-4">
                  <div>
                    <label className="block text-xs font-medium text-muted mb-1">Email</label>
                    <input
                      type="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="you@example.com"
                      className="w-full rounded-xl bg-[var(--surface-raised)] border border-[var(--border)] px-3.5 py-2.5 text-sm text-main focus:border-[var(--accent)] focus:outline-none transition-colors"
                    />
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <label className="text-xs font-medium text-muted">Password</label>
                    </div>
                    <div className="relative">
                      <input
                        type={showPassword ? "text" : "password"}
                        required
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="••••••••••••"
                        className="w-full rounded-xl bg-[var(--surface-raised)] border border-[var(--border)] pl-3.5 pr-10 py-2.5 text-sm text-main focus:border-[var(--accent)] focus:outline-none transition-colors"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword((v) => !v)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-faint hover:text-main cursor-pointer"
                        aria-label={showPassword ? "Hide password" : "Show password"}
                      >
                        {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="w-full rounded-xl bg-gold py-2.5 text-xs font-semibold cursor-pointer disabled:opacity-50 transition-opacity shadow-sm hover:opacity-95"
                  >
                    {isSubmitting ? "Signing in..." : "Sign In to Workspace"}
                  </button>
                </form>

                <div className="text-center text-xs text-muted border-t border-[var(--border)] pt-4">
                  Don't have an account?{" "}
                  <Link to="/register" className="text-gold hover:underline font-medium">
                    Create Workspace
                  </Link>
                </div>
              </>
            ) : (
              <>
                {/* 2FA Challenge View */}
                <div className="text-center space-y-2">
                  <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-[var(--accent)]/12 border border-[var(--accent)]/30 text-gold mb-1 shadow-xs">
                    {useRecoveryCode ? <KeyRound className="w-5 h-5" /> : <ShieldCheck className="w-5 h-5" />}
                  </div>
                  <h1 className="font-display text-xl font-bold tracking-tight text-main">
                    {useRecoveryCode ? "Enter Recovery Code" : "Two-Factor Verification"}
                  </h1>
                  <p className="text-xs text-muted">
                    {useRecoveryCode
                      ? "Enter one of your 10-character emergency recovery codes."
                      : "Enter the 6-digit security code from your authenticator app."}
                  </p>
                </div>

                {errorMessage && (
                  <div className="flex items-center gap-2 rounded-xl bg-[var(--negative-bg)] border border-[var(--negative-border)] p-3 text-xs text-[var(--negative)]">
                    <AlertCircle className="w-4 h-4 shrink-0" />
                    <span>{errorMessage}</span>
                  </div>
                )}

                <form onSubmit={handle2FASubmit} className="space-y-4">
                  <div>
                    <label className="block text-xs font-medium text-muted mb-1">
                      {useRecoveryCode ? "Recovery Code" : "Authentication Code"}
                    </label>
                    <input
                      type="text"
                      required
                      autoFocus
                      autoComplete="one-time-code"
                      value={twoFactorCode}
                      onChange={(e) => setTwoFactorCode(e.target.value)}
                      placeholder={useRecoveryCode ? "e.g. 4F8A-9B2C" : "123456"}
                      maxLength={useRecoveryCode ? 20 : 8}
                      className="w-full text-center tracking-widest text-lg font-mono rounded-xl bg-[var(--surface-raised)] border border-[var(--border)] px-3 py-2.5 text-main focus:border-[var(--accent)] focus:outline-none transition-colors"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={isSubmitting || twoFactorCode.trim().length === 0}
                    className="w-full rounded-xl bg-gold py-2.5 text-xs font-semibold cursor-pointer disabled:opacity-50 transition-opacity shadow-sm hover:opacity-95"
                  >
                    {isSubmitting ? "Verifying..." : "Verify & Continue"}
                  </button>
                </form>

                <div className="flex flex-col items-center gap-2 pt-2 border-t border-[var(--border)] text-xs">
                  <button
                    type="button"
                    onClick={() => {
                      setUseRecoveryCode(!useRecoveryCode);
                      setTwoFactorCode("");
                      setErrorMessage(null);
                    }}
                    className="text-gold hover:underline cursor-pointer font-medium"
                  >
                    {useRecoveryCode
                      ? "Use Authenticator App instead"
                      : "Lost access? Use an emergency recovery code"}
                  </button>
                  <button
                    type="button"
                    onClick={cancelMfa}
                    className="text-muted hover:text-main cursor-pointer"
                  >
                    Cancel and return to password login
                  </button>
                </div>
              </>
            )}
        </div>

        <p className="text-center text-[11px] font-mono text-faint mt-4">
          Zero-Drift Double-Entry · USD &amp; KHR
        </p>
      </div>

      <div className="relative z-10 text-center text-[11px] text-faint">
        XakuFinance · Private Financial Ledger
      </div>
    </div>
  );
};
