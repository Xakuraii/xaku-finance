"""Reversal service for immutable journal entries."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import transaction

from apps.ledger.models import JournalEntry, JournalEntryStatus, JournalEntryType
from apps.ledger.services.posting import EntrySpec, PostingSpec, post_entry
from apps.workspaces.models import Workspace

if TYPE_CHECKING:
    from apps.identity.models import User


def reverse_entry(
    *,
    workspace: Workspace,
    actor: User | None,
    entry: JournalEntry,
    reason: str = "",
) -> JournalEntry:
    """Atomically create a reversing journal entry and mark the original as reversed."""
    with transaction.atomic():
        locked_entry = (
            JournalEntry.objects.select_for_update()
            .prefetch_related("postings")
            .get(id=entry.id, workspace_id=workspace.id)
        )

        if locked_entry.status != JournalEntryStatus.POSTED:
            raise ValueError(
                f"Cannot reverse entry {locked_entry.id}: "
                f"status is {locked_entry.status} (expected posted)"
            )

        # Build negated postings
        reversal_postings = [
            PostingSpec(
                ledger_account_id=p.ledger_account_id,
                amount_minor=-p.amount_minor,
                currency=p.currency_id,
                memo=f"Reversal of posting {p.id}: {reason}".strip(),
            )
            for p in locked_entry.postings.all()
        ]

        desc = f"Reversal of entry #{locked_entry.ledger_seq}: {reason}".strip()

        spec = EntrySpec(
            entry_type=str(JournalEntryType.REVERSAL),
            status=str(JournalEntryStatus.POSTED),
            effective_date=locked_entry.effective_date,
            source_type="reversal",
            source_id=locked_entry.id,
            postings=reversal_postings,
            description=desc,
            fx_snapshot=locked_entry.fx_snapshot,
            reverses_entry_id=locked_entry.id,
        )

        reversal_entry = post_entry(workspace=workspace, actor=actor, spec=spec)

        locked_entry.status = JournalEntryStatus.REVERSED
        locked_entry.reversed_by_entry = reversal_entry
        locked_entry.save(update_fields=["status", "reversed_by_entry"])

        return reversal_entry
