import React, { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth-context";
import {
  AlertCircle,
  ArrowLeft,
  Eye,
  EyeOff,
  CheckCircle2,
} from "lucide-react";
import { ApiError } from "@/lib/api/client";
import { AnimatedThemeToggler } from "@/components/ui/animated-theme-toggler";
import { BrandLogo } from "@/components/brand-logo";
import { GoogleAuthButton } from "../components/google-auth-button";

export const RegisterPage: React.FC = () => {
  const navigate = useNavigate();
  const { register, loginWithGoogle } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [displayName, setDisplayName] = useState("");
  const [reportingCurrency, setReportingCurrency] = useState<"USD" | "KHR">("USD");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const passwordStrength = useMemo(() => {
    let score = 0;
    if (password.length >= 12) score += 1;
    if (/[A-Z]/.test(password)) score += 1;
    if (/[0-9]/.test(password)) score += 1;
    if (/[^A-Za-z0-9]/.test(password)) score += 1;

    const labels = ["Too short", "Weak", "Fair", "Good", "Strong"];
    const colors = [
      "var(--border-strong)",
      "var(--negative)",
      "var(--warning)",
      "var(--info)",
      "var(--positive)",
    ];
    return { score, label: password ? labels[score] : "Minimum 12 chars", color: colors[score] };
  }, [password]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (password.length < 12) {
      setErrorMessage("Password must be at least 12 characters long.");
      return;
    }

    setIsSubmitting(true);
    try {
      await register({
        email: email.trim(),
        password,
        display_name: displayName.trim() || undefined,
        reporting_currency: reportingCurrency,
      });
      navigate("/app/accounts");
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage("Registration failed. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleGoogleSignUp = async (idToken: string) => {
    if (!loginWithGoogle) return;
    setErrorMessage(null);
    setIsSubmitting(true);
    try {
      const result = await loginWithGoogle(idToken);
      if (result.mfa_required) {
        navigate("/login");
      } else {
        navigate("/app/accounts");
      }
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage("Google sign-up failed. Please verify your OAuth configuration.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col justify-between p-5 sm:p-8 bg-[var(--bg)] text-[var(--text)] relative overflow-hidden transition-colors">
      {/* Subtle Ambient Institutional Glow */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-32 left-1/2 -translate-x-1/2 w-[520px] h-[320px] rounded-full bg-[var(--accent)]/8 blur-[130px]" />
        <div className="absolute -bottom-32 left-1/4 w-[380px] h-[260px] rounded-full bg-[var(--positive)]/6 blur-[130px]" />
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

      {/* Centered Registration Card */}
      <div className="relative z-10 w-full max-w-[440px] mx-auto my-auto py-6 animate-xaku-fade-up">
        <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-7 sm:p-8 shadow-2xl shadow-black/10 dark:shadow-black/45 space-y-5 relative overflow-hidden transition-colors">
          <div className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-transparent via-[var(--accent)] to-transparent opacity-80" />
          <div className="text-center space-y-2">
            <Link to="/" className="inline-flex items-center group mb-0.5">
              <BrandLogo
                iconClassName="w-10 h-10 sm:w-12 sm:h-12 group-hover:scale-105 transition-transform"
                textClassName="text-xl sm:text-2xl"
              />
            </Link>
            <h1 className="font-display text-2xl font-bold tracking-tight text-main">
              Create Workspace
            </h1>
            <p className="text-xs text-muted">
              Set up your private USD &amp; Khmer Riel ledger with accounting integrity.
            </p>
          </div>

            <GoogleAuthButton
              onSuccessToken={handleGoogleSignUp}
              label="Sign up with Google"
              mode="signup"
              disabled={isSubmitting}
            />

            <div className="relative flex items-center">
              <div className="flex-grow border-t border-[var(--border)]" />
              <span className="shrink mx-3 text-[11px] text-faint font-medium">
                or create with email
              </span>
              <div className="flex-grow border-t border-[var(--border)]" />
            </div>

            {errorMessage && (
              <div className="flex items-center gap-2 rounded-xl bg-[var(--negative-bg)] border border-[var(--negative-border)] p-3 text-xs text-[var(--negative)]">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{errorMessage}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
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
                <label className="block text-xs font-medium text-muted mb-1">
                  Display Name <span className="text-faint font-normal">(Optional)</span>
                </label>
                <input
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="Mara"
                  className="w-full rounded-xl bg-[var(--surface-raised)] border border-[var(--border)] px-3.5 py-2.5 text-sm text-main focus:border-[var(--accent)] focus:outline-none transition-colors"
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="block text-xs font-medium text-muted">Primary Reporting Currency</label>
                </div>
                <div className="grid grid-cols-2 gap-2.5">
                  <button
                    type="button"
                    onClick={() => setReportingCurrency("USD")}
                    className={`flex flex-col items-start p-3 rounded-xl border text-left transition-all cursor-pointer ${
                      reportingCurrency === "USD"
                        ? "border-[var(--accent)] bg-[var(--accent)]/10"
                        : "border-[var(--border)] bg-[var(--surface-raised)] hover:border-[var(--border-strong)]"
                    }`}
                  >
                    <div className="flex items-center justify-between w-full">
                      <span className="font-mono text-sm font-bold text-main">USD ($)</span>
                      {reportingCurrency === "USD" && (
                        <CheckCircle2 className="w-3.5 h-3.5 text-gold" />
                      )}
                    </div>
                    <span className="text-[11px] text-muted mt-0.5">US Dollar</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setReportingCurrency("KHR")}
                    className={`flex flex-col items-start p-3 rounded-xl border text-left transition-all cursor-pointer ${
                      reportingCurrency === "KHR"
                        ? "border-[var(--accent)] bg-[var(--accent)]/10"
                        : "border-[var(--border)] bg-[var(--surface-raised)] hover:border-[var(--border-strong)]"
                    }`}
                  >
                    <div className="flex items-center justify-between w-full">
                      <span className="font-mono text-sm font-bold text-main">KHR (៛)</span>
                      {reportingCurrency === "KHR" && (
                        <CheckCircle2 className="w-3.5 h-3.5 text-gold" />
                      )}
                    </div>
                    <span className="text-[11px] text-muted mt-0.5">Khmer Riel</span>
                  </button>
                </div>
                <p className="text-[10px] text-faint mt-1.5">
                  You can view both USD &amp; KHR individually or combined inside the workspace.
                </p>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="block text-xs font-medium text-muted">Password</label>
                  <span
                    className="text-[10px] font-medium"
                    style={{ color: passwordStrength.color }}
                  >
                    {passwordStrength.label}
                  </span>
                </div>
                <div className="relative">
                  <input
                    type={showPassword ? "text" : "password"}
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="At least 12 characters"
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

                {/* 4-segment Password Strength Meter */}
                <div className="grid grid-cols-4 gap-1 mt-2">
                  {[1, 2, 3, 4].map((step) => (
                    <div
                      key={step}
                      className="h-1 rounded-full transition-colors"
                      style={{
                        backgroundColor:
                          password && passwordStrength.score >= step
                            ? passwordStrength.color
                            : "var(--surface-raised)",
                      }}
                    />
                  ))}
                </div>
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full rounded-xl bg-gold py-2.5 text-xs font-semibold cursor-pointer disabled:opacity-50 transition-opacity shadow-sm hover:opacity-95"
              >
                {isSubmitting ? "Creating Workspace..." : "Create Free Workspace"}
              </button>
            </form>

            <div className="text-center text-xs text-muted border-t border-[var(--border)] pt-4">
              Already have an account?{" "}
              <Link to="/login" className="text-gold hover:underline font-medium">
                Sign in
              </Link>
            </div>
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
