import React, { useState, useEffect } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../auth-context";
import { AlertCircle, Lock, ArrowLeft, Sparkles, Check } from "lucide-react";
import { ApiError } from "@/lib/api/client";
import { AnimatedThemeToggler } from "@/components/ui/animated-theme-toggler";

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [demoFilled, setDemoFilled] = useState(false);

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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      const result = await login(email.trim(), password);
      if (result.mfa_required) {
        setErrorMessage("Two-factor authentication is required. Please verify via authenticator app.");
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

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-[var(--bg)] px-4 py-12 relative transition-colors">
      {/* Top Controls */}
      <div className="absolute top-6 left-6 flex items-center gap-3">
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-xs text-muted hover:text-main px-3 py-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] hover:bg-[var(--surface-raised)] transition-all"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Home</span>
        </Link>
      </div>

      <div className="absolute top-6 right-6">
        <AnimatedThemeToggler variant="circle" />
      </div>

      <div className="w-full max-w-sm rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-8 shadow-xl space-y-6 transition-colors">
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-gold/10 border border-gold/30 text-gold mb-1 shadow-xs">
            <Lock className="w-5 h-5" />
          </div>
          <h1 className="font-display text-2xl font-bold tracking-tight text-main">
            XakuFinance
          </h1>
          <p className="text-xs text-muted">
            Track your money. Build your savings. Understand your future.
          </p>
        </div>

        {/* Demo Credentials Quick-Fill Pill */}
        <div className="flex items-center justify-between p-2.5 rounded-xl border border-gold/30 bg-gold/5 text-xs">
          <div className="space-y-0.5">
            <div className="font-medium text-main flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-gold" />
              Demo Account
            </div>
            <div className="text-[11px] text-muted">
              demo@xakufinance.local
            </div>
          </div>
          <button
            type="button"
            onClick={fillDemoCredentials}
            className="px-2.5 py-1 rounded bg-gold text-black text-[11px] font-semibold hover:opacity-90 transition-opacity cursor-pointer flex items-center gap-1"
          >
            {demoFilled ? <Check className="w-3 h-3" /> : null}
            {demoFilled ? "Filled!" : "Fill In"}
          </button>
        </div>

        {errorMessage && (
          <div className="flex items-center gap-2 rounded-lg bg-red-500/10 border border-red-500/20 p-3 text-xs text-negative">
            <AlertCircle className="w-4 h-4 shrink-0 text-negative" />
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
              className="w-full rounded-lg bg-[var(--surface-raised)] border border-[var(--border)] px-3 py-2 text-sm text-main focus:border-[var(--accent)] focus:outline-none transition-colors"
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="text-xs font-medium text-muted">Password</label>
            </div>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••••••"
              className="w-full rounded-lg bg-[var(--surface-raised)] border border-[var(--border)] px-3 py-2 text-sm text-main focus:border-[var(--accent)] focus:outline-none transition-colors"
            />
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded-xl bg-gold py-2.5 text-xs font-semibold text-black cursor-pointer disabled:opacity-50 transition-opacity shadow-sm hover:opacity-95"
          >
            {isSubmitting ? "Signing in..." : "Sign In to Workspace"}
          </button>
        </form>

        <div className="text-center text-xs text-muted border-t border-[var(--border)] pt-4">
          Don't have an account?{" "}
          <Link to="/register" className="text-gold hover:underline font-medium">
            Register here
          </Link>
        </div>
      </div>
    </div>
  );
};
