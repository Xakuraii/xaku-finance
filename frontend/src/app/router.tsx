import { createBrowserRouter, Navigate } from "react-router-dom";
import { LoginPage } from "@/features/auth/pages/login-page";
import { RegisterPage } from "@/features/auth/pages/register-page";
import { AuthenticatedLayout } from "./authenticated-layout";
import { StatementSheet } from "@/features/accounts/components/statement-sheet";
import { TransactionsPage } from "@/features/transactions/pages/transactions-page";

export const router = createBrowserRouter([
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    path: "/register",
    element: <RegisterPage />,
  },
  {
    path: "/",
    element: <AuthenticatedLayout />,
    children: [
      {
        index: true,
        element: <Navigate to="/accounts" replace />,
      },
      {
        path: "accounts",
        element: <StatementSheet />,
      },
      {
        path: "transactions",
        element: <TransactionsPage />,
      },
    ],
  },
  {
    path: "*",
    element: <Navigate to="/" replace />,
  },
]);
