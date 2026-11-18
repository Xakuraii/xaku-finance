import { createBrowserRouter, Navigate } from "react-router-dom";
import { LandingPage } from "@/features/landing/landing-page";
import { LoginPage } from "@/features/auth/pages/login-page";
import { RegisterPage } from "@/features/auth/pages/register-page";
import { AuthenticatedLayout } from "./authenticated-layout";
import { StatementSheet } from "@/features/accounts/components/statement-sheet";
import { DashboardPage } from "@/features/dashboard/pages/dashboard-page";
import { TransactionsPage } from "@/features/transactions/pages/transactions-page";
import { BudgetsPage } from "@/features/budgets/pages/budgets-page";
import { AnalyticsPage } from "@/features/analytics/pages/analytics-page";
import { SavingsPage } from "@/features/savings/pages/savings-page";
import { DebtsPage } from "@/features/debts/pages/debts-page";
import { EmergencyFundPage } from "@/features/emergency-fund/pages/emergency-fund-page";
import { SettingsPage } from "@/features/settings/pages/settings-page";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <LandingPage />,
  },
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    path: "/register",
    element: <RegisterPage />,
  },
  {
    path: "/app",
    element: <AuthenticatedLayout />,
    children: [
      {
        index: true,
        element: <Navigate to="/app/dashboard" replace />,
      },
      {
        path: "dashboard",
        element: <DashboardPage />,
      },
      {
        path: "accounts",
        element: <StatementSheet />,
      },
      {
        path: "transactions",
        element: <TransactionsPage />,
      },
      {
        path: "budgets",
        element: <BudgetsPage />,
      },
      {
        path: "savings",
        element: <SavingsPage />,
      },
      {
        path: "debts",
        element: <DebtsPage />,
      },
      {
        path: "emergency-fund",
        element: <EmergencyFundPage />,
      },
      {
        path: "analytics",
        element: <AnalyticsPage />,
      },
      {
        path: "settings",
        element: <SettingsPage />,
      },
    ],
  },
  // Backward compatibility redirects for direct routes
  {
    path: "/settings",
    element: <Navigate to="/app/settings" replace />,
  },
  {
    path: "/dashboard",
    element: <Navigate to="/app/dashboard" replace />,
  },
  {
    path: "/accounts",
    element: <Navigate to="/app/accounts" replace />,
  },
  {
    path: "/transactions",
    element: <Navigate to="/app/transactions" replace />,
  },
  {
    path: "/budgets",
    element: <Navigate to="/app/budgets" replace />,
  },
  {
    path: "/savings",
    element: <Navigate to="/app/savings" replace />,
  },
  {
    path: "/debts",
    element: <Navigate to="/app/debts" replace />,
  },
  {
    path: "/emergency-fund",
    element: <Navigate to="/app/emergency-fund" replace />,
  },
  {
    path: "/analytics",
    element: <Navigate to="/app/analytics" replace />,
  },
  {
    path: "*",
    element: <Navigate to="/" replace />,
  },
]);
