import React, { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth-context";
import {
  AlertCircle,
  UserPlus,
  ArrowLeft,
  Eye,
  EyeOff,
  CheckCircle2,
  Coins,
  Shield,
  ShieldCheck,
} from "lucide-react";
import { ApiError } from "@/lib/api/client";
import { AnimatedThemeToggler } from "@/components/ui/animated-theme-toggler";
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
    <div className="min-h-screen flex bg-[var(--bg)] text-[var(--text)] transition-colors">
      {/* Left Institutional Showcase Panel */}
      <aside className="hidden lg:flex lg:w-[46%] xl:w-[48%] flex-col justify-between p-10 xl:p-14 border-r border-[var(--border)] bg-[var(--surface)] relative overflow-hidden">
        <div className="absolute -top-24 -left-24 w-96 h-96 rounded-full bg-[var(--accent)]/8 blur-[120px] pointer-events-none" />
        <div className="absolute -bottom-24 -right-24 w-96 h-96 rounded-full bg-[var(--positive)]/6 blur-[120px] pointer-events-none" />

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

        <div className="relative z-10 space-y-8 my-auto py-8">
          <div className="space-y-3">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-[var(--accent)]/30 bg-[var(--accent)]/8 text-gold text-xs font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent)]" />
              Open Your Private Ledger
            </div>
            <h2 className="font-display text-3xl xl:text-4xl font-bold tracking-tight text-main leading-[1.15]">
              Every dollar and riel accounted for to the minor unit.
            </h2>
            <p className="text-sm text-muted leading-relaxed max-w-md">
              Create your isolated workspace with USD ($), Khmer Riel (៛), or combined dual-currency reporting enabled out of the box.
            </p>
          </div>

          <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg)] p-5 shadow-lg space-y-4 max-w-md">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-muted">Multi-Currency Ledger Sample</span>
              <span className="inline-flex items-center gap-1 text-[10px] font-medium px-2 py-0.5 rounded-full bg-[var(--positive-bg)] border border-[var(--positive-border)] text-[var(--positive)]">
                <CheckCircle2 className="w-3 h-3" />
                Atomic Journal
              </span>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-xl bg-[var(--surface)] border border-[var(--border)] p-3">
                <div className="text-[10px] text-faint font-medium">Primary USD Wallet</div>
                <div className="font-mono text-lg font-bold text-gold mt-0.5">$4,250.00</div>
              </div>
              <div className="rounded-xl bg-[var(--surface)] border border-[var(--border)] p-3">
                <div className="text-[10px] text-faint font-medium">Local KHR Wallet</div>
                <div className="font-mono text-lg font-bold text-[var(--positive)] mt-0.5">17,425,000 ៛</div>
              </div>
            </div>

            <div className="flex items-center justify-between text-[11px] font-mono text-faint pt-2 border-t border-[var(--border)]">
              <span>Auto Dual Conversion</span>
              <span>$1 = 4,100 ៛</span>
            </div>
          </div>

          <div className="space-y-3 pt-1">
            {[
              {
                icon: <Shield className="w-4 h-4 text-gold" />,
                title: "Strict Workspace Isolation",
                desc: "All accounts, budgets, and goals live in an isolated tenant boundary.",
              },
              {
                icon: <Coins className="w-4 h-4 text-[var(--positive)]" />,
                title: "Switch Currencies Anytime",
                desc: "Inspect individual USD / KHR wallets or view combined portfolio value.",
              },
              {
                icon: <ShieldCheck className="w-4 h-4 text-[var(--info)]" />,
                title: "Instant Gmail Onboarding",
                desc: "Sign up in one step with Google OAuth 2.0 or strong email credentials.",
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
          XakuFinance · Verified Workspace Creation
        </div>
      </aside>

      {/* Right Form Column */}
      <div className="flex-1 flex flex-col justify-between p-5 sm:p-8 relative">
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

        <div className="w-full max-w-md mx-auto my-auto py-8">
          <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-7 sm:p-8 shadow-xl space-y-5 transition-colors">
            <div className="text-center space-y-2">
              <div className="inline-flex items-center justify-center w-11 h-11 rounded-xl bg-[var(--accent)]/12 border border-[var(--accent)]/30 text-gold mb-1 shadow-xs">
                <UserPlus className="w-5 h-5" />
              </div>
              <h1 className="font-display text-2xl font-bold tracking-tight text-main">
                Create Workspace
              </h1>
              <p className="text-xs text-muted">
                Set up your private financial ledger with accounting integrity.
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
        </div>

        <div className="text-center text-[11px] text-faint lg:hidden">
          XakuFinance · Double-Entry Ledger Architecture
        </div>
      </div>
    </div>
  );
};
