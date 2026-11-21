import React, { useEffect, useMemo, useState } from "react";
import { Link, NavLink, Outlet, Navigate, useLocation, useNavigate } from "react-router-dom";
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
  Menu,
  X,
  Search,
  PlusCircle,
  CheckCircle2,
  CornerDownLeft,
} from "lucide-react";
import { AnimatedThemeToggler } from "@/components/ui/animated-theme-toggler";
import { NotificationBell } from "@/features/notifications/components/notification-bell";
import { ImportWizardDialog } from "@/features/imports/components/import-wizard-dialog";
import { useQuery } from "@tanstack/react-query";
import { getAccounts } from "@/features/accounts/api";
import { queryKeys } from "@/lib/query-keys";
import { CurrencyDisplayMode, useCurrency } from "@/lib/currency-context";

type NavItem = {
  to: string;
  label: string;
  section: string;
  icon: React.ReactNode;
  keywords?: string;
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
        section: "Overview",
        icon: <LayoutDashboard className="w-4 h-4" />,
        keywords: "home summary kpi net worth",
      },
      {
        to: "/app/analytics",
        label: "Analytics",
        section: "Overview",
        icon: <BarChart3 className="w-4 h-4" />,
        keywords: "intelligence charts reports safe to spend",
      },
    ],
  },
  {
    label: "Finance",
    items: [
      {
        to: "/app/accounts",
        label: "Accounts",
        section: "Finance",
        icon: <Wallet className="w-4 h-4" />,
        keywords: "balances ledger wallets bank checking",
      },
      {
        to: "/app/transactions",
        label: "Transactions",
        section: "Finance",
        icon: <ArrowLeftRight className="w-4 h-4" />,
        keywords: "register expenses income splits journal",
      },
    ],
  },
  {
    label: "Planning",
    items: [
      {
        to: "/app/budgets",
        label: "Budgets",
        section: "Planning",
        icon: <PiggyBank className="w-4 h-4" />,
        keywords: "rollover limits spending cap",
      },
      {
        to: "/app/savings",
        label: "Savings",
        section: "Planning",
        icon: <Target className="w-4 h-4" />,
        keywords: "goals earmarks targets",
      },
      {
        to: "/app/debts",
        label: "Debts",
        section: "Planning",
        icon: <CreditCard className="w-4 h-4" />,
        keywords: "liabilities loans payoff apr",
      },
      {
        to: "/app/emergency-fund",
        label: "Emergency",
        section: "Planning",
        icon: <Shield className="w-4 h-4" />,
        keywords: "safety net runway cushion",
      },
    ],
  },
];

const EXTRA_ROUTES: Array<{ to: string; label: string; section: string }> = [
  { to: "/app/settings", label: "Settings & Security", section: "Workspace" },
];

const navLinkClass = (isActive: boolean, collapsed: boolean) =>
  `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150 ${
    isActive
      ? "bg-[var(--accent)]/12 text-[var(--accent-text)] border border-[var(--accent)]/30 font-semibold"
      : "text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--surface-raised)] border border-transparent"
  } ${collapsed ? "justify-center px-2" : ""}`;

export const AuthenticatedLayout: React.FC = () => {
  const { user, workspace, isAuthenticated, isLoading, logout } = useAuth();
  const { mode, setMode, usdToKhrRate } = useCurrency();
  const location = useLocation();
  const navigate = useNavigate();
  const [isImportOpen, setIsImportOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [isCommandOpen, setIsCommandOpen] = useState(false);
  const [commandQuery, setCommandQuery] = useState("");

  const { data: accounts = [] } = useQuery({
    queryKey: queryKeys.accounts.list(false),
    queryFn: () => getAccounts(false),
    enabled: isAuthenticated,
  });

  // Global Cmd+K / Ctrl+K shortcut for Quick Command Palette
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setIsCommandOpen((prev) => !prev);
      } else if (e.key === "Escape") {
        setIsCommandOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const currentRouteMeta = useMemo(() => {
    const allItems = [...NAV_GROUPS.flatMap((g) => g.items), ...EXTRA_ROUTES];
    const match = allItems.find((item) => location.pathname.startsWith(item.to));
    return match || { section: "Workspace", label: "Financial Control" };
  }, [location.pathname]);

  const commandOptions = useMemo(() => {
    const navCommands = [
      ...NAV_GROUPS.flatMap((g) =>
        g.items.map((item) => ({
          id: `nav-${item.to}`,
          title: item.label,
          subtitle: `${item.section} view`,
          keywords: `${item.label} ${item.section} ${item.keywords || ""}`,
          icon: item.icon,
          group: "Navigate",
          action: () => navigate(item.to),
        }))
      ),
      {
        id: "nav-settings",
        title: "Settings & Security",
        subtitle: "Profile, Workspace, 2FA & Privacy",
        keywords: "settings profile workspace security 2fa privacy export",
        icon: <Settings className="w-4 h-4" />,
        group: "Navigate",
        action: () => navigate("/app/settings"),
      },
    ];

    const quickActions = [
      {
        id: "action-new-tx",
        title: "Record New Transaction",
        subtitle: "Post expense, income, or multi-category split",
        keywords: "new add record transaction expense income split",
        icon: <PlusCircle className="w-4 h-4 text-[var(--accent-text)]" />,
        group: "Quick Action",
        action: () => navigate("/app/transactions?action=new"),
      },
      {
        id: "action-import-csv",
        title: "Import Bank Statement CSV",
        subtitle: "Open 4-step mapping & duplicate review wizard",
        keywords: "import csv upload bank statement",
        icon: <UploadCloud className="w-4 h-4 text-[var(--accent-text)]" />,
        group: "Quick Action",
        action: () => setIsImportOpen(true),
      },
    ];

    const all = [...quickActions, ...navCommands];
    const q = commandQuery.trim().toLowerCase();
    if (!q) return all;
    return all.filter(
      (item) =>
        item.title.toLowerCase().includes(q) ||
        item.subtitle.toLowerCase().includes(q) ||
        item.keywords.toLowerCase().includes(q)
    );
  }, [commandQuery, navigate]);

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
      <div
        className={`flex items-center justify-between border-b border-[var(--border)] px-4 py-4 ${
          collapsed ? "justify-center px-2" : ""
        }`}
      >
        <Link
          to="/app/dashboard"
          className="flex items-center gap-2.5 group shrink-0"
          onClick={() => setMobileSidebarOpen(false)}
        >
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#F0B90B] to-[#D9A600] flex items-center justify-center text-black font-bold shadow-sm group-hover:scale-105 transition-transform shrink-0">
            <span className="font-display text-sm">X</span>
          </div>
          {!collapsed && (
            <div className="flex flex-col">
              <span className="font-display font-bold tracking-tight text-[var(--text)] text-base leading-tight">
                XakuFinance
              </span>
              <span className="text-[10px] text-[var(--text-faint)] font-medium">
                Ledger Control
              </span>
            </div>
          )}
        </Link>
        {isMobile && (
          <button
            type="button"
            onClick={() => setMobileSidebarOpen(false)}
            className="p-1.5 rounded-lg text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--surface-raised)] transition-colors cursor-pointer"
            title="Close menu"
            aria-label="Close navigation menu"
          >
            <X className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* Nav Groups */}
      <nav className="flex-1 overflow-y-auto py-4 px-2 space-y-5" aria-label="Workspace Navigation">
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
          className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--surface-raised)] transition-all cursor-pointer ${
            collapsed ? "justify-center px-2" : ""
          }`}
          title={collapsed ? "Import CSV" : undefined}
        >
          <UploadCloud className="w-4 h-4 text-[var(--accent-text)] shrink-0" />
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
                  <Shield className="w-3 h-3 text-[var(--accent-text)] shrink-0" />
                  <span className="text-[11px] font-medium text-[var(--text)] truncate">
                    {workspace.name}
                  </span>
                  <span className="text-[10px] font-mono text-[var(--text-faint)]">
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
            aria-label="Sign out"
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
          aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
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
        {/* Institutional Top Bar */}
        <header className="sticky top-0 z-20 border-b border-[var(--border)] bg-[var(--surface)]/92 backdrop-blur-md">
          <div className="h-14 px-4 sm:px-6 flex items-center justify-between gap-3">
            {/* Mobile hamburger & logo */}
            <div className="flex items-center gap-3">
              <button
                type="button"
                className="md:hidden flex items-center justify-center w-8 h-8 rounded-lg text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--surface-raised)] transition-colors cursor-pointer"
                onClick={() => setMobileSidebarOpen(true)}
                aria-label="Open navigation menu"
              >
                <Menu className="w-4 h-4" />
              </button>

              <Link to="/app/dashboard" className="md:hidden flex items-center gap-2 group">
                <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[#F0B90B] to-[#D9A600] flex items-center justify-center text-black font-bold shadow-xs">
                  <span className="font-display text-xs">X</span>
                </div>
                <span className="font-display font-bold tracking-tight text-[var(--text)] text-base">
                  XakuFinance
                </span>
              </Link>

              {/* Desktop Dynamic Breadcrumb */}
              <div className="hidden md:flex items-center gap-2 text-xs">
                <span className="text-[var(--text-faint)] font-medium">
                  {currentRouteMeta.section}
                </span>
                <span className="text-[var(--text-faint)]">/</span>
                <span className="font-semibold text-[var(--text)]">
                  {currentRouteMeta.label}
                </span>
              </div>
            </div>

            {/* Right controls */}
            <div className="flex items-center gap-2 sm:gap-2.5">
              {/* Interactive Dual-Currency Switcher ($ USD | ៛ KHR | Both) */}
              <div
                className="inline-flex items-center rounded-lg border border-[var(--border)] bg-[var(--surface-raised)] p-0.5 text-[11px]"
                role="group"
                aria-label="Currency display switcher"
                title={`Exchange reference: $1 = ${usdToKhrRate.toLocaleString()} ៛`}
              >
                {(
                  [
                    { value: "USD", label: "$ USD", short: "$" },
                    { value: "KHR", label: "៛ KHR", short: "៛" },
                    { value: "BOTH", label: "$ + ៛ Both", short: "$+៛" },
                  ] as Array<{ value: CurrencyDisplayMode; label: string; short: string }>
                ).map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setMode(opt.value)}
                    className={`px-2 py-1 rounded-md font-medium transition-colors cursor-pointer whitespace-nowrap ${
                      mode === opt.value
                        ? "bg-gold shadow-xs font-semibold"
                        : "text-[var(--text-muted)] hover:text-[var(--text)]"
                    }`}
                  >
                    <span className="hidden sm:inline">{opt.label}</span>
                    <span className="sm:hidden">{opt.short}</span>
                  </button>
                ))}
                <span className="hidden 2xl:inline-block px-2 text-[10px] font-mono text-[var(--text-faint)] border-l border-[var(--border)] ml-0.5">
                  1$={usdToKhrRate.toLocaleString()}៛
                </span>
              </div>

              {/* Quick Command Palette Trigger */}
              <button
                type="button"
                onClick={() => {
                  setCommandQuery("");
                  setIsCommandOpen(true);
                }}
                className="inline-flex items-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--surface-raised)] hover:bg-[var(--surface-hover)] px-2.5 py-1.5 text-xs text-[var(--text-muted)] hover:text-[var(--text)] transition-colors cursor-pointer"
                title="Open Quick Command Palette (Ctrl/Cmd + K)"
              >
                <Search className="w-3.5 h-3.5" />
                <span className="hidden md:inline">Quick jump</span>
                <kbd className="hidden md:inline-flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] font-mono rounded bg-[var(--surface)] border border-[var(--border)] text-[var(--text-faint)]">
                  ⌘K
                </kbd>
              </button>

              {/* Live Integrity Pill */}
              <span className="hidden xl:inline-flex items-center gap-1.5 rounded-lg bg-[var(--positive-bg)] border border-[var(--positive-border)] px-2.5 py-1 text-[11px] font-medium text-[var(--positive)]">
                <CheckCircle2 className="w-3 h-3" />
                <span>0 Drift · Reconciled</span>
              </span>

              {workspace && (
                <span className="hidden lg:inline-flex items-center gap-1 rounded-lg bg-[var(--surface-raised)] border border-[var(--border)] px-2.5 py-1 text-[11px] text-[var(--text-muted)] font-medium">
                  <Shield className="w-3 h-3 text-[var(--accent-text)]" />
                  <span>{workspace.name}</span>
                  <span className="font-mono text-[var(--text-faint)]">
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
      </div>

      {/* Quick Action & Navigation Command Palette */}
      {isCommandOpen && (
        <div
          className="fixed inset-0 z-50 flex items-start justify-center pt-[12vh] px-4 bg-black/60 backdrop-blur-xs"
          onClick={() => setIsCommandOpen(false)}
          role="dialog"
          aria-modal="true"
          aria-label="Quick Command Palette"
        >
          <div
            className="w-full max-w-lg rounded-2xl border border-[var(--border)] bg-[var(--surface)] shadow-2xl overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-2.5 px-4 py-3 border-b border-[var(--border)]">
              <Search className="w-4 h-4 text-[var(--text-muted)] shrink-0" />
              <input
                type="text"
                autoFocus
                value={commandQuery}
                onChange={(e) => setCommandQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && commandOptions.length > 0) {
                    e.preventDefault();
                    commandOptions[0].action();
                    setIsCommandOpen(false);
                  }
                }}
                placeholder="Type a command or jump to page (e.g. analytics, budgets, record)..."
                className="w-full bg-transparent text-sm text-[var(--text)] placeholder:text-[var(--text-faint)] focus:outline-none"
              />
              <button
                type="button"
                onClick={() => setIsCommandOpen(false)}
                className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[var(--surface-raised)] border border-[var(--border)] text-[var(--text-muted)] cursor-pointer"
              >
                ESC
              </button>
            </div>

            <div className="max-h-80 overflow-y-auto p-2 space-y-1">
              {commandOptions.length === 0 ? (
                <div className="py-8 text-center text-xs text-[var(--text-muted)]">
                  No matching navigation pages or actions found.
                </div>
              ) : (
                commandOptions.map((item, idx) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => {
                      item.action();
                      setIsCommandOpen(false);
                    }}
                    className={`w-full flex items-center justify-between gap-3 px-3 py-2.5 rounded-xl text-left transition-colors cursor-pointer ${
                      idx === 0
                        ? "bg-[var(--surface-raised)] border border-[var(--border)]"
                        : "hover:bg-[var(--surface-raised)] border border-transparent"
                    }`}
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <span className="w-7 h-7 rounded-lg bg-[var(--surface)] border border-[var(--border)] flex items-center justify-center text-[var(--text-muted)] shrink-0">
                        {item.icon}
                      </span>
                      <div className="min-w-0">
                        <div className="text-xs font-semibold text-[var(--text)] truncate">
                          {item.title}
                        </div>
                        <div className="text-[11px] text-[var(--text-faint)] truncate">
                          {item.subtitle}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                      <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-[var(--surface)] border border-[var(--border)] text-[var(--text-muted)]">
                        {item.group}
                      </span>
                      {idx === 0 && (
                        <CornerDownLeft className="w-3 h-3 text-[var(--text-faint)]" />
                      )}
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* Global CSV Statement Import Dialog */}
      <ImportWizardDialog
        open={isImportOpen}
        onOpenChange={setIsImportOpen}
        accounts={accounts}
      />
    </div>
  );
};
