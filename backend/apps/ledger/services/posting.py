"""Atomic journal entry posting service."""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone

from apps.ledger.models import (
    JournalEntry,
    JournalEntryStatus,
    LedgerAccount,
    Posting,
)
from apps.workspaces.models import Workspace

if TYPE_CHECKING:
    from apps.identity.models import User


class UnbalancedEntry(ValueError):
    """Raised when an entry spec is unbalanced for a currency."""


class InvalidLedgerAccount(ValueError):
    """Raised when a posting references an invalid or foreign ledger account."""


@dataclass(frozen=True)
class PostingSpec:
    ledger_account_id: uuid.UUID
    amount_minor: int
    currency: str
    memo: str = ""


@dataclass(frozen=True)
class EntrySpec:
    entry_type: str
    status: str
    effective_date: date
    source_type: str
    source_id: uuid.UUID | None
    postings: list[PostingSpec]
    description: str = ""
    fx_snapshot: dict = field(default_factory=dict)
    reverses_entry_id: uuid.UUID | None = None


def post_entry(
    *,
    workspace: Workspace,
    actor: User | None,
    spec: EntrySpec,
) -> JournalEntry:
    """Atomically validate and post a journal entry and its postings."""
    if not spec.postings:
        raise ValueError("Cannot post an entry with no postings")

    # Validate per-currency balancing if status is posted
    if spec.status == JournalEntryStatus.POSTED:
        currency_sums: dict[str, int] = defaultdict(int)
        for p in spec.postings:
            currency_sums[p.currency] += p.amount_minor

        for curr, s in currency_sums.items():
            if s != 0:
                raise UnbalancedEntry(
                    f"Entry is unbalanced for {curr}: sum is {s} minor units (expected 0)"
                )

    with transaction.atomic():
        # Lock workspace row to obtain the next sequential ledger_seq
        ws = Workspace.objects.select_for_update().get(id=workspace.id)
        ws.ledger_seq += 1
        ws.save(update_fields=["ledger_seq", "updated_at"])
        seq = ws.ledger_seq

        # Lock involved ledger accounts in sorted order to avoid deadlocks
        account_ids = sorted({p.ledger_account_id for p in spec.postings})
        accounts = {
            acc.id: acc
            for acc in LedgerAccount.objects.select_for_update().filter(
                id__in=account_ids, workspace_id=ws.id
            )
        }

        # Verify all accounts exist and belong to workspace
        for acc_id in account_ids:
            if acc_id not in accounts:
                raise InvalidLedgerAccount(
                    f"Ledger account {acc_id} does not exist in workspace {ws.id}"
                )

        # Verify posting currency matches account currency
        for p in spec.postings:
            acc = accounts[p.ledger_account_id]
            if acc.currency_id != p.currency:
                raise ValueError(
                    f"Posting currency {p.currency} does not match "
                    f"ledger account currency {acc.currency_id}"
                )

        posted_at = timezone.now() if spec.status == JournalEntryStatus.POSTED else None

        entry = JournalEntry.objects.create(
            workspace=ws,
            entry_type=spec.entry_type,
            status=spec.status,
            effective_date=spec.effective_date,
            posted_at=posted_at,
            source_type=spec.source_type,
            source_id=spec.source_id,
            description=spec.description,
            fx_snapshot=spec.fx_snapshot,
            reverses_entry_id=spec.reverses_entry_id,
            ledger_seq=seq,
            created_by=actor,
        )

        Posting.objects.bulk_create([
            Posting(
                journal_entry=entry,
                ledger_account_id=p.ledger_account_id,
                workspace=ws,
                currency_id=p.currency,
                amount_minor=p.amount_minor,
                memo=p.memo,
            )
            for p in spec.postings
        ])

        return entry
