import React from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  CheckCircle2,
  ArrowRight,
  ShieldCheck,
  Check,
  Ban,
} from "lucide-react";
import { ImportJob, ImportRecord } from "../types";
import { commitJob, resolveCandidate } from "../api/imports-api";

interface DuplicateReviewStepProps {
  job: ImportJob;
  records: ImportRecord[];
  onSuccess: (completedJob: ImportJob) => void;
  onBack: () => void;
}

export const DuplicateReviewStep: React.FC<DuplicateReviewStepProps> = ({
  job,
  records,
  onSuccess,
  onBack,
}) => {
  const queryClient = useQueryClient();

  const resolveMutation = useMutation({
    mutationFn: ({
      candidateId,
      decision,
    }: {
      candidateId: string;
      decision: "import" | "skip";
    }) => resolveCandidate(job.id, candidateId, decision),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["import-records", job.id] });
      queryClient.invalidateQueries({ queryKey: ["import-job", job.id] });
    },
  });

  const commitMutation = useMutation({
    mutationFn: () => commitJob(job.id),
    onSuccess: (completedJob) => {
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["accounts"] });
      onSuccess(completedJob);
    },
  });

  // Calculate pending duplicate candidates
  const allCandidates = records.flatMap((r) => r.duplicate_candidates || []);
  const pendingCount = allCandidates.filter((c) => c.decision === "pending").length;
  const duplicateRecords = records.filter(
    (r) => r.duplicate_candidates && r.duplicate_candidates.length > 0
  );
  const cleanRecords = records.filter(
    (r) => !r.duplicate_candidates || r.duplicate_candidates.length === 0
  );

  const canCommit = pendingCount === 0 && !commitMutation.isPending;

  return (
    <div data-testid="duplicate-review-step" className="space-y-5">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-3 border-b border-[var(--border)]">
        <div>
          <h4 className="font-semibold text-main flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-gold" />
            Duplicate Review & Verification
          </h4>
          <p className="text-xs text-muted mt-0.5">
            {pendingCount > 0 ? (
              <span className="text-amber-400 font-medium">
                {pendingCount} suspected duplicate(s) require your review before committing.
              </span>
            ) : (
              <span className="text-emerald-400 font-medium flex items-center gap-1 mt-0.5">
                <CheckCircle2 className="w-3.5 h-3.5" />
                All duplicate candidates resolved. Ready to commit into ledger.
              </span>
            )}
          </p>
        </div>

        <div className="text-xs text-muted">
          Total rows: <span className="font-mono text-main">{records.length}</span> ({cleanRecords.length} clean, {duplicateRecords.length} flagged)
        </div>
      </div>

      {/* Duplicate Candidates List */}
      {duplicateRecords.length > 0 && (
        <div className="space-y-3">
          <h5 className="text-xs font-semibold uppercase tracking-wider text-muted">
            Flagged Duplicates
          </h5>
          <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
            {duplicateRecords.map((rec) => {
              const cand = rec.duplicate_candidates[0];
              const scorePct = cand ? Math.round(parseFloat(cand.score) * 100) : 0;
              return (
                <div
                  key={rec.id}
                  data-testid={`duplicate-row-${rec.row_number}`}
                  className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-3 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-main">
                        Row #{rec.row_number}: {rec.normalized?.title}
                      </span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                        {scorePct}% match
                      </span>
                      {cand?.decision !== "pending" && (
                        <span
                          className={`text-[10px] font-semibold px-2 py-0.5 rounded capitalize ${
                            cand?.decision === "skip"
                              ? "bg-[var(--surface-raised)] text-muted"
                              : "bg-emerald-500/20 text-emerald-400"
                          }`}
                        >
                          {cand?.decision}
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-muted font-mono">
                      {rec.normalized?.date} • {rec.normalized?.amount} {rec.normalized?.currency}
                    </div>
                  </div>

                  {cand && (
                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        type="button"
                        data-testid={`skip-btn-${rec.row_number}`}
                        onClick={() =>
                          resolveMutation.mutate({
                            candidateId: cand.id,
                            decision: "skip",
                          })
                        }
                        className={`flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-lg border transition-all ${
                          cand.decision === "skip"
                            ? "bg-slate-700 text-main border-slate-500"
                            : "bg-[var(--surface-raised)] border-[var(--border)] text-main hover:text-main hover:border-slate-500"
                        }`}
                      >
                        <Ban className="w-3.5 h-3.5 text-muted" />
                        Skip
                      </button>

                      <button
                        type="button"
                        data-testid={`import-btn-${rec.row_number}`}
                        onClick={() =>
                          resolveMutation.mutate({
                            candidateId: cand.id,
                            decision: "import",
                          })
                        }
                        className={`flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-lg border transition-all ${
                          cand.decision === "import"
                            ? "bg-[#F0B90B] text-black border-[#F0B90B] font-semibold"
                            : "bg-[var(--surface-raised)] border-[var(--border)] text-main hover:text-main hover:border-[#F0B90B]"
                        }`}
                      >
                        <Check className="w-3.5 h-3.5 text-gold" />
                        Import Anyway
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Clean Records Sample */}
      {cleanRecords.length > 0 && (
        <div className="space-y-2">
          <h5 className="text-xs font-semibold uppercase tracking-wider text-muted">
            Clean Transactions ({cleanRecords.length})
          </h5>
          <div className="space-y-1.5 max-h-40 overflow-y-auto pr-1">
            {cleanRecords.slice(0, 5).map((rec) => (
              <div
                key={rec.id}
                className="rounded-lg border border-[var(--border)] bg-[var(--surface-raised)] px-3 py-2 text-xs flex items-center justify-between text-main"
              >
                <span>
                  Row #{rec.row_number}: {rec.normalized?.title}
                </span>
                <span className="font-mono text-main">
                  {rec.normalized?.date} • {rec.normalized?.amount} {rec.normalized?.currency}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Commit Footer */}
      <div className="flex items-center justify-between pt-4 border-t border-[var(--border)]">
        <button
          type="button"
          onClick={onBack}
          className="px-4 py-2 text-xs font-medium text-muted hover:text-main rounded-lg transition-colors"
        >
          Cancel
        </button>

        <button
          type="button"
          data-testid="commit-import-btn"
          disabled={!canCommit}
          onClick={() => commitMutation.mutate()}
          className="flex items-center gap-1.5 px-5 py-2.5 text-xs font-bold rounded-xl bg-[#F0B90B] text-black hover:bg-[#FCD535] shadow-lg shadow-[#F0B90B]/10 transition-all disabled:opacity-40 cursor-pointer"
        >
          {commitMutation.isPending ? "Committing into Ledger..." : "Commit Transactions"}
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
