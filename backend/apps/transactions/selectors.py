"""Read selectors for transactions and totals."""

from __future__ import annotations

import uuid
from datetime import date

from django.db.models import Sum

from apps.ledger.models import JournalEntryStatus, LedgerAccountKind, Posting
from apps.transactions.models import Transaction
from apps.workspaces.models import Workspace


def get_transaction(*, workspace: Workspace, transaction_id: uuid.UUID) -> Transaction:
    """Retrieve a single transaction for a workspace."""
    return Transaction.objects.get(id=transaction_id, workspace_id=workspace.id)


def expense_total(workspace: Workspace, as_of: date | None = None) -> int:
    """Compute total expenses in minor units across all expense accounts in the workspace."""
    qs = Posting.objects.filter(
        workspace_id=workspace.id,
        ledger_account__kind=LedgerAccountKind.EXPENSE,
        journal_entry__status__in=[JournalEntryStatus.POSTED, JournalEntryStatus.REVERSED],
    )
    if as_of is not None:
        qs = qs.filter(journal_entry__effective_date__lte=as_of)
    total = qs.aggregate(total=Sum("amount_minor"))["total"]
    return int(total or 0)


def income_total(workspace: Workspace, as_of: date | None = None) -> int:
    """Compute total income in minor units across all income accounts in the workspace.

    In double-entry, income accounts have credit postings (negative values), so we negate the sum.
    """
    qs = Posting.objects.filter(
        workspace_id=workspace.id,
        ledger_account__kind=LedgerAccountKind.INCOME,
        journal_entry__status__in=[JournalEntryStatus.POSTED, JournalEntryStatus.REVERSED],
    )
    if as_of is not None:
        qs = qs.filter(journal_entry__effective_date__lte=as_of)
    total = qs.aggregate(total=Sum("amount_minor"))["total"]
    return -int(total or 0)
