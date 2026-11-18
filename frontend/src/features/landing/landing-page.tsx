import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Shield,
  ArrowRight,
  CheckCircle2,
  Lock,
  ArrowLeftRight,
  Coins,
  Sparkles,
  TrendingUp,
  Receipt,
  FileSpreadsheet,
} from "lucide-react";
import { AnimatedThemeToggler } from "@/components/ui/animated-theme-toggler";
import { useAuth } from "@/features/auth/auth-context";

export const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const { isAuthenticated, login } = useAuth();
  const [isDemoLoggingIn, setIsDemoLoggingIn] = useState(false);
  const [selectedCurrency, setSelectedCurrency] = useState<"USD" | "KHR">("USD");

  const handleInstantDemo = async () => {
    setIsDemoLoggingIn(true);
    try {
      await login("demo@xakufinance.local", "DemoPass123456");
      navigate("/app/accounts");
    } catch {
      // If login fails (e.g. backend offline or changed), redirect to login page with prefill
      navigate("/login?demo=true");
    } finally {
      setIsDemoLoggingIn(false);
    }
  };

  const previewAmount = selectedCurrency === "USD" ? "$13,700.00" : "56,170,000 ៛";
  const safeToSpend = selectedCurrency === "USD" ? "$2,850.00" : "11,685,000 ៛";
  const monthlySavings = selectedCurrency === "USD" ? "+$650.00" : "+2,665,000 ៛";

  return (
    <div className="min-h-screen flex flex-col bg-[var(--bg)] text-main selection:bg-gold/20 selection:text-gold transition-colors duration-300">
      {/* Top Navbar */}
      <header className="sticky top-0 z-50 backdrop-blur-md bg-[var(--surface)]/90 border-b border-[var(--border)] transition-colors">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5 group">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#F0B90B] to-[#D9A600] flex items-center justify-center text-black font-bold shadow-md shadow-gold/20 group-hover:scale-105 transition-transform">
              <span className="font-display text-base">X</span>
            </div>
            <div className="flex flex-col">
              <span className="font-display font-bold tracking-tight text-lg leading-tight text-main">
                XakuFinance
              </span>
              <span className="text-[10px] tracking-wider uppercase text-muted font-medium">
                Double-Entry Ledger
              </span>
            </div>
          </Link>

          <nav className="hidden md:flex items-center gap-6 text-xs font-medium text-muted">
            <a href="#features" className="hover:text-main transition-colors">
              Features
            </a>
            <a href="#architecture" className="hover:text-main transition-colors">
              Ledger Engine
            </a>
            <a href="#security" className="hover:text-main transition-colors">
              Security
            </a>
          </nav>

          <div className="flex items-center gap-3">
            {/* View Transitions Animated Theme Toggler */}
            <AnimatedThemeToggler variant="circle" />

            {isAuthenticated ? (
              <Link
                to="/app/accounts"
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-gold text-xs font-semibold hover:opacity-95 transition-all shadow-sm cursor-pointer"
              >
                Go to App
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            ) : (
              <>
                <button
                  onClick={handleInstantDemo}
                  disabled={isDemoLoggingIn}
                  className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gold/40 bg-gold/10 text-gold hover:bg-gold/20 text-xs font-medium transition-colors cursor-pointer disabled:opacity-50"
                  title="Log in directly with pre-seeded demo workspace"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  {isDemoLoggingIn ? "Loading..." : "Demo Login"}
                </button>

                <Link
                  to="/login"
                  className="px-3.5 py-1.5 rounded-lg border border-[var(--border)] hover:border-[var(--border-strong)] text-xs font-medium text-main hover:bg-[var(--surface-raised)] transition-all"
                >
                  Sign In
                </Link>

                <Link
                  to="/register"
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-gold text-xs font-semibold hover:opacity-95 transition-all shadow-sm cursor-pointer"
                >
                  Get Started
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative overflow-hidden pt-16 pb-20 md:pt-24 md:pb-28 border-b border-[var(--border)]">
        {/* Subtle background glow */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[350px] bg-gold/5 blur-[120px] pointer-events-none rounded-full" />

        <div className="max-w-6xl mx-auto px-4 sm:px-6 relative z-10">
          <div className="text-center max-w-3xl mx-auto space-y-6">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-gold/30 bg-gold/5 text-gold text-xs font-medium shadow-xs">
              <span className="w-1.5 h-1.5 rounded-full bg-gold animate-pulse" />
              <span>Zero Ledger Drift &bull; True Double-Entry Precision</span>
            </div>

            <h1 className="font-display text-4xl sm:text-5xl md:text-6xl font-bold tracking-tight text-main leading-[1.12]">
              Track your money. <br className="hidden sm:inline" />
              <span className="bg-gradient-to-r from-amber-400 via-[#F0B90B] to-yellow-200 bg-clip-text text-transparent">
                Understand your financial future.
              </span>
            </h1>

            <p className="text-base sm:text-lg text-muted max-w-2xl mx-auto font-normal leading-relaxed">
              XakuFinance is not another toy expense tracker. It is a sovereign personal financial
              management system with multi-currency accounting integrity, positive budget rollover,
              and immutable journal entries.
            </p>

            <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
              <button
                onClick={handleInstantDemo}
                disabled={isDemoLoggingIn}
                className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-gold text-sm font-semibold hover:opacity-95 shadow-md shadow-gold/20 transition-all cursor-pointer disabled:opacity-50"
              >
                <Sparkles className="w-4 h-4" />
                {isDemoLoggingIn ? "Opening Demo Workspace..." : "Explore Live Demo"}
              </button>

              <Link
                to="/register"
                className="inline-flex items-center gap-2 px-6 py-3 rounded-xl border border-[var(--border)] bg-[var(--surface)] hover:bg-[var(--surface-raised)] text-sm font-medium text-main transition-all shadow-xs"
              >
                Create Free Workspace
                <ArrowRight className="w-4 h-4 text-muted" />
              </Link>
            </div>

            <div className="flex items-center justify-center gap-6 pt-4 text-xs text-muted">
              <span className="flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-positive" />
                No credit card required
              </span>
              <span className="flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-positive" />
                Instant local seeding
              </span>
              <span className="flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-positive" />
                USD &amp; KHR dual currency
              </span>
            </div>
          </div>

          {/* Interactive Hero Preview Component */}
          <div className="mt-14 max-w-4xl mx-auto rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6 sm:p-8 shadow-2xl relative">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-6 border-b border-[var(--border)]">
              <div>
                <span className="text-xs uppercase tracking-wider text-muted font-medium">
                  Authoritative Workspace Overview
                </span>
                <div className="flex items-center gap-3 mt-1">
                  <h3 className="font-display text-3xl font-bold text-main">
                    {previewAmount}
                  </h3>
                  <div className="flex items-center rounded-lg border border-[var(--border)] bg-[var(--surface-raised)] p-0.5 text-xs">
                    <button
                      onClick={() => setSelectedCurrency("USD")}
                      className={`px-2 py-0.5 rounded font-medium transition-colors ${
                        selectedCurrency === "USD"
                          ? "bg-gold text-black font-semibold"
                          : "text-muted hover:text-main"
                      }`}
                    >
                      USD
                    </button>
                    <button
                      onClick={() => setSelectedCurrency("KHR")}
                      className={`px-2 py-0.5 rounded font-medium transition-colors ${
                        selectedCurrency === "KHR"
                          ? "bg-gold text-black font-semibold"
                          : "text-muted hover:text-main"
                      }`}
                    >
                      KHR
                    </button>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-positive text-xs font-medium">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                Double-Entry Ledger Reconciled (0 Drift)
              </div>
            </div>

            {/* Metrics Row */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 py-6 border-b border-[var(--border)]">
              <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-raised)] p-4">
                <div className="flex items-center justify-between text-xs text-muted mb-1">
                  <span>Safe-to-Spend</span>
                  <TrendingUp className="w-3.5 h-3.5 text-gold" />
                </div>
                <div className="text-xl font-bold font-tabular text-main">
                  {safeToSpend}
                </div>
                <p className="text-[11px] text-muted mt-1">Checking &amp; Cash Wallets</p>
              </div>

              <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-raised)] p-4">
                <div className="flex items-center justify-between text-xs text-muted mb-1">
                  <span>Emergency Fund</span>
                  <Shield className="w-3.5 h-3.5 text-positive" />
                </div>
                <div className="text-xl font-bold font-tabular text-positive">
                  {selectedCurrency === "USD" ? "$10,000.00" : "41,000,000 ៛"}
                </div>
                <p className="text-[11px] text-muted mt-1">Isolated from daily spending</p>
              </div>

              <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-raised)] p-4">
                <div className="flex items-center justify-between text-xs text-muted mb-1">
                  <span>Rollover Surplus</span>
                  <Coins className="w-3.5 h-3.5 text-sky-400" />
                </div>
                <div className="text-xl font-bold font-tabular text-sky-400">
                  {monthlySavings}
                </div>
                <p className="text-[11px] text-muted mt-1">Carried forward to next month</p>
              </div>
            </div>

            {/* Simulated Live Journal Entries */}
            <div className="pt-6">
              <div className="flex items-center justify-between text-xs mb-3">
                <span className="font-semibold text-main uppercase tracking-wider text-[11px]">
                  Recent Journal Postings
                </span>
                <span className="text-muted text-[11px]">Audit-logged &bull; Soft-archived</span>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between p-3 rounded-lg border border-[var(--border)] bg-[var(--surface-raised)] text-xs">
                  <div className="flex items-center gap-3">
                    <div className="w-7 h-7 rounded bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400 font-bold text-[11px]">
                      GF
                    </div>
                    <div>
                      <div className="font-medium text-main">Whole Foods Groceries (Split)</div>
                      <div className="text-[11px] text-muted">
                        Primary Checking &bull; Groceries ($65.50) + Home Supplies ($24.00)
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="font-tabular font-semibold text-negative">-$89.50</span>
                    <div className="text-[10px] text-emerald-400">Essential</div>
                  </div>
                </div>

                <div className="flex items-center justify-between p-3 rounded-lg border border-[var(--border)] bg-[var(--surface-raised)] text-xs">
                  <div className="flex items-center gap-3">
                    <div className="w-7 h-7 rounded bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 font-bold text-[11px]">
                      TX
                    </div>
                    <div>
                      <div className="font-medium text-main">Salary Direct Deposit</div>
                      <div className="text-[11px] text-muted">
                        Primary Checking &bull; Income Posting
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="font-tabular font-semibold text-positive">+$3,500.00</span>
                    <div className="text-[10px] text-muted">Cleared</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Feature Grid Section */}
      <section id="features" className="py-20 border-b border-[var(--border)]">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="text-center max-w-2xl mx-auto mb-16 space-y-3">
            <h2 className="font-display text-3xl sm:text-4xl font-bold tracking-tight text-main">
              Built for Financial Accuracy
            </h2>
            <p className="text-sm text-muted">
              Every design decision prioritizes accounting rigor, auditability, and clear visual hierarchy.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Card 1 */}
            <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 hover:border-gold/40 transition-colors group">
              <div className="w-10 h-10 rounded-lg bg-gold/10 border border-gold/20 flex items-center justify-center text-gold mb-4 group-hover:scale-105 transition-transform">
                <Shield className="w-5 h-5" />
              </div>
              <h3 className="font-semibold text-base text-main mb-2">
                Double-Entry Ledger Core
              </h3>
              <p className="text-xs text-muted leading-relaxed">
                Every transaction generates balanced debit and credit entries. Balances are derived from immutable journal entries, guaranteeing 0 minor unit drift.
              </p>
            </div>

            {/* Card 2 */}
            <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 hover:border-gold/40 transition-colors group">
              <div className="w-10 h-10 rounded-lg bg-gold/10 border border-gold/20 flex items-center justify-center text-gold mb-4 group-hover:scale-105 transition-transform">
                <Receipt className="w-5 h-5" />
              </div>
              <h3 className="font-semibold text-base text-main mb-2">
                Multi-Category Split Allocations
              </h3>
              <p className="text-xs text-muted leading-relaxed">
                Split a single receipt into multiple categories and tags with penny-level validation. Track essentials vs. lifestyle spending accurately.
              </p>
            </div>

            {/* Card 3 */}
            <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 hover:border-gold/40 transition-colors group">
              <div className="w-10 h-10 rounded-lg bg-gold/10 border border-gold/20 flex items-center justify-center text-gold mb-4 group-hover:scale-105 transition-transform">
                <TrendingUp className="w-5 h-5" />
              </div>
              <h3 className="font-semibold text-base text-main mb-2">
                Positive-Only Budget Rollover
              </h3>
              <p className="text-xs text-muted leading-relaxed">
                Reward good financial discipline. Unused budget rolls forward into next month; overspending is contained to prevent cascading debt.
              </p>
            </div>

            {/* Card 4 */}
            <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 hover:border-gold/40 transition-colors group">
              <div className="w-10 h-10 rounded-lg bg-gold/10 border border-gold/20 flex items-center justify-center text-gold mb-4 group-hover:scale-105 transition-transform">
                <ArrowLeftRight className="w-5 h-5" />
              </div>
              <h3 className="font-semibold text-base text-main mb-2">
                FX Transfers &amp; Multi-Currency
              </h3>
              <p className="text-xs text-muted leading-relaxed">
                Transfer seamlessly between USD and Cambodian Riel (KHR) accounts with transparent exchange rate calculations and zero phantom money creation.
              </p>
            </div>

            {/* Card 5 */}
            <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 hover:border-gold/40 transition-colors group">
              <div className="w-10 h-10 rounded-lg bg-gold/10 border border-gold/20 flex items-center justify-center text-gold mb-4 group-hover:scale-105 transition-transform">
                <FileSpreadsheet className="w-5 h-5" />
              </div>
              <h3 className="font-semibold text-base text-main mb-2">
                Bank Statement CSV Import
              </h3>
              <p className="text-xs text-muted leading-relaxed">
                4-step import wizard with auto-detected column mapping, fuzzy duplicate detection scoring, and atomic commit preview.
              </p>
            </div>

            {/* Card 6 */}
            <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 hover:border-gold/40 transition-colors group">
              <div className="w-10 h-10 rounded-lg bg-gold/10 border border-gold/20 flex items-center justify-center text-gold mb-4 group-hover:scale-105 transition-transform">
                <Lock className="w-5 h-5" />
              </div>
              <h3 className="font-semibold text-base text-main mb-2">
                Sovereign Security &amp; 2FA
              </h3>
              <p className="text-xs text-muted leading-relaxed">
                TOTP authenticator app support (RFC 6238), progressive brute-force lockout, single-use recovery codes, and strict workspace boundary isolation.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-[var(--surface)] relative overflow-hidden">
        <div className="max-w-4xl mx-auto px-4 text-center space-y-6">
          <h2 className="font-display text-3xl sm:text-4xl font-bold tracking-tight text-main">
            Ready to take complete control of your finances?
          </h2>
          <p className="text-sm text-muted max-w-xl mx-auto">
            Experience the clarity and confidence that comes with institution-grade double-entry financial tracking.
          </p>

          <div className="flex flex-wrap items-center justify-center gap-3 pt-4">
            <button
              onClick={handleInstantDemo}
              disabled={isDemoLoggingIn}
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-gold text-sm font-semibold hover:opacity-95 shadow-md shadow-gold/20 transition-all cursor-pointer disabled:opacity-50"
            >
              <Sparkles className="w-4 h-4" />
              {isDemoLoggingIn ? "Logging in..." : "Try Demo Now (Instant Access)"}
            </button>

            <Link
              to="/register"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl border border-[var(--border)] bg-[var(--surface-raised)] hover:bg-[var(--surface-hover)] text-sm font-medium text-main transition-all"
            >
              Register New Account
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-[var(--border)] py-8 text-xs text-muted bg-[var(--bg)]">
        <div className="max-w-6xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-gold" />
            <span className="font-display font-semibold text-main">XakuFinance</span>
            <span>&bull;</span>
            <span>Ledger Integrity Standard</span>
          </div>

          <div className="flex items-center gap-6">
            <a href="http://127.0.0.1:8000/api/docs/" target="_blank" rel="noreferrer" className="hover:text-main transition-colors">
              API Docs
            </a>
            <a href="http://127.0.0.1:8000/health/ready" target="_blank" rel="noreferrer" className="hover:text-main transition-colors">
              System Status
            </a>
            <Link to="/login" className="hover:text-main transition-colors">
              Login
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
};
