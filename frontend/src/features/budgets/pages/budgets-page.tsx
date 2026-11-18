import React from "react";
import { useQuery } from "@tanstack/react-query";
import { BudgetList } from "../components/budget-list";
import { fetchCategories } from "@/features/categories/api";
import { useAuth } from "@/features/auth/auth-context";

export const BudgetsPage: React.FC = () => {
  const { workspace } = useAuth();
  const { data: categories = [] } = useQuery({
    queryKey: ["categories"],
    queryFn: fetchCategories,
  });

  return (
    <div className="space-y-6">
      <BudgetList
        categories={categories}
        defaultCurrency={workspace?.reporting_currency || "USD"}
      />
    </div>
  );
};
