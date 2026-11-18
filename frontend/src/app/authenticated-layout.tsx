import React, { useState } from "react";
import { Link, NavLink, Outlet, Navigate } from "react-router-dom";
import { useAuth } from "@/features/auth/auth-context";
import {
  Wallet,
  ArrowLeftRight,
  LogOut,
  Shield,
  PiggyBank,
  BarChart3,
  UploadCloud,
} from "lucide-react";
import { AnimatedThemeToggler } from "@/components/ui/animated-theme-toggler";
import { ImportWizardDialog } from "@/features/imports/components/import-wizard-dialog";
import { useQuery } from "@tanstack/react-query";
import { getAccounts } from "@/features/accounts/api";
import { queryKeys } from "@/lib/query-keys";

export const AuthenticatedLayout: React.FC = () => {
  const { user, workspace, isAuthenticated, isLoading, logout } = useAuth();
  const [isImportOpen, setIsImportOpen] = useState(false);

  const { data: accounts = [] } = useQuery({
    queryKey: queryKeys.accounts.list(false),
    queryFn: () => getAccounts(false),
    enabled: isAuthenticated,
  });

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--bg)] text-xs text-muted">
        <div className="flex flex-col items-center gap-3">
          <div className="w-6 h-6 rounded-full border-2 border-gold border-t-transparent animate-spin" />
          <span>Opening financial workspace...</span>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="min-h-screen flex flex-col bg-[var(--bg)] text-main transition-colors duration-200">
      {/* Top Ledger Navigation Bar */}
      <header className="border-b border-[var(--border)] bg-[var(--surface)] sticky top-0 z-40 shadow-xs backdrop-blur-md">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-8">
            <Link to="/app/accounts" className="flex items-center gap-2.5 group">
              <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[#F0B90B] to-[#D9A600] flex items-center justify-center text-black font-bold shadow-xs group-hover:scale-105 transition-transform">
                <span className="font-display text-sm">X</span>
              </div>
              <span className="font-display font-bold tracking-tight text-main text-lg">
                XakuFinance
              </span>
            </Link>

            <nav className="hidden md:flex items-center gap-1.5">
              <NavLink
                to="/app/accounts"
                className={({ isActive }) =>
                  `flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                    isActive
                      ? "text-gold bg-gold/10 font-semibold border border-gold/20"
                      : "text-muted hover:text-main hover:bg-[var(--surface-raised)]"
                  }`
                }
              >
                <Wallet className="w-3.5 h-3.5" />
                Accounts
              </NavLink>

              <NavLink
                to="/app/transactions"
                className={({ isActive }) =>
                  `flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                    isActive
                      ? "text-gold bg-gold/10 font-semibold border border-gold/20"
                      : "text-muted hover:text-main hover:bg-[var(--surface-raised)]"
                  }`
                }
              >
                <ArrowLeftRight className="w-3.5 h-3.5" />
                Transactions
              </NavLink>

              <NavLink
                to="/app/budgets"
                className={({ isActive }) =>
                  `flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                    isActive
                      ? "text-gold bg-gold/10 font-semibold border border-gold/20"
                      : "text-muted hover:text-main hover:bg-[var(--surface-raised)]"
                  }`
                }
              >
                <PiggyBank className="w-3.5 h-3.5" />
                Budgets
              </NavLink>

              <NavLink
                to="/app/analytics"
                className={({ isActive }) =>
                  `flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                    isActive
                      ? "text-gold bg-gold/10 font-semibold border border-gold/20"
                      : "text-muted hover:text-main hover:bg-[var(--surface-raised)]"
                  }`
                }
              >
                <BarChart3 className="w-3.5 h-3.5" />
                Analytics
              </NavLink>
            </nav>
          </div>

          <div className="flex items-center gap-3">
            {/* Quick CSV Import Trigger */}
            <button
              type="button"
              onClick={() => setIsImportOpen(true)}
              className="hidden lg:inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface-raised)] hover:bg-[var(--surface-hover)] text-xs font-medium text-main transition-colors cursor-pointer"
              title="Import bank statement CSV with column mapping"
            >
              <UploadCloud className="w-3.5 h-3.5 text-gold" />
              <span>Import CSV</span>
            </button>

            {/* Workspace Indicator */}
            {workspace && (
              <span className="hidden sm:inline-flex items-center gap-1 rounded-lg bg-[var(--surface-raised)] border border-[var(--border)] px-2.5 py-1 text-[11px] text-muted font-medium">
                <Shield className="w-3 h-3 text-gold" />
                {workspace.name} ({workspace.reporting_currency})
              </span>
            )}

            {/* View Transitions Animated Theme Toggler */}
            <AnimatedThemeToggler variant="circle" />

            <div className="flex items-center gap-2 pl-2 border-l border-[var(--border)]">
              <span className="text-xs text-muted hidden xl:inline">{user?.email}</span>
              <button
                onClick={logout}
                className="flex items-center gap-1 text-xs text-muted hover:text-negative cursor-pointer transition-colors px-2 py-1 rounded hover:bg-[var(--surface-raised)]"
                title="Sign out of workspace"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Sign Out</span>
              </button>
            </div>
          </div>
        </div>

        {/* Mobile Navigation Strip */}
        <div className="md:hidden border-t border-[var(--border)] px-4 py-2 flex items-center justify-around overflow-x-auto text-xs bg-[var(--surface-raised)]">
          <NavLink
            to="/app/accounts"
            className={({ isActive }) =>
              `flex items-center gap-1 px-2.5 py-1 rounded font-medium ${
                isActive ? "text-gold font-semibold" : "text-muted"
              }`
            }
          >
            <Wallet className="w-3.5 h-3.5" />
            Accounts
          </NavLink>
          <NavLink
            to="/app/transactions"
            className={({ isActive }) =>
              `flex items-center gap-1 px-2.5 py-1 rounded font-medium ${
                isActive ? "text-gold font-semibold" : "text-muted"
              }`
            }
          >
            <ArrowLeftRight className="w-3.5 h-3.5" />
            Transactions
          </NavLink>
          <NavLink
            to="/app/budgets"
            className={({ isActive }) =>
              `flex items-center gap-1 px-2.5 py-1 rounded font-medium ${
                isActive ? "text-gold font-semibold" : "text-muted"
              }`
            }
          >
            <PiggyBank className="w-3.5 h-3.5" />
            Budgets
          </NavLink>
          <NavLink
            to="/app/analytics"
            className={({ isActive }) =>
              `flex items-center gap-1 px-2.5 py-1 rounded font-medium ${
                isActive ? "text-gold font-semibold" : "text-muted"
              }`
            }
          >
            <BarChart3 className="w-3.5 h-3.5" />
            Analytics
          </NavLink>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 py-8">
        <Outlet />
      </main>

      {/* Institutional Ledger Integrity Footer */}
      <footer className="border-t border-[var(--border)] py-4 text-center text-[11px] text-muted flex items-center justify-center gap-2">
        <span className="w-1.5 h-1.5 rounded-full bg-gold" />
        <span>XakuFinance &bull; Double-Entry Accounting Core &bull; 0 Drift Balance Integrity</span>
      </footer>

      {/* Global CSV Statement Import Dialog */}
      <ImportWizardDialog
        open={isImportOpen}
        onOpenChange={setIsImportOpen}
        accounts={accounts}
      />
    </div>
  );
};
