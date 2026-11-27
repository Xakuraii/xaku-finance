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
  BookOpen,
  Layers,
} from "lucide-react";
import { AnimatedThemeToggler } from "@/components/ui/animated-theme-toggler";
import { BrandLogo } from "@/components/brand-logo";
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
      navigate("/login?demo=true");
    } finally {
      setIsDemoLoggingIn(false);
    }
  };

  const previewAmount = selectedCurrency === "USD" ? "$13,700.00" : "56,170,000 ៛";
  const safeToSpend = selectedCurrency === "USD" ? "$2,850.00" : "11,685,000 ៛";
  const monthlySavings = selectedCurrency === "USD" ? "+$650.00" : "+2,665,000 ៛";

  return (
    <div className="min-h-screen flex flex-col bg-[var(--bg)] text-[var(--text)] selection:bg-[var(--accent)]/20 selection:text-[var(--accent-text)] transition-colors duration-300">
      {/* Top Navbar */}
      <header className="sticky top-0 z-50 backdrop-blur-md bg-[var(--surface)]/90 border-b border-[var(--border)] transition-colors">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center group">
            <BrandLogo
              iconClassName="w-10 h-10 sm:w-12 sm:h-12 group-hover:scale-105 transition-transform"
              textClassName="text-xl sm:text-2xl"
            />
          </Link>

          <nav className="hidden md:flex items-center gap-6 text-xs font-medium text-[var(--text-muted)]">
            <a href="#features" className="hover:text-[var(--text)] transition-colors">
              Features
            </a>
            <a href="#architecture" className="hover:text-[var(--text)] transition-colors">
              Ledger Engine
            </a>
            <a href="#security" className="hover:text-[var(--text)] transition-colors">
              Security
            </a>
          </nav>

          <div className="flex items-center gap-3">
            <AnimatedThemeToggler variant="circle" />

            {isAuthenticated ? (
              <Link
                to="/app/accounts"
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[var(--accent)] text-xs font-semibold text-[var(--on-accent)] hover:opacity-95 transition-all shadow-sm cursor-pointer"
              >
                Go to App
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            ) : (
              <>
                <button
                  onClick={handleInstantDemo}
                  disabled={isDemoLoggingIn}
                  className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[var(--accent)]/40 bg-[var(--accent)]/10 text-[var(--accent-text)] hover:bg-[var(--accent)]/20 text-xs font-medium transition-colors cursor-pointer disabled:opacity-50"
                  title="Log in directly with pre-seeded demo workspace"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  {isDemoLoggingIn ? "Loading..." : "Demo Login"}
                </button>

                <Link
                  to="/login"
                  className="px-3.5 py-1.5 rounded-lg border border-[var(--border)] hover:border-[var(--border-strong)] text-xs font-medium text-[var(--text)] hover:bg-[var(--surface-raised)] transition-all"
                >
                  Sign In
                </Link>

                <Link
                  to="/register"
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-[var(--accent)] text-xs font-semibold text-[var(--on-accent)] hover:opacity-95 transition-all shadow-sm cursor-pointer"
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
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[350px] bg-[var(--accent)]/5 blur-[120px] pointer-events-none rounded-full" />

        <div className="max-w-6xl mx-auto px-4 sm:px-6 relative z-10">
          <div className="text-center max-w-3xl mx-auto space-y-6">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-[var(--accent)]/30 bg-[var(--accent)]/5 text-[var(--accent-text)] text-xs font-medium shadow-xs">
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent)] animate-pulse" />
              <span>Zero Ledger Drift · True Double-Entry Precision</span>
            </div>

            <h1 className="font-display text-4xl sm:text-5xl md:text-6xl font-bold tracking-tight text-[var(--text)] leading-[1.12]">
              Track your money.{" "}
              <br className="hidden sm:inline" />
              <span className="bg-gradient-to-r from-amber-600 via-amber-500 to-amber-700 dark:from-amber-400 dark:via-[#F0B90B] dark:to-yellow-200 bg-clip-text text-transparent">
                Understand your financial future.
              </span>
            </h1>

            <p className="text-base sm:text-lg text-[var(--text-muted)] max-w-2xl mx-auto font-normal leading-relaxed">
              XakuFinance is not another toy expense tracker. It is a sovereign personal financial
              management system with multi-currency accounting integrity, positive budget rollover,
              and immutable journal entries.
            </p>

            <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
              <button
                onClick={handleInstantDemo}
                disabled={isDemoLoggingIn}
                className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-[var(--accent)] text-sm font-semibold text-[var(--on-accent)] hover:opacity-95 shadow-md shadow-[var(--accent)]/20 transition-all cursor-pointer disabled:opacity-50"
              >
                <Sparkles className="w-4 h-4" />
                {isDemoLoggingIn ? "Opening Demo Workspace..." : "Explore Live Demo"}
              </button>

              <Link
                to="/register"
                className="inline-flex items-center gap-2 px-6 py-3 rounded-xl border border-[var(--border)] bg-[var(--surface)] hover:bg-[var(--surface-raised)] text-sm font-medium text-[var(--text)] transition-all shadow-xs"
              >
                Create Free Workspace
              </Link>
            </div>

            <div className="flex items-center justify-center gap-6 pt-4 text-xs text-[var(--text-muted)]">
              <span className="flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-[var(--positive)]" />
                No credit card required
              </span>
              <span className="flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-[var(--positive)]" />
                Instant local seeding
              </span>
              <span className="flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-[var(--positive)]" />
                USD &amp; KHR dual currency
              </span>
            </div>
          </div>

          {/* Interactive Hero Preview Component */}
          <div className="mt-14 max-w-4xl mx-auto rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6 sm:p-8 shadow-2xl relative">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-6 border-b border-[var(--border)]">
              <div>
                <p className="text-xs text-[var(--text-faint)] font-medium mb-1">
                  Authoritative Workspace Overview
                </p>
                <div className="flex items-center gap-3 mt-1">
                  <h3 className="font-display text-3xl font-bold text-[var(--text)]">
                    {previewAmount}
                  </h3>
                  <div className="flex items-center rounded-lg border border-[var(--border)] bg-[var(--surface-raised)] p-0.5 text-xs">
                    <button
                      onClick={() => setSelectedCurrency("USD")}
                      className={`px-2 py-0.5 rounded font-medium transition-colors ${
                        selectedCurrency === "USD"
                          ? "bg-[var(--accent)] text-[var(--on-accent)] font-semibold"
                          : "text-[var(--text-muted)] hover:text-[var(--text)]"
                      }`}
                    >
                      USD
                    </button>
                    <button
                      onClick={() => setSelectedCurrency("KHR")}
                      className={`px-2 py-0.5 rounded font-medium transition-colors ${
                        selectedCurrency === "KHR"
                          ? "bg-[var(--accent)] text-[var(--on-accent)] font-semibold"
                          : "text-[var(--text-muted)] hover:text-[var(--text)]"
                      }`}
                    >
                      KHR
                    </button>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-[var(--positive-bg)] border border-[var(--positive)]/20 text-[var(--positive)] text-xs font-medium">
                <span className="w-2 h-2 rounded-full bg-[var(--positive)] animate-pulse" />
                Double-Entry Reconciled · 0 Drift
              </div>
            </div>

            {/* Metrics Row */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 py-6 border-b border-[var(--border)]">
              <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-raised)] p-4">
                <div className="flex items-center justify-between text-xs text-[var(--text-muted)] mb-1">
                  <span>Safe-to-Spend</span>
                  <TrendingUp className="w-3.5 h-3.5 text-[var(--accent-text)]" />
                </div>
                <div className="text-xl font-bold font-tabular text-[var(--text)]">
                  {safeToSpend}
                </div>
                <p className="text-[11px] text-[var(--text-faint)] mt-1">Checking &amp; Cash Wallets</p>
              </div>

              <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-raised)] p-4">
                <div className="flex items-center justify-between text-xs text-[var(--text-muted)] mb-1">
                  <span>Emergency Fund</span>
                  <Shield className="w-3.5 h-3.5 text-[var(--positive)]" />
                </div>
                <div className="text-xl font-bold font-tabular text-[var(--positive)]">
                  {selectedCurrency === "USD" ? "$10,000.00" : "41,000,000 ៛"}
                </div>
                <p className="text-[11px] text-[var(--text-faint)] mt-1">Isolated from daily spending</p>
              </div>

              <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-raised)] p-4">
                <div className="flex items-center justify-between text-xs text-[var(--text-muted)] mb-1">
                  <span>Rollover Surplus</span>
                  <Coins className="w-3.5 h-3.5 text-[var(--info)]" />
                </div>
                <div className="text-xl font-bold font-tabular text-[var(--info)]">
                  {monthlySavings}
                </div>
                <p className="text-[11px] text-[var(--text-faint)] mt-1">Carried forward to next month</p>
              </div>
            </div>

            {/* Simulated Live Journal Entries */}
            <div className="pt-6">
              <div className="flex items-center justify-between text-xs mb-3">
                <span className="font-semibold text-[var(--text)] text-[11px]">
                  Recent Journal Postings
                </span>
                <span className="text-[var(--text-faint)] text-[11px]">Audit-logged · Soft-archived</span>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between p-3 rounded-lg border border-[var(--border)] bg-[var(--surface-raised)] text-xs">
                  <div className="flex items-center gap-3">
                    <div className="w-7 h-7 rounded bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-[var(--accent-text)] font-bold text-[11px] shrink-0">
                      GF
                    </div>
                    <div>
                      <div className="font-medium text-[var(--text)]">Whole Foods Groceries (Split)</div>
                      <div className="text-[11px] text-[var(--text-faint)]">
                        Primary Checking · Groceries ($65.50) + Home Supplies ($24.00)
                      </div>
                    </div>
                  </div>
                  <div className="text-right shrink-0 ml-3">
                    <span className="font-tabular font-semibold text-[var(--negative)]">-$89.50</span>
                    <div className="text-[10px] text-[var(--positive)]">Essential</div>
                  </div>
                </div>

                <div className="flex items-center justify-between p-3 rounded-lg border border-[var(--border)] bg-[var(--surface-raised)] text-xs">
                  <div className="flex items-center gap-3">
                    <div className="w-7 h-7 rounded bg-[var(--positive-bg)] border border-[var(--positive)]/20 flex items-center justify-center text-[var(--positive)] font-bold text-[11px] shrink-0">
                      TX
                    </div>
                    <div>
                      <div className="font-medium text-[var(--text)]">Salary Direct Deposit</div>
                      <div className="text-[11px] text-[var(--text-faint)]">
                        Primary Checking · Income Posting
                      </div>
                    </div>
                  </div>
                  <div className="text-right shrink-0 ml-3">
                    <span className="font-tabular font-semibold text-[var(--positive)]">+$3,500.00</span>
                    <div className="text-[10px] text-[var(--text-faint)]">Cleared</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Feature Grid Section — asymmetric layout */}
      <section id="features" className="py-20 border-b border-[var(--border)]">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="mb-14">
            <h2 className="font-display text-3xl sm:text-4xl font-bold tracking-tight text-[var(--text)]">
              Built for Financial Accuracy
            </h2>
            <p className="text-sm text-[var(--text-muted)] mt-3 max-w-xl">
              Every design decision prioritizes accounting rigor, auditability, and clear visual hierarchy.
            </p>
          </div>

          {/* Top row: 2 large + 1 tall */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {/* Large featured card — left */}
            <div className="md:col-span-2 rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-7 hover:border-[var(--accent)]/40 transition-colors group relative overflow-hidden">
              <div className="absolute right-0 top-0 w-40 h-40 bg-[var(--accent)]/3 rounded-full blur-3xl pointer-events-none" />
              <div className="w-11 h-11 rounded-xl bg-[var(--accent)]/10 border border-[var(--accent)]/20 flex items-center justify-center text-[var(--accent-text)] mb-5">
                <BookOpen className="w-5 h-5" />
              </div>
              <h3 className="font-semibold text-lg text-[var(--text)] mb-2">
                Double-Entry Ledger Core
              </h3>
              <p className="text-sm text-[var(--text-muted)] leading-relaxed">
                Every transaction generates balanced debit and credit entries. Balances are derived
                from immutable journal entries, guaranteeing 0 minor unit drift. This is the same
                accounting model used by every serious financial institution on the planet.
              </p>
              <div className="mt-5 flex gap-2 flex-wrap">
                {["Immutable entries", "Zero drift", "Audit trail"].map((tag) => (
                  <span
                    key={tag}
                    className="inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-medium bg-[var(--accent)]/8 text-[var(--accent-text)] border border-[var(--accent)]/20"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>

            {/* Tall right card */}
            <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-7 hover:border-[var(--positive)]/40 transition-colors group flex flex-col">
              <div className="w-11 h-11 rounded-xl bg-[var(--positive-bg)] border border-[var(--positive)]/20 flex items-center justify-center text-[var(--positive)] mb-5">
                <TrendingUp className="w-5 h-5" />
              </div>
              <h3 className="font-semibold text-base text-[var(--text)] mb-2">
                Positive-Only Budget Rollover
              </h3>
              <p className="text-xs text-[var(--text-muted)] leading-relaxed flex-1">
                Reward good financial discipline. Unused budget rolls forward into next month;
                overspending is contained to prevent cascading debt.
              </p>
              <div className="mt-4 p-3 rounded-lg bg-[var(--surface-raised)] border border-[var(--border)]">
                <div className="text-[11px] text-[var(--text-faint)] mb-1">Nov rollover surplus</div>
                <div className="text-base font-bold font-tabular text-[var(--positive)]">+$245.00</div>
              </div>
            </div>

            {/* Bottom row: 3 equal */}
            <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6 hover:border-[var(--accent)]/40 transition-colors group">
              <div className="w-10 h-10 rounded-xl bg-[var(--accent)]/10 border border-[var(--accent)]/20 flex items-center justify-center text-[var(--accent-text)] mb-4">
                <Receipt className="w-5 h-5" />
              </div>
              <h3 className="font-semibold text-sm text-[var(--text)] mb-1.5">
                Multi-Category Split Allocations
              </h3>
              <p className="text-xs text-[var(--text-muted)] leading-relaxed">
                Split a single receipt into multiple categories with penny-level validation.
              </p>
            </div>

            <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6 hover:border-[var(--info)]/40 transition-colors group">
              <div className="w-10 h-10 rounded-xl bg-[var(--info)]/10 border border-[var(--info)]/20 flex items-center justify-center text-[var(--info)] mb-4">
                <ArrowLeftRight className="w-5 h-5" />
              </div>
              <h3 className="font-semibold text-sm text-[var(--text)] mb-1.5">
                FX Transfers &amp; Multi-Currency
              </h3>
              <p className="text-xs text-[var(--text-muted)] leading-relaxed">
                Seamless USD ↔ KHR transfers with transparent exchange rates. Zero phantom money.
              </p>
            </div>

            <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6 hover:border-[var(--accent)]/40 transition-colors group">
              <div className="w-10 h-10 rounded-xl bg-[var(--accent)]/10 border border-[var(--accent)]/20 flex items-center justify-center text-[var(--accent-text)] mb-4">
                <FileSpreadsheet className="w-5 h-5" />
              </div>
              <h3 className="font-semibold text-sm text-[var(--text)] mb-1.5">
                Bank Statement CSV Import
              </h3>
              <p className="text-xs text-[var(--text-muted)] leading-relaxed">
                4-step wizard with auto-detected column mapping and fuzzy duplicate detection.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Architecture / Ledger Engine Section */}
      <section id="architecture" className="py-20 border-b border-[var(--border)] bg-[var(--surface)]">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
            <div className="space-y-5">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-[var(--accent)]/30 bg-[var(--accent)]/5 text-[var(--accent-text)] text-xs font-medium">
                <Layers className="w-3.5 h-3.5" />
                Ledger Engine
              </div>
              <h2 className="font-display text-3xl font-bold tracking-tight text-[var(--text)]">
                Not a simple sum of rows.
              </h2>
              <p className="text-sm text-[var(--text-muted)] leading-relaxed">
                Every balance in XakuFinance is computed from an immutable double-entry journal. When
                you record an expense, two journal entries are created: a debit to the expense account
                and a credit to your asset account. The sum of all debits always equals the sum of all
                credits — guaranteed at the database constraint level.
              </p>
              <ul className="space-y-3">
                {[
                  "Database-enforced balance invariants",
                  "Minor-unit integer arithmetic (no float rounding)",
                  "Soft-delete with full audit history",
                  "Idempotent period close operations",
                ].map((item) => (
                  <li key={item} className="flex items-start gap-2.5 text-sm text-[var(--text-muted)]">
                    <CheckCircle2 className="w-4 h-4 text-[var(--positive)] shrink-0 mt-0.5" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>

            {/* Code-like display block */}
            <div className="rounded-xl border border-[var(--border)] bg-[var(--bg)] p-5 font-mono text-xs space-y-2 text-[var(--text-muted)]">
              <div className="text-[var(--text-faint)] text-[11px] mb-3">// Journal Entry Example</div>
              <div>
                <span className="text-[var(--accent-text)]">DR</span>{" "}
                <span className="text-[var(--text)]">Expenses:Groceries</span>
                <span className="ml-auto float-right text-[var(--text)]">$89.50</span>
              </div>
              <div>
                <span className="text-[var(--positive)]">CR</span>{" "}
                <span className="text-[var(--text)]">Assets:Checking</span>
                <span className="ml-auto float-right text-[var(--text)]">$89.50</span>
              </div>
              <div className="border-t border-[var(--border)] pt-2 mt-2 flex justify-between">
                <span>Balance check</span>
                <span className="text-[var(--positive)] font-semibold">✓ 0 drift</span>
              </div>
              <div className="border-t border-[var(--border)] pt-2 mt-2 text-[11px] space-y-1 text-[var(--text-faint)]">
                <div className="flex justify-between">
                  <span>entry_id</span>
                  <span>jrn_a4f9c...</span>
                </div>
                <div className="flex justify-between">
                  <span>version</span>
                  <span>v1 (immutable)</span>
                </div>
                <div className="flex justify-between">
                  <span>split</span>
                  <span>Groceries $65.50 / Home $24.00</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Security Section */}
      <section id="security" className="py-20 border-b border-[var(--border)]">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 text-center">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-[var(--positive-bg)] border border-[var(--positive)]/20 text-[var(--positive)] mb-6">
            <Lock className="w-6 h-6" />
          </div>
          <h2 className="font-display text-3xl sm:text-4xl font-bold tracking-tight text-[var(--text)] mb-4">
            Sovereign Security &amp; 2FA
          </h2>
          <p className="text-sm text-[var(--text-muted)] max-w-2xl mx-auto leading-relaxed">
            TOTP authenticator app support (RFC 6238), progressive brute-force lockout, single-use
            recovery codes, and strict workspace boundary isolation.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-5 mt-10 max-w-3xl mx-auto">
            {[
              { label: "TOTP 2FA", desc: "RFC 6238 authenticator app support" },
              { label: "Brute-Force Lock", desc: "Progressive lockout on failed attempts" },
              { label: "Recovery Codes", desc: "10 single-use emergency codes" },
            ].map((item) => (
              <div
                key={item.label}
                className="p-5 rounded-xl border border-[var(--border)] bg-[var(--surface)] text-left"
              >
                <div className="text-sm font-semibold text-[var(--text)] mb-1">{item.label}</div>
                <div className="text-xs text-[var(--text-muted)]">{item.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-[var(--surface)] relative overflow-hidden">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[300px] bg-[var(--accent)]/5 blur-[100px] pointer-events-none rounded-full" />
        <div className="max-w-4xl mx-auto px-4 text-center space-y-6 relative z-10">
          <h2 className="font-display text-3xl sm:text-4xl font-bold tracking-tight text-[var(--text)]">
            Ready to take complete control of your finances?
          </h2>
          <p className="text-sm text-[var(--text-muted)] max-w-xl mx-auto">
            Experience the clarity and confidence that comes with institution-grade double-entry
            financial tracking.
          </p>

          <div className="flex flex-wrap items-center justify-center gap-3 pt-4">
            <button
              onClick={handleInstantDemo}
              disabled={isDemoLoggingIn}
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-[var(--accent)] text-sm font-semibold text-[var(--on-accent)] hover:opacity-95 shadow-md shadow-[var(--accent)]/20 transition-all cursor-pointer disabled:opacity-50"
            >
              <Sparkles className="w-4 h-4" />
              {isDemoLoggingIn ? "Logging in..." : "Try Demo Now (Instant Access)"}
            </button>

            <Link
              to="/register"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl border border-[var(--border)] bg-[var(--surface-raised)] hover:bg-[var(--surface-hover)] text-sm font-medium text-[var(--text)] transition-all"
            >
              Register New Account
            </Link>
          </div>
        </div>
      </section>

      {/* Institutional 4-Column Footer */}
      <footer className="border-t border-[var(--border)] py-12 text-xs text-[var(--text-muted)] bg-[var(--bg)]">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 space-y-10">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
            <div className="space-y-3">
              <BrandLogo
                iconClassName="w-10 h-10 sm:w-12 sm:h-12"
                textClassName="text-lg sm:text-xl"
              />
              <p className="text-[11px] text-[var(--text-faint)] leading-relaxed">
                Sovereign personal financial management built on an immutable double-entry ledger core with strict balance invariants.
              </p>
            </div>

            <div className="space-y-2.5">
              <div className="font-semibold text-[var(--text)]">Core Ledger Modules</div>
              <ul className="space-y-1.5 text-[11px] text-[var(--text-faint)]">
                <li>
                  <a href="#features" className="hover:text-[var(--text)] transition-colors">
                    Double-Entry Accounts
                  </a>
                </li>
                <li>
                  <a href="#features" className="hover:text-[var(--text)] transition-colors">
                    Multi-Category Splits
                  </a>
                </li>
                <li>
                  <a href="#features" className="hover:text-[var(--text)] transition-colors">
                    USD &amp; KHR FX Transfers
                  </a>
                </li>
                <li>
                  <a href="#features" className="hover:text-[var(--text)] transition-colors">
                    Bank Statement CSV Import
                  </a>
                </li>
              </ul>
            </div>

            <div className="space-y-2.5">
              <div className="font-semibold text-[var(--text)]">Planning &amp; Analytics</div>
              <ul className="space-y-1.5 text-[11px] text-[var(--text-faint)]">
                <li>
                  <a href="#features" className="hover:text-[var(--text)] transition-colors">
                    Positive-Only Budget Rollover
                  </a>
                </li>
                <li>
                  <a href="#architecture" className="hover:text-[var(--text)] transition-colors">
                    Safe-to-Spend &amp; Pacing
                  </a>
                </li>
                <li>
                  <a href="#architecture" className="hover:text-[var(--text)] transition-colors">
                    Savings Goals &amp; Debt Payoff
                  </a>
                </li>
                <li>
                  <a href="#architecture" className="hover:text-[var(--text)] transition-colors">
                    Emergency Runway Planner
                  </a>
                </li>
              </ul>
            </div>

            <div className="space-y-2.5">
              <div className="font-semibold text-[var(--text)]">Security &amp; Access</div>
              <ul className="space-y-1.5 text-[11px] text-[var(--text-faint)]">
                <li>
                  <a href="#security" className="hover:text-[var(--text)] transition-colors">
                    RFC 6238 TOTP Two-Factor
                  </a>
                </li>
                <li>
                  <a href="#security" className="hover:text-[var(--text)] transition-colors">
                    Emergency Recovery Codes
                  </a>
                </li>
                <li>
                  <Link to="/login" className="hover:text-[var(--text)] transition-colors">
                    Sign In to Workspace
                  </Link>
                </li>
                <li>
                  <Link to="/register" className="hover:text-[var(--text)] transition-colors">
                    Create Workspace
                  </Link>
                </li>
              </ul>
            </div>
          </div>

          <div className="pt-6 border-t border-[var(--border)] flex flex-col sm:flex-row items-center justify-between gap-3 text-[11px] text-[var(--text-faint)]">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[var(--accent)]" />
              <span>XakuFinance · Immutable Double-Entry Journal Architecture</span>
            </div>
            <div className="font-mono">0 Minor-Unit Drift Standard</div>
          </div>
        </div>
      </footer>
    </div>
  );
};
