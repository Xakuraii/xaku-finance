import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { TrendingUp, Calendar, Clock, DollarSign } from "lucide-react";
import {
  EmergencyFundStatus,
  getEmergencyFundProjection,
} from "../api/emergency-fund-api";

interface EmergencyProjectionCardProps {
  status: EmergencyFundStatus;
}

export const EmergencyProjectionCard: React.FC<EmergencyProjectionCardProps> = ({
  status,
}) => {
  const [monthlyContribution, setMonthlyContribution] = useState<string>("200.00");
  const isTargetMet = status.remaining_target_minor === 0;

  const {
    data: projection,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ["emergency-fund-projection", monthlyContribution],
    queryFn: () => getEmergencyFundProjection(monthlyContribution),
    enabled: !isTargetMet && parseFloat(monthlyContribution) > 0,
  });

  return (
    <div
      data-testid="emergency-projection-card"
      className="bg-[var(--surface)] border border-[var(--border)] rounded-xl p-6 shadow-sm space-y-4"
    >
      <div className="flex items-center gap-2">
        <TrendingUp className="w-5 h-5 text-[var(--accent)]" />
        <h3 className="text-base font-bold text-main">
          Emergency Fund Timeline Projection
        </h3>
      </div>

      <p className="text-xs text-[var(--text-muted)]">
        Calculate how quickly regular monthly contributions will build your target safety cushion.
      </p>

      {isTargetMet ? (
        <div className="p-4 bg-[var(--positive)]/10 border border-[var(--positive-border)] rounded-lg text-[var(--positive)] text-sm">
          🎉 Congratulations! Your emergency fund target is 100% funded!
        </div>
      ) : (
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-muted mb-1">
              Planned Monthly Contribution (${status.currency})
            </label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)] text-sm">
                $
              </span>
              <input
                type="number"
                step="10.00"
                min="1.00"
                value={monthlyContribution}
                onChange={(e) => setMonthlyContribution(e.target.value)}
                className="w-full pl-8 pr-3 py-2 bg-[var(--surface-raised)] border border-[var(--border)] rounded-lg text-sm text-main focus:outline-none focus:border-[var(--accent)]"
              />
            </div>
          </div>

          {isLoading && (
            <div className="text-xs text-[var(--text-muted)]">Calculating forecast...</div>
          )}

          {isError && (
            <div className="text-xs text-[var(--negative)]">
              Unable to project timeline. Please enter a valid contribution amount.
            </div>
          )}

          {projection && !isLoading && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
              <div className="p-3 bg-[var(--surface-raised)]/60 border border-[var(--border)]/40 rounded-lg">
                <div className="flex items-center gap-1.5 text-xs text-[var(--text-muted)] mb-1">
                  <Clock className="w-3.5 h-3.5" />
                  <span>Time to Target</span>
                </div>
                <div className="text-base font-bold text-main">
                  {projection.months_to_target !== null
                    ? `${projection.months_to_target} months`
                    : "—"}
                </div>
                <div className="text-[10px] text-[var(--text-muted)] mt-0.5">
                  ~{projection.days_to_target ?? 0} calendar days
                </div>
              </div>

              <div className="p-3 bg-[var(--surface-raised)]/60 border border-[var(--border)]/40 rounded-lg">
                <div className="flex items-center gap-1.5 text-xs text-[var(--text-muted)] mb-1">
                  <Calendar className="w-3.5 h-3.5" />
                  <span>Completion Date</span>
                </div>
                <div className="text-base font-bold text-main">
                  {projection.projected_completion_date ?? "—"}
                </div>
                <div className="text-[10px] text-[var(--text-muted)] mt-0.5">
                  At current contribution rate
                </div>
              </div>

              <div className="p-3 bg-[var(--surface-raised)]/60 border border-[var(--border)]/40 rounded-lg">
                <div className="flex items-center gap-1.5 text-xs text-[var(--text-muted)] mb-1">
                  <DollarSign className="w-3.5 h-3.5" />
                  <span>Remaining Needed</span>
                </div>
                <div className="text-base font-bold text-main">
                  ${(projection.remaining_target_minor / 100).toFixed(2)}
                </div>
                <div className="text-[10px] text-[var(--text-muted)] mt-0.5">
                  To reach full safety net
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
