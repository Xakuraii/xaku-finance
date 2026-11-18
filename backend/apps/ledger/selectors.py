"""Read selectors for the double-entry ledger."""

from __future__ import annotations

import uuid
from datetime import date

from django.db.models import Sum

from apps.common.money import Money
from apps.ledger.models import JournalEntryStatus, LedgerAccount, Posting
from apps.workspaces.models import Workspace


def postings_balance(*, ledger_account_id: uuid.UUID, as_of: date | None = None) -> int:
    """Compute the signed balance of a ledger account from posted and reversed entries."""
    qs = Posting.objects.filter(
        ledger_account_id=ledger_account_id,
        journal_entry__status__in=[JournalEntryStatus.POSTED, JournalEntryStatus.REVERSED],
    )
    if as_of is not None:
        qs = qs.filter(journal_entry__effective_date__lte=as_of)

    total = qs.aggregate(total=Sum("amount_minor"))["total"]
    return int(total or 0)


def get_ledger_balance(
    *,
    workspace: Workspace,
    ledger_account: LedgerAccount,
    as_of: date | None = None,
) -> Money:
    """Compute the Money balance for a ledger account."""
    balance_minor = postings_balance(ledger_account_id=ledger_account.id, as_of=as_of)
    return Money(
        amount_minor=balance_minor,
        currency=ledger_account.currency_id,
        minor_unit=ledger_account.currency.minor_unit,
    )
