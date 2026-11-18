export type AccountType =
  | "checking"
  | "savings"
  | "cash"
  | "ewallet"
  | "credit_card"
  | "investment"
  | "other";

export type AccountNature = "asset" | "liability";

export interface Account {
  id: string;
  name: string;
  account_type: AccountType;
  currency: string;
  nature: AccountNature;
  description?: string | null;
  is_spendable: boolean;
  allows_negative_balance: boolean;
  display_order: number;
  opened_on: string;
  is_archived: boolean;
  archived_at?: string | null;
  archive_reason?: string | null;
  balance: string;
  balance_minor: number;
  balance_display: string;
  created_at: string;
  updated_at: string;
}

export interface CreateAccountInput {
  name: string;
  account_type: AccountType;
  currency: string;
  opening_balance?: string;
  opening_balance_date?: string;
  is_spendable?: boolean;
  description?: string;
  allows_negative_balance?: boolean;
}
