export type ImportJobStatus =
  | "uploaded"
  | "validating"
  | "validated"
  | "awaiting_review"
  | "committing"
  | "completed"
  | "failed"
  | "cancelled";

export type ImportRecordStatus =
  | "valid"
  | "invalid"
  | "duplicate_exact"
  | "duplicate_potential"
  | "skipped"
  | "imported";

export interface DuplicateCandidate {
  id: string;
  existing_transaction_id: string;
  score: string;
  reasons: Record<string, any>;
  decision: "pending" | "import" | "skip";
  decided_at?: string | null;
}

export interface ImportRecord {
  id: string;
  row_number: number;
  raw: Record<string, any>;
  normalized?: {
    date: string;
    amount: string;
    amount_minor: number;
    currency: string;
    kind: "income" | "expense";
    title: string;
    category_id?: string | null;
    notes?: string;
  } | null;
  status: ImportRecordStatus;
  action: "import" | "skip";
  errors: string[];
  duplicate_candidates: DuplicateCandidate[];
}

export interface ImportJob {
  id: string;
  account_id: string;
  file_name: string;
  file_format: string;
  status: ImportJobStatus;
  mapping: Record<string, string>;
  row_count: number;
  valid_count: number;
  invalid_count: number;
  duplicate_count: number;
  imported_count: number;
  error_summary: Record<string, any>;
  created_at: string;
  finished_at?: string | null;
}

export interface ColumnMapping {
  date: string;
  amount: string;
  title: string;
  category?: string;
  notes?: string;
}
