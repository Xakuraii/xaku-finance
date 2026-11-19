import React, { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { UploadCloud, X, CheckCircle2, FileText, ArrowRight } from "lucide-react";
import { Account } from "@/features/accounts/types";
import { ColumnMapping, ImportJob, ImportRecord } from "../types";
import { ColumnMappingStep } from "./column-mapping-step";
import { DuplicateReviewStep } from "./duplicate-review-step";
import { fetchImportRecords, uploadCsvStatement } from "../api/imports-api";

interface ImportWizardDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  accounts: Account[];
}

export const ImportWizardDialog: React.FC<ImportWizardDialogProps> = ({
  open,
  onOpenChange,
  accounts,
}) => {
  const spendableAccounts = accounts.filter((a) => !a.is_archived);

  const [step, setStep] = useState<1 | 2 | 3 | 4>(1);
  const [selectedAccountId, setSelectedAccountId] = useState(
    spendableAccounts[0]?.id || ""
  );
  const [file, setFile] = useState<File | null>(null);
  const [headers, setHeaders] = useState<string[]>([]);
  const [mapping, setMapping] = useState<ColumnMapping>({
    date: "",
    amount: "",
    title: "",
  });
  const [job, setJob] = useState<ImportJob | null>(null);
  const [records, setRecords] = useState<ImportRecord[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const resetAll = () => {
    setStep(1);
    setFile(null);
    setHeaders([]);
    setMapping({ date: "", amount: "", title: "" });
    setJob(null);
    setRecords([]);
    setErrorMessage(null);
    setIsUploading(false);
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (!selected) return;
    setFile(selected);
    setErrorMessage(null);

    // Read header line from file
    const text = await selected.text();
    const firstLine = text.split("\n")[0] || "";
    const parsedHeaders = firstLine
      .split(",")
      .map((h) => h.trim().replace(/^["']|["']$/g, ""))
      .filter(Boolean);

    setHeaders(parsedHeaders);

    // Guess default mapping
    const guessed: ColumnMapping = { date: "", amount: "", title: "" };
    parsedHeaders.forEach((h) => {
      const lower = h.toLowerCase();
      if (lower.includes("date") && !guessed.date) guessed.date = h;
      else if ((lower.includes("amount") || lower.includes("price")) && !guessed.amount)
        guessed.amount = h;
      else if (
        (lower.includes("desc") || lower.includes("title") || lower.includes("payee")) &&
        !guessed.title
      )
        guessed.title = h;
      else if (lower.includes("cat") && !guessed.category) guessed.category = h;
    });

    setMapping(guessed);
  };

  const handleProceedFromUpload = () => {
    if (!file) {
      setErrorMessage("Please select a CSV file.");
      return;
    }
    if (!selectedAccountId) {
      setErrorMessage("Please select a target account.");
      return;
    }
    setStep(2);
  };

  const handleUploadAndScan = async () => {
    if (!file || !selectedAccountId) return;
    setIsUploading(true);
    setErrorMessage(null);

    try {
      const newJob = await uploadCsvStatement(selectedAccountId, file, mapping as any);
      setJob(newJob);

      const stagedRecords = await fetchImportRecords(newJob.id);
      setRecords(stagedRecords);
      setStep(3);
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to parse and stage CSV.");
    } finally {
      setIsUploading(false);
    }
  };

  const handleCommitSuccess = (completedJob: ImportJob) => {
    setJob(completedJob);
    setStep(4);
  };

  return (
    <Dialog.Root open={open} onOpenChange={(val) => { onOpenChange(val); if (!val) resetAll(); }}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 animate-fade-in" />
        <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-xl rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6 shadow-2xl z-50 text-main animate-scale-in">
          {/* Header */}
          <div className="flex items-center justify-between pb-3 border-b border-[var(--border)]">
            <div>
              <Dialog.Title className="text-lg font-bold text-main flex items-center gap-2">
                <UploadCloud className="w-5 h-5 text-gold" />
                Import Transactions (CSV)
              </Dialog.Title>
              <div className="flex items-center gap-2 mt-1 text-xs text-muted">
                <span className={step >= 1 ? "text-gold font-semibold" : ""}>1. File</span>
                <span>→</span>
                <span className={step >= 2 ? "text-gold font-semibold" : ""}>2. Mapping</span>
                <span>→</span>
                <span className={step >= 3 ? "text-gold font-semibold" : ""}>3. Duplicate Review</span>
                <span>→</span>
                <span className={step >= 4 ? "text-gold font-semibold" : ""}>4. Done</span>
              </div>
            </div>

            <Dialog.Close asChild>
              <button
                type="button"
                className="text-muted hover:text-main p-1 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </Dialog.Close>
          </div>

          <div className="mt-4">
            {errorMessage && (
              <div className="mb-4 p-3 text-xs bg-[var(--negative-bg)] border border-[var(--negative-border)] text-[var(--negative)] rounded-lg">
                {errorMessage}
              </div>
            )}

            {/* STEP 1: Upload & Account Select */}
            {step === 1 && (
              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-main mb-1">
                    Target Account
                  </label>
                  <select
                    value={selectedAccountId}
                    onChange={(e) => setSelectedAccountId(e.target.value)}
                    className="w-full bg-[var(--surface-raised)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-main focus:outline-none focus:border-[var(--accent)]"
                  >
                    {spendableAccounts.map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.name} ({a.currency})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-main mb-1">
                    Select CSV Statement
                  </label>
                  <div className="border-2 border-dashed border-[var(--border)] hover:border-[#F0B90B] rounded-xl p-6 text-center cursor-pointer bg-[var(--surface-raised)]/60 transition-all relative">
                    <input
                      type="file"
                      accept=".csv,text/csv"
                      onChange={handleFileSelect}
                      className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                    />
                    <FileText className="w-8 h-8 mx-auto mb-2 text-gold" />
                    {file ? (
                      <div>
                        <p className="text-sm font-semibold text-main">{file.name}</p>
                        <p className="text-xs text-faint">{(file.size / 1024).toFixed(1)} KB</p>
                      </div>
                    ) : (
                      <div>
                        <p className="text-sm font-medium text-main">
                          Click or drag and drop statement file
                        </p>
                        <p className="text-xs text-faint">Supports standard CSV exports</p>
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex justify-end pt-3 border-t border-[var(--border)]">
                  <button
                    type="button"
                    disabled={!file}
                    onClick={handleProceedFromUpload}
                    className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg bg-[#F0B90B] text-black hover:bg-[#FCD535] transition-all disabled:opacity-40"
                  >
                    Continue
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}

            {/* STEP 2: Column Mapping */}
            {step === 2 && (
              isUploading ? (
                <div className="py-12 text-center text-muted">
                  <div className="inline-block animate-spin rounded-full h-8 w-8 border-2 border-[#F0B90B] border-t-transparent mb-3" />
                  <p className="text-sm font-medium text-main">Staging records and checking for duplicates...</p>
                </div>
              ) : (
                <ColumnMappingStep
                  headers={headers}
                  mapping={mapping}
                  onChange={setMapping}
                  onNext={handleUploadAndScan}
                  onBack={() => setStep(1)}
                />
              )
            )}

            {/* STEP 3: Duplicate Review */}
            {step === 3 && job && (
              <DuplicateReviewStep
                job={job}
                records={records}
                onSuccess={handleCommitSuccess}
                onBack={() => setStep(2)}
              />
            )}

            {/* STEP 4: Success & Summary */}
            {step === 4 && job && (
              <div className="py-8 text-center space-y-3">
                <CheckCircle2 className="w-12 h-12 mx-auto text-emerald-400" />
                <h3 className="text-lg font-bold text-main">Import Complete!</h3>
                <p className="text-sm text-main">
                  Successfully imported{" "}
                  <span className="font-bold text-gold font-mono">{job.imported_count}</span>{" "}
                  transactions into your account.
                </p>
                <div className="pt-4">
                  <button
                    type="button"
                    onClick={() => { onOpenChange(false); resetAll(); }}
                    className="px-6 py-2 text-xs font-bold rounded-xl bg-[#F0B90B] text-black hover:bg-[#FCD535] transition-all"
                  >
                    Done
                  </button>
                </div>
              </div>
            )}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
};
