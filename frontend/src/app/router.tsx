import { createBrowserRouter, Navigate } from "react-router-dom";
import { LandingPage } from "@/features/landing/landing-page";
import { LoginPage } from "@/features/auth/pages/login-page";
import { RegisterPage } from "@/features/auth/pages/register-page";
import { AuthenticatedLayout } from "./authenticated-layout";
import { StatementSheet } from "@/features/accounts/components/statement-sheet";
import { TransactionsPage } from "@/features/transactions/pages/transactions-page";
import { BudgetsPage } from "@/features/budgets/pages/budgets-page";
import { AnalyticsPage } from "@/features/analytics/pages/analytics-page";
import { SavingsPage } from "@/features/savings/pages/savings-page";
import { DebtsPage } from "@/features/debts/pages/debts-page";

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
        element: <Navigate to="/app/accounts" replace />,
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
        path: "analytics",
        element: <AnalyticsPage />,
      },
    ],
  },
  // Backward compatibility redirects for direct routes
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
    path: "/analytics",
    element: <Navigate to="/app/analytics" replace />,
  },
  {
    path: "*",
    element: <Navigate to="/" replace />,
  },
]);
