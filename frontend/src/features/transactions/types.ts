export type TransactionType =
  | "income"
  | "expense"
  | "transfer"
  | "opening_balance"
  | "debt_disbursement"
  | "debt_repayment"
  | "adjustment";

export type TransactionStatus = "pending" | "completed" | "cancelled";

export type SpendingNecessity = "essential" | "important" | "lifestyle" | "unplanned";

export interface TransactionSplit {
  id?: string;
  category_id: string;
  category_name?: string;
  amount: string;
  amount_minor?: number;
  memo?: string;
}

export interface Transaction {
  id: string;
  account_id: string;
  account_name: string;
  type: TransactionType;
  status: TransactionStatus;
  amount: string;
  amount_minor: number;
  amount_display: string;
  currency: string;
  occurred_on: string;
  title: string;
  description?: string;
  notes?: string;
  merchant?: string;
  category_id?: string | null;
  category_name?: string | null;
  is_split: boolean;
  splits: TransactionSplit[];
  tags: string[];
  necessity?: SpendingNecessity | null;
  version: number;
  is_archived: boolean;
  archived_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface TransactionAudit {
  id: string;
  revision: number;
  action: string;
  reason: string;
  changed_fields: string[];
  before: Record<string, unknown>;
  after: Record<string, unknown>;
  snapshot: Record<string, unknown>;
  actor_email?: string | null;
  created_at: string;
}

export interface CreateTransactionInput {
  type: TransactionType;
  account_id: string;
  amount: string;
  currency: string;
  occurred_on: string;
  title: string;
  category_id?: string | null;
  splits?: { category_id: string; amount: string; memo?: string }[];
  tags?: string[];
  necessity?: SpendingNecessity | null;
  status?: TransactionStatus;
  description?: string;
  notes?: string;
  merchant?: string;
}

export interface UpdateTransactionInput {
  expected_version: number;
  reason: string;
  amount?: string;
  title?: string;
  occurred_on?: string;
  category_id?: string | null;
  splits?: { category_id: string; amount: string; memo?: string }[];
  tags?: string[];
  necessity?: SpendingNecessity | null;
  description?: string;
  notes?: string;
  merchant?: string;
}
