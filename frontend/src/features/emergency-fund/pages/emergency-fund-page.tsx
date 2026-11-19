import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Shield } from "lucide-react";
import { getAccounts } from "@/features/accounts/api";
import { fetchSavingsGoals } from "@/features/savings/api/savings-api";
import { getEmergencyFundStatus } from "../api/emergency-fund-api";
import { EmergencyFundCard } from "../components/emergency-fund-card";
import { EmergencyConfigDialog } from "../components/emergency-config-dialog";
import { EmergencyProjectionCard } from "../components/emergency-projection-card";

export const EmergencyFundPage: React.FC = () => {
  const [configOpen, setConfigOpen] = useState(false);

  const {
    data: status,
    isLoading: isStatusLoading,
    isError: isStatusError,
  } = useQuery({
    queryKey: ["emergency-fund-status"],
    queryFn: getEmergencyFundStatus,
  });

  const { data: accounts = [] } = useQuery({
    queryKey: ["accounts"],
    queryFn: () => getAccounts(false),
  });

  const { data: goals = [] } = useQuery({
    queryKey: ["savings-goals"],
    queryFn: () => fetchSavingsGoals(false),
  });

  if (isStatusLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[var(--accent)]" />
      </div>
    );
  }

  if (isStatusError || !status) {
    return (
      <div className="p-8 text-center space-y-3">
        <Shield className="w-10 h-10 text-[var(--negative)] mx-auto" />
        <h2 className="text-lg font-bold text-main">
          Unable to Load Emergency Fund
        </h2>
        <p className="text-sm text-[var(--text-muted)]">
          There was an error retrieving your emergency fund data.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-5xl mx-auto py-4">
      {/* Top Banner & Header */}
      <div>
        <h1 className="text-2xl font-bold text-main">
          Emergency Fund Planner
        </h1>
        <p className="text-sm text-[var(--text-muted)] mt-1">
          Maintain an airtight financial safety net calibrated to your essential living expenses.
        </p>
      </div>

      {/* Main Status Card */}
      <EmergencyFundCard
        status={status}
        onConfigure={() => setConfigOpen(true)}
      />

      {/* Projection & Calculator Card */}
      <EmergencyProjectionCard status={status} />

      {/* Configuration Dialog */}
      <EmergencyConfigDialog
        open={configOpen}
        onOpenChange={setConfigOpen}
        status={status}
        accounts={accounts}
        goals={goals}
      />
    </div>
  );
};
