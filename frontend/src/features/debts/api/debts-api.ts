import { api } from "@/lib/api/client";

export interface Liability {
  id: string;
  name: string;
  liability_type: string;
  currency: string;
  original_principal: string;
  original_principal_minor: number;
  outstanding_principal: string;
  outstanding_principal_minor: number;
  paid_principal: string;
  paid_principal_minor: number;
  progress_percent: number;
  interest_rate: string | null;
  interest_type: string;
  lender: string | null;
  due_day: number | null;
  next_due_date: string | null;
  linked_account_id: string | null;
  linked_account_name: string | null;
  ledger_account_id: string;
  status: "active" | "paid_off" | "archived";
  is_archived: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateLiabilityPayload {
  name: string;
  original_principal: string;
  currency: string;
  liability_type?: string;
  interest_rate?: string | null;
  interest_type?: string;
  lender?: string | null;
  due_day?: number | null;
  next_due_date?: string | null;
  linked_account_id?: string | null;
  initial_disbursement_account_id?: string | null;
  disbursement_date?: string | null;
  notes?: string | null;
}

export interface DebtRepayment {
  id: string;
  liability_id: string;
  transaction_id: string;
  principal_amount: string;
  principal_minor: number;
  interest_amount: string;
  interest_minor: number;
  fee_amount: string;
  fee_minor: number;
  total_amount: string;
  total_amount_minor: number;
  currency: string;
  paid_on: string;
  note: string | null;
  created_at: string;
}

export interface RecordRepaymentPayload {
  paying_account_id: string;
  principal_amount: string;
  interest_amount?: string;
  fee_amount?: string;
  paid_on?: string | null;
  note?: string | null;
}

export interface DebtProjection {
  liability_id: string;
  currency: string;
  outstanding_principal_minor: number;
  interest_rate: number | null;
  monthly_payment_minor: number | null;
  estimated_months_to_payoff: number | null;
  total_interest_minor: number | null;
  projected_payoff_date: string | null;
}

export async function fetchLiabilities(includeArchived = false): Promise<Liability[]> {
  const url = includeArchived ? "/api/v1/debts/?include_archived=true" : "/api/v1/debts/";
  return await api.get<Liability[]>(url);
}

export async function createLiability(payload: CreateLiabilityPayload): Promise<Liability> {
  return await api.post<Liability>("/api/v1/debts/", payload);
}

export async function updateLiability(
  id: string,
  payload: Partial<CreateLiabilityPayload> & { status?: string }
): Promise<Liability> {
  return await api.patch<Liability>(`/api/v1/debts/${id}/`, payload);
}

export async function archiveLiability(id: string): Promise<Liability> {
  return await api.post<Liability>(`/api/v1/debts/${id}/archive/`);
}

export async function restoreLiability(id: string): Promise<Liability> {
  return await api.post<Liability>(`/api/v1/debts/${id}/restore/`);
}

export async function fetchDebtRepayments(liabilityId: string): Promise<DebtRepayment[]> {
  return await api.get<DebtRepayment[]>(`/api/v1/debts/${liabilityId}/repayments/`);
}

export async function recordDebtRepayment(
  liabilityId: string,
  payload: RecordRepaymentPayload
): Promise<DebtRepayment> {
  return await api.post<DebtRepayment>(`/api/v1/debts/${liabilityId}/repayments/`, payload);
}

export async function fetchDebtProjection(
  liabilityId: string,
  monthlyPayment?: string
): Promise<DebtProjection> {
  const url = monthlyPayment
    ? `/api/v1/debts/${liabilityId}/projection/?monthly_payment=${encodeURIComponent(monthlyPayment)}`
    : `/api/v1/debts/${liabilityId}/projection/`;
  return await api.get<DebtProjection>(url);
}
