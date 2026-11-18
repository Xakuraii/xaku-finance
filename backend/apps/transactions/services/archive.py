"""Transaction archive and restore service."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone

from apps.ledger.models import JournalEntryStatus
from apps.ledger.services.reversal import reverse_entry
from apps.transactions.models import Transaction, TransactionAudit
from apps.workspaces.models import Workspace

if TYPE_CHECKING:
    from apps.identity.models import User


def archive_transaction(
    *,
    workspace: Workspace,
    actor: User | None,
    transaction_id: uuid.UUID,
    reason: str,
) -> Transaction:
    """Archive a transaction.

    If posted, reverses the journal entry so the archived transaction no longer affects balances.
    """
    with transaction.atomic():
        tx = Transaction.objects.select_for_update().get(
            id=transaction_id, workspace_id=workspace.id
        )

        if tx.is_archived:
            return tx

        prior_entry = tx.current_journal_entry
        if prior_entry and prior_entry.status == JournalEntryStatus.POSTED:
            reverse_entry(
                workspace=workspace,
                actor=actor,
                entry=prior_entry,
                reason=f"Archived transaction #{tx.id}: {reason}",
            )
            tx.current_journal_entry = None

        tx.is_archived = True
        tx.archived_at = timezone.now()
        tx.version += 1
        tx.save(update_fields=["is_archived", "archived_at", "version", "current_journal_entry"])

        TransactionAudit.objects.create(
            workspace=workspace,
            transaction=tx,
            revision=tx.version,
            actor=actor,
            reason=f"Archived: {reason}",
            changed_fields=["is_archived", "archived_at"],
            before={"is_archived": False},
            after={"is_archived": True, "archived_at": tx.archived_at.isoformat()},
        )

        return tx


def restore_transaction(
    *,
    workspace: Workspace,
    actor: User | None,
    transaction_id: uuid.UUID,
) -> Transaction:
    """Restore an archived transaction."""
    from apps.transactions.services.update import update_transaction

    with transaction.atomic():
        tx = Transaction.objects.select_for_update().get(
            id=transaction_id, workspace_id=workspace.id
        )
        if not tx.is_archived:
            return tx

        tx.is_archived = False
        tx.archived_at = None
        tx.version += 1
        tx.save(update_fields=["is_archived", "archived_at", "version"])

        TransactionAudit.objects.create(
            workspace=workspace,
            transaction=tx,
            revision=tx.version,
            actor=actor,
            reason="Restored from archive",
            changed_fields=["is_archived", "archived_at"],
            before={"is_archived": True},
            after={"is_archived": False},
        )

        # If it was completed, re-post
        if tx.status == "completed":
            return update_transaction(
                workspace=workspace,
                actor=actor,
                transaction_id=tx.id,
                expected_version=tx.version,
                reason="Restored completed transaction",
                status="completed",
            )

        return tx
