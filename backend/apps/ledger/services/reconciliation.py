"""Ledger reconciliation and integrity checks."""

from __future__ import annotations

from dataclasses import dataclass, field

from django.db.models import F, Sum

from apps.ledger.models import JournalEntryStatus, Posting
from apps.workspaces.models import Workspace


@dataclass
class ReconciliationReport:
    is_valid: bool
    errors: list[str] = field(default_factory=list)


def reconcile_workspace(workspace: Workspace) -> ReconciliationReport:
    """Run full ledger reconciliation checks on a workspace."""
    errors: list[str] = []

    # 1. Check that all posted entries balance to zero per currency
    unbalanced = (
        Posting.objects.filter(
            workspace_id=workspace.id,
            journal_entry__status__in=[JournalEntryStatus.POSTED, JournalEntryStatus.REVERSED],
        )
        .values("journal_entry_id", "currency_id")
        .annotate(balance=Sum("amount_minor"))
        .filter(balance__isnull=False)
        .exclude(balance=0)
    )

    for item in unbalanced:
        errors.append(
            f"Entry {item['journal_entry_id']} is unbalanced for currency {item['currency_id']}: "
            f"sum = {item['balance']}"
        )

    # 2. Check that posting currency matches ledger account currency
    mismatches = (
        Posting.objects.filter(workspace_id=workspace.id)
        .exclude(currency_id=F("ledger_account__currency_id"))
        .values_list("id", "currency_id", "ledger_account__currency_id")
    )
    for p_id, p_curr, acc_curr in mismatches:
        errors.append(
            f"Posting {p_id} currency ({p_curr}) does not match "
            f"ledger account currency ({acc_curr})"
        )

    return ReconciliationReport(is_valid=len(errors) == 0, errors=errors)
