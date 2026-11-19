import React, { useState } from "react";
import { Link, NavLink, Outlet, Navigate } from "react-router-dom";
import { useAuth } from "@/features/auth/auth-context";
import {
  Wallet,
  LayoutDashboard,
  ArrowLeftRight,
  LogOut,
  Shield,
  PiggyBank,
  BarChart3,
  Target,
  CreditCard,
  UploadCloud,
  Settings,
  ChevronLeft,
  ChevronRight,
  Menu, X,
} from "lucide-react";
import { AnimatedThemeToggler } from "@/components/ui/animated-theme-toggler";
import { NotificationBell } from "@/features/notifications/components/notification-bell";
import { ImportWizardDialog } from "@/features/imports/components/import-wizard-dialog";
import { useQuery } from "@tanstack/react-query";
import { getAccounts } from "@/features/accounts/api";
import { queryKeys } from "@/lib/query-keys";

type NavItem = {
  to: string;
  label: string;
  icon: React.ReactNode;
};

type NavGroup = {
  label: string;
  items: NavItem[];
};

const NAV_GROUPS: NavGroup[] = [
  {
    label: "Overview",
    items: [
      {
        to: "/app/dashboard",
        label: "Dashboard",
        icon: <LayoutDashboard className="w-4 h-4" />,
      },
      {
        to: "/app/analytics",
        label: "Analytics",
        icon: <BarChart3 className="w-4 h-4" />,
      },
    ],
  },
  {
    label: "Finance",
    items: [
      {
        to: "/app/accounts",
        label: "Accounts",
        icon: <Wallet className="w-4 h-4" />,
      },
      {
        to: "/app/transactions",
        label: "Transactions",
        icon: <ArrowLeftRight className="w-4 h-4" />,
      },
    ],
  },
  {
    label: "Planning",
    items: [
      {
        to: "/app/budgets",
        label: "Budgets",
        icon: <PiggyBank className="w-4 h-4" />,
      },
      {
        to: "/app/savings",
        label: "Savings",
        icon: <Target className="w-4 h-4" />,
      },
      {
        to: "/app/debts",
        label: "Debts",
        icon: <CreditCard className="w-4 h-4" />,
      },
      {
        to: "/app/emergency-fund",
        label: "Emergency",
        icon: <Shield className="w-4 h-4" />,
      },
    ],
  },
];

const navLinkClass = (isActive: boolean, collapsed: boolean) =>
  `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150 ${
    isActive
      ? "bg-[var(--accent)]/10 text-[var(--accent)] border border-[var(--accent)]/20"
      : "text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--surface-raised)]"
  } ${collapsed ? "justify-center px-2" : ""}`;

export const AuthenticatedLayout: React.FC = () => {
  const { user, workspace, isAuthenticated, isLoading, logout } = useAuth();
  const [isImportOpen, setIsImportOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  const { data: accounts = [] } = useQuery({
    queryKey: queryKeys.accounts.list(false),
    queryFn: () => getAccounts(false),
    enabled: isAuthenticated,
  });

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--bg)] text-xs">
        <div className="flex flex-col items-center gap-3">
          <div className="w-6 h-6 rounded-full border-2 border-[var(--accent)] border-t-transparent animate-spin" />
          <span className="text-[var(--text-muted)]">Opening financial workspace...</span>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  const SidebarContent = ({ collapsed, isMobile }: { collapsed: boolean; isMobile?: boolean }) => (
    <div className="flex flex-col h-full">
      {/* Logo */}
      <div className={`flex items-center justify-between border-b border-[var(--border)] px-4 py-4 ${
          collapsed ? "justify-center px-2" : ""
        }`}
      >
        <Link
          to="/app/accounts"
          className="flex items-center gap-2.5 group shrink-0"
          onClick={() => setMobileSidebarOpen(false)}
        >
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#F0B90B] to-[#D9A600] flex items-center justify-center text-black font-bold shadow-sm group-hover:scale-105 transition-transform shrink-0">
            <span className="font-display text-sm">X</span>
          </div>
          {!collapsed && (
            <span className="font-display font-bold tracking-tight text-[var(--text)] text-base leading-tight">
              XakuFinance
            </span>
          )}
        </Link>
        {isMobile && (
          <button
            type="button"
            onClick={() => setMobileSidebarOpen(false)}
            className="p-1.5 rounded-lg text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--surface-raised)] transition-colors cursor-pointer"
            title="Close menu"
          >
            <X className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* Nav Groups */}
      <nav className="flex-1 overflow-y-auto py-4 px-2 space-y-5">
        {NAV_GROUPS.map((group) => (
          <div key={group.label}>
            {!collapsed && (
              <p className="px-3 mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-[var(--text-faint)]">
                {group.label}
              </p>
            )}
            <div className="space-y-0.5">
              {group.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  onClick={() => setMobileSidebarOpen(false)}
                  className={({ isActive }) => navLinkClass(isActive, collapsed)}
                  title={collapsed ? item.label : undefined}
                >
                  <span className="shrink-0">{item.icon}</span>
                  {!collapsed && <span>{item.label}</span>}
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </nav>

      {/* Bottom Actions */}
      <div className="border-t border-[var(--border)] px-2 py-3 space-y-0.5">
        <button
          type="button"
          onClick={() => {
            setIsImportOpen(true);
            setMobileSidebarOpen(false);
          }}
          className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--surface-raised)] transition-all ${
            collapsed ? "justify-center px-2" : ""
          }`}
          title={collapsed ? "Import CSV" : undefined}
        >
          <UploadCloud className="w-4 h-4 text-[var(--accent)] shrink-0" />
          {!collapsed && <span>Import CSV</span>}
        </button>

        <NavLink
          to="/app/settings"
          onClick={() => setMobileSidebarOpen(false)}
          className={({ isActive }) => `w-full ${navLinkClass(isActive, collapsed)}`}
          title={collapsed ? "Settings" : undefined}
        >
          <Settings className="w-4 h-4 shrink-0" />
          {!collapsed && <span>Settings</span>}
        </NavLink>
      </div>

      {/* User / Sign Out */}
      <div className="border-t border-[var(--border)] px-2 py-3">
        <div
          className={`flex items-center gap-2 px-3 py-2 rounded-lg bg-[var(--surface-raised)] ${
            collapsed ? "justify-center px-2" : ""
          }`}
        >
          {!collapsed && (
            <div className="flex-1 min-w-0">
              {workspace && (
                <div className="flex items-center gap-1 mb-0.5">
                  <Shield className="w-3 h-3 text-[var(--accent)] shrink-0" />
                  <span className="text-[11px] font-medium text-[var(--text)] truncate">
                    {workspace.name}
                  </span>
                  <span className="text-[10px] text-[var(--text-faint)]">
                    ({workspace.reporting_currency})
                  </span>
                </div>
              )}
              <p className="text-[11px] text-[var(--text-faint)] truncate">{user?.email}</p>
            </div>
          )}
          <button
            onClick={logout}
            className="flex items-center justify-center gap-1 text-[var(--text-faint)] hover:text-[var(--negative)] cursor-pointer transition-colors p-1 rounded"
            title="Sign out"
          >
            <LogOut className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen flex bg-[var(--bg)] text-[var(--text)] transition-colors duration-200">
      {/* Desktop Sidebar */}
      <aside
        className={`hidden md:flex flex-col fixed left-0 top-0 h-full z-30 border-r border-[var(--border)] bg-[var(--surface)] transition-all duration-200 ${
          sidebarCollapsed ? "w-14" : "w-56"
        }`}
      >
        <SidebarContent collapsed={sidebarCollapsed} />

        {/* Collapse Toggle */}
        <button
          type="button"
          onClick={() => setSidebarCollapsed((v) => !v)}
          className="absolute -right-3 top-20 w-6 h-6 rounded-full border border-[var(--border)] bg-[var(--surface)] flex items-center justify-center text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--surface-raised)] transition-all shadow-xs cursor-pointer z-10"
          title={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {sidebarCollapsed ? (
            <ChevronRight className="w-3.5 h-3.5" />
          ) : (
            <ChevronLeft className="w-3.5 h-3.5" />
          )}
        </button>
      </aside>

      {/* Mobile Sidebar Overlay */}
      {mobileSidebarOpen && (
        <div
          className="md:hidden fixed inset-0 z-40 bg-black/50 backdrop-blur-sm"
          onClick={() => setMobileSidebarOpen(false)}
        />
      )}
      <aside
        className={`md:hidden fixed left-0 top-0 h-full z-50 w-64 border-r border-[var(--border)] bg-[var(--surface)] transition-transform duration-200 ${
          mobileSidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <SidebarContent collapsed={false} isMobile={true} />
      </aside>

      {/* Main Area */}
      <div
        className={`flex-1 flex flex-col min-h-screen transition-all duration-200 ${
          sidebarCollapsed ? "md:ml-14" : "md:ml-56"
        }`}
      >
        {/* Top Bar */}
        <header className="sticky top-0 z-20 border-b border-[var(--border)] bg-[var(--surface)]/90 backdrop-blur-md">
          <div className="h-14 px-4 flex items-center justify-between gap-3">
            {/* Mobile hamburger */}
            <button
              type="button"
              className="md:hidden flex items-center justify-center w-8 h-8 rounded-lg text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--surface-raised)] transition-colors cursor-pointer"
              onClick={() => setMobileSidebarOpen(true)}
            >
              <Menu className="w-4 h-4" />
            </button>

            {/* Mobile logo */}
            <Link to="/app/accounts" className="md:hidden flex items-center gap-2 group">
              <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[#F0B90B] to-[#D9A600] flex items-center justify-center text-black font-bold shadow-xs">
                <span className="font-display text-xs">X</span>
              </div>
              <span className="font-display font-bold tracking-tight text-[var(--text)] text-base">
                XakuFinance
              </span>
            </Link>

            <div className="flex-1" />

            {/* Right controls */}
            <div className="flex items-center gap-2">
              {workspace && (
                <span className="hidden lg:inline-flex items-center gap-1 rounded-lg bg-[var(--surface-raised)] border border-[var(--border)] px-2.5 py-1 text-[11px] text-[var(--text-muted)] font-medium">
                  <Shield className="w-3 h-3 text-[var(--accent)]" />
                  {workspace.name}
                  <span className="text-[var(--text-faint)]">
                    ({workspace.reporting_currency})
                  </span>
                </span>
              )}
              <NotificationBell />
              <AnimatedThemeToggler variant="circle" />
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 px-4 sm:px-6 py-6 max-w-7xl w-full mx-auto">
          <Outlet />
        </main>

        {/* Footer */}
        <footer className="border-t border-[var(--border)] py-3 text-center text-[11px] text-[var(--text-faint)] flex items-center justify-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent)]" />
          <span>XakuFinance · Double-Entry Accounting Core · 0 Drift Balance Integrity</span>
        </footer>
      </div>

      {/* Global CSV Statement Import Dialog */}
      <ImportWizardDialog
        open={isImportOpen}
        onOpenChange={setIsImportOpen}
        accounts={accounts}
      />
    </div>
  );
};
