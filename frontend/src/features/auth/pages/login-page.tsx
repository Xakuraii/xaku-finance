import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth-context";
import { AlertCircle, Lock } from "lucide-react";
import { ApiError } from "@/lib/api/client";

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      const result = await login(email.trim(), password);
      if (result.mfa_required) {
        setErrorMessage("Two-factor authentication is required. Please verify via authenticator app.");
      } else {
        navigate("/accounts");
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
    <div className="min-h-screen flex items-center justify-center bg-[var(--bg)] px-4 py-12">
      <div className="w-full max-w-sm rounded-xl border border-[var(--border)] bg-[var(--surface)] p-8 shadow-2xl space-y-6">
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-gold/10 border border-gold/30 text-gold mb-1">
            <Lock className="w-5 h-5" />
          </div>
          <h1 className="font-display text-2xl font-bold tracking-tight text-main">
            XakuFinance
          </h1>
          <p className="text-xs text-muted">
            Track your money. Build your savings. Understand your future.
          </p>
        </div>

        {errorMessage && (
          <div className="flex items-center gap-2 rounded bg-red-950/40 border border-red-900/60 p-3 text-xs text-red-200">
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
              className="w-full rounded bg-[var(--surface-raised)] border border-[var(--border)] px-3 py-2 text-sm text-main focus:border-[var(--accent)] focus:outline-none"
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
              className="w-full rounded bg-[var(--surface-raised)] border border-[var(--border)] px-3 py-2 text-sm text-main focus:border-[var(--accent)] focus:outline-none"
            />
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded bg-gold py-2.5 text-xs font-semibold cursor-pointer disabled:opacity-50 transition-colors shadow-xs"
          >
            {isSubmitting ? "Signing in..." : "Sign In"}
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
