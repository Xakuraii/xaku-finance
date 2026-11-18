import React from "react";
import { Link, NavLink, Outlet, Navigate } from "react-router-dom";
import { useAuth } from "@/features/auth/auth-context";
import { Wallet, ArrowLeftRight, LogOut, Shield } from "lucide-react";

export const AuthenticatedLayout: React.FC = () => {
  const { user, workspace, isAuthenticated, isLoading, logout } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--bg)] text-xs text-muted">
        Loading financial workspace...
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="min-h-screen flex flex-col bg-[var(--bg)] text-main">
      {/* Top Ledger Navigation */}
      <header className="border-b border-[var(--border)] bg-[var(--surface)] sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <Link to="/accounts" className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-gold" />
              <span className="font-display font-bold tracking-tight text-main text-lg">
                XakuFinance
              </span>
            </Link>

            <nav className="flex items-center gap-1">
              <NavLink
                to="/accounts"
                className={({ isActive }) =>
                  `flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                    isActive
                      ? "text-gold bg-gold/10 font-semibold"
                      : "text-muted hover:text-main hover:bg-[var(--surface-raised)]"
                  }`
                }
              >
                <Wallet className="w-3.5 h-3.5" />
                Accounts
              </NavLink>

              <NavLink
                to="/transactions"
                className={({ isActive }) =>
                  `flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                    isActive
                      ? "text-gold bg-gold/10 font-semibold"
                      : "text-muted hover:text-main hover:bg-[var(--surface-raised)]"
                  }`
                }
              >
                <ArrowLeftRight className="w-3.5 h-3.5" />
                Transactions
              </NavLink>
            </nav>
          </div>

          <div className="flex items-center gap-4 text-xs">
            {workspace && (
              <span className="hidden sm:inline-flex items-center gap-1 rounded bg-[var(--surface-raised)] border border-[var(--border)] px-2.5 py-1 text-[11px] text-muted font-medium">
                <Shield className="w-3 h-3 text-gold" />
                {workspace.name} ({workspace.reporting_currency})
              </span>
            )}

            <div className="flex items-center gap-3">
              <span className="text-muted hidden md:inline">{user?.email}</span>
              <button
                onClick={logout}
                className="flex items-center gap-1 text-xs text-muted hover:text-negative cursor-pointer transition-colors"
                title="Sign out"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Sign Out</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 py-8">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="border-t border-[var(--border)] py-4 text-center text-[11px] text-faint">
        XakuFinance &bull; Ledger Integrity &bull; Obsidian &amp; Gold Standard
      </footer>
    </div>
  );
};
