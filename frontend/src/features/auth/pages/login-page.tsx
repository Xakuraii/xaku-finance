import React, { useState, useEffect } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../auth-context";
import {
  AlertCircle,
  Lock,
  ArrowLeft,
  Sparkles,
  Check,
  ShieldCheck,
  KeyRound,
  Eye,
  EyeOff,
  CheckCircle2,
  Coins,
  Shield,
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
    <div className="min-h-screen flex bg-[var(--bg)] text-[var(--text)] transition-colors">
      {/* Left Institutional Showcase Panel */}
      <aside className="hidden lg:flex lg:w-[46%] xl:w-[48%] flex-col justify-between p-10 xl:p-14 border-r border-[var(--border)] bg-[var(--surface)] relative overflow-hidden">
        <div className="absolute -top-24 -left-24 w-96 h-96 rounded-full bg-[var(--accent)]/8 blur-[120px] pointer-events-none" />
        <div className="absolute -bottom-24 -right-24 w-96 h-96 rounded-full bg-[var(--positive)]/6 blur-[120px] pointer-events-none" />

        {/* Brand Header */}
        <div className="relative z-10 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5 group">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#F0B90B] to-[#D9A600] flex items-center justify-center text-black font-bold shadow-sm group-hover:scale-105 transition-transform">
              <span className="font-display text-base">X</span>
            </div>
            <div>
              <span className="font-display font-bold tracking-tight text-lg text-main block leading-tight">
                XakuFinance
              </span>
              <span className="text-[10px] tracking-wider uppercase text-faint font-medium">
                Double-Entry Ledger Architecture
              </span>
            </div>
          </Link>
        </div>

        {/* Center Showcase Content */}
        <div className="relative z-10 space-y-8 my-auto py-8">
          <div className="space-y-3">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-[var(--accent)]/30 bg-[var(--accent)]/8 text-gold text-xs font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent)]" />
              Institutional Financial Control
            </div>
            <h2 className="font-display text-3xl xl:text-4xl font-bold tracking-tight text-main leading-[1.15]">
              Sovereign financial clarity with zero drift.
            </h2>
            <p className="text-sm text-muted leading-relaxed max-w-md">
              Monitor US Dollar ($) and Cambodian Riel (៛) accounts simultaneously in one reconciled double-entry journal.
            </p>
          </div>

          {/* Dual-Currency Live Preview Card */}
          <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg)] p-5 shadow-lg space-y-4 max-w-md">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-muted">Combined Liquid Balance</span>
              <span className="inline-flex items-center gap-1 text-[10px] font-medium px-2 py-0.5 rounded-full bg-[var(--positive-bg)] border border-[var(--positive-border)] text-[var(--positive)]">
                <CheckCircle2 className="w-3 h-3" />
                0 Drift
              </span>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-xl bg-[var(--surface)] border border-[var(--border)] p-3">
                <div className="text-[10px] text-faint font-medium">US Dollar ($)</div>
                <div className="font-mono text-lg font-bold text-gold mt-0.5">$13,700.00</div>
              </div>
              <div className="rounded-xl bg-[var(--surface)] border border-[var(--border)] p-3">
                <div className="text-[10px] text-faint font-medium">Khmer Riel (៛)</div>
                <div className="font-mono text-lg font-bold text-[var(--positive)] mt-0.5">56,170,000 ៛</div>
              </div>
            </div>

            <div className="flex items-center justify-between text-[11px] font-mono text-faint pt-2 border-t border-[var(--border)]">
              <span>Live Dual-Currency View</span>
              <span>$1 = 4,100 ៛</span>
            </div>
          </div>

          {/* 3 Security Pillars */}
          <div className="space-y-3 pt-1">
            {[
              {
                icon: <Shield className="w-4 h-4 text-gold" />,
                title: "Double-Entry Zero-Drift Core",
                desc: "Every transaction posts immutable balanced debit & credit lines.",
              },
              {
                icon: <Coins className="w-4 h-4 text-[var(--positive)]" />,
                title: "USD & Khmer Riel Dual-Currency",
                desc: "Switch between $, ៛, or combined dual view in one click.",
              },
              {
                icon: <ShieldCheck className="w-4 h-4 text-[var(--info)]" />,
                title: "Google OAuth 2.0 & RFC 6238 TOTP",
                desc: "Verified Gmail identity plus optional authenticator two-factor security.",
              },
            ].map((item) => (
              <div key={item.title} className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-[var(--surface-raised)] border border-[var(--border)] flex items-center justify-center shrink-0 mt-0.5">
                  {item.icon}
                </div>
                <div>
                  <div className="text-xs font-semibold text-main">{item.title}</div>
                  <div className="text-[11px] text-muted">{item.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="relative z-10 text-[11px] text-faint font-mono">
          XakuFinance · Verified Workspace Access
        </div>
      </aside>

      {/* Right Authentication Area */}
      <div className="flex-1 flex flex-col justify-between p-5 sm:p-8 relative">
        {/* Top Controls */}
        <div className="flex items-center justify-between">
          <Link
            to="/"
            className="inline-flex items-center gap-1.5 text-xs text-muted hover:text-main px-3 py-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] hover:bg-[var(--surface-raised)] transition-all"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to Home</span>
          </Link>

          <AnimatedThemeToggler variant="circle" />
        </div>

        {/* Center Auth Card */}
        <div className="w-full max-w-md mx-auto my-auto py-8">
          <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-7 sm:p-8 shadow-xl space-y-6 transition-colors">
            {!mfaChallenge ? (
              <>
                <div className="text-center space-y-2">
                  <div className="inline-flex items-center justify-center w-11 h-11 rounded-xl bg-[var(--accent)]/12 border border-[var(--accent)]/30 text-gold mb-1 shadow-xs">
                    <Lock className="w-5 h-5" />
                  </div>
                  <h1 className="font-display text-2xl font-bold tracking-tight text-main">
                    Welcome Back
                  </h1>
                  <p className="text-xs text-muted">
                    Sign in to XakuFinance to inspect your dual-currency ledger.
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
        </div>

        <div className="text-center text-[11px] text-faint lg:hidden">
          XakuFinance · Double-Entry Ledger Architecture
        </div>
      </div>
    </div>
  );
};
