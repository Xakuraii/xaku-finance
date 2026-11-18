import { api } from "@/lib/api/client";

export interface AccountBrief {
  id: string;
  name: string;
  currency: string;
  account_type?: string;
}

export interface CategoryBrief {
  id: string;
  name: string;
  kind: string;
}

export interface ConversionInfo {
  rate: string;
  reference_rate: string | null;
  spread_amount: string;
  spread_currency: string;
  spread_amount_minor: number;
  policy_note: string;
}

export interface Transfer {
  id: string;
  transaction_id: string;
  source_account: AccountBrief;
  destination_account: AccountBrief;
  amount: string;
  amount_minor: number;
  currency: string;
  destination_amount: string;
  destination_amount_minor: number;
  destination_currency: string;
  rate: string;
  reference_rate: string | null;
  transfer_fee: string;
  transfer_fee_minor: number;
  transfer_fee_category: CategoryBrief | null;
  conversion_fee: string;
  conversion_fee_minor: number;
  conversion_fee_category: CategoryBrief | null;
  conversion: ConversionInfo | null;
  occurred_on: string;
  notes: string;
  status: string;
  is_archived: boolean;
  created_at: string;
}

export interface CreateTransferPayload {
  source_account_id: string;
  destination_account_id: string;
  amount: string;
  destination_amount?: string;
  rate?: string;
  reference_rate?: string;
  transfer_fee?: string;
  transfer_fee_category_id?: string;
  conversion_fee_category_id?: string;
  occurred_on: string;
  notes?: string;
}

export const getTransfers = async (includeArchived = false): Promise<Transfer[]> => {
  const res = await api.get<{ results: Transfer[] } | Transfer[]>(
    `/api/v1/transfers/?include_archived=${includeArchived}`
  );
  if (Array.isArray(res)) {
    return res;
  }
  return res.results || [];
};

export const createTransfer = async (payload: CreateTransferPayload): Promise<Transfer> => {
  return api.post<Transfer>("/api/v1/transfers/", payload);
};

export const archiveTransfer = async ({
  transferId,
  reason,
}: {
  transferId: string;
  reason: string;
}): Promise<{ id: string; is_archived: boolean; archived_at: string }> => {
  return api.post(`/api/v1/transfers/${transferId}/archive/`, { reason });
};
