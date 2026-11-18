import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth-context";
import { AlertCircle, UserPlus } from "lucide-react";
import { ApiError } from "@/lib/api/client";

export const RegisterPage: React.FC = () => {
  const navigate = useNavigate();
  const { register } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [reportingCurrency, setReportingCurrency] = useState("USD");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

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
      navigate("/accounts");
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

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--bg)] px-4 py-12">
      <div className="w-full max-w-sm rounded-xl border border-[var(--border)] bg-[var(--surface)] p-8 shadow-2xl space-y-6">
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-gold/10 border border-gold/30 text-gold mb-1">
            <UserPlus className="w-5 h-5" />
          </div>
          <h1 className="font-display text-2xl font-bold tracking-tight text-main">
            Create Workspace
          </h1>
          <p className="text-xs text-muted">
            Set up your private financial ledger with accounting integrity.
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
            <label className="block text-xs font-medium text-muted mb-1">
              Display Name <span className="text-faint font-normal">(Optional)</span>
            </label>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="Mara"
              className="w-full rounded bg-[var(--surface-raised)] border border-[var(--border)] px-3 py-2 text-sm text-main focus:border-[var(--accent)] focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-muted mb-1">Reporting Currency</label>
            <select
              value={reportingCurrency}
              onChange={(e) => setReportingCurrency(e.target.value)}
              className="w-full rounded bg-[var(--surface-raised)] border border-[var(--border)] px-3 py-2 text-sm text-main focus:border-[var(--accent)] focus:outline-none"
            >
              <option value="USD">USD ($) — United States Dollar</option>
              <option value="KHR">KHR (៛) — Cambodian Riel</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-muted mb-1">
              Password <span className="text-faint font-normal">(Minimum 12 chars)</span>
            </label>
            <input
              type="password"
              required
              minLength={12}
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
            {isSubmitting ? "Creating workspace..." : "Create Account"}
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
  );
};
