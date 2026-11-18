export function formatDate(dateString: string, locale: string = "en-US"): string {
  try {
    const d = new Date(dateString);
    return new Intl.DateTimeFormat(locale, {
      year: "numeric",
      month: "short",
      day: "numeric",
    }).format(d);
  } catch {
    return dateString;
  }
}

export function formatDateTime(isoString: string, locale: string = "en-US"): string {
  try {
    const d = new Date(isoString);
    return new Intl.DateTimeFormat(locale, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(d);
  } catch {
    return isoString;
  }
}

export function formatAccountType(type: string): string {
  const map: Record<string, string> = {
    checking: "Checking",
    savings: "Savings",
    cash: "Cash Wallet",
    ewallet: "E-Wallet",
    credit_card: "Credit Card",
    investment: "Investment",
    other: "Other",
  };
  return map[type] || type;
}

export function formatTransactionType(type: string): string {
  const map: Record<string, string> = {
    income: "Income",
    expense: "Expense",
    transfer: "Transfer",
    opening_balance: "Opening Balance",
    debt_disbursement: "Debt Disbursement",
    debt_repayment: "Debt Repayment",
    adjustment: "Adjustment",
  };
  return map[type] || type;
}
