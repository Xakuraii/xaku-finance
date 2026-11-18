"""Transaction update service with optimistic concurrency and audit logging."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from django.db import transaction

from apps.categories.models import Category
from apps.common.money import Money
from apps.ledger.models import JournalEntryStatus
from apps.ledger.services.accounts import (
    get_or_create_account_ledger_account,
    get_or_create_category_ledger_account,
)
from apps.ledger.services.posting import EntrySpec, PostingSpec, post_entry
from apps.ledger.services.reversal import reverse_entry
from apps.transactions.models import (
    Transaction,
    TransactionAudit,
    TransactionSplit,
    TransactionStatus,
    TransactionType,
)
from apps.workspaces.models import Workspace

if TYPE_CHECKING:
    from apps.identity.models import User
    from apps.transactions.services.create import SplitInput


class VersionConflict(ValueError):
    """Raised when an update specifies a stale version number."""


def update_transaction(
    *,
    workspace: Workspace,
    actor: User | None,
    transaction_id: uuid.UUID,
    expected_version: int,
    reason: str,
    title: str | None = None,
    amount: str | None = None,
    occurred_on: Any = None,
    category_id: uuid.UUID | None = None,
    splits: list[SplitInput] | None = None,
    status: str | None = None,
    description: str | None = None,
    notes: str | None = None,
    merchant: str | None = None,
    necessity: str | None = None,
) -> Transaction:
    """Update a transaction with optimistic locking, reversal/repost, and audit."""
    with transaction.atomic():
        tx = (
            Transaction.objects.select_for_update()
            .get(id=transaction_id, workspace_id=workspace.id)
        )

        if tx.version != expected_version:
            raise VersionConflict(
                f"Version conflict: expected {expected_version}, but transaction is at {tx.version}"
            )

        before_state: dict[str, Any] = {
            "title": tx.title,
            "amount_minor": tx.amount_minor,
            "status": tx.status,
            "occurred_on": tx.occurred_on.isoformat(),
            "category_id": str(tx.category_id) if tx.category_id else None,
            "is_split": tx.is_split,
            "description": tx.description,
            "notes": tx.notes,
            "merchant": tx.merchant,
            "necessity": tx.necessity,
        }

        # Apply simple scalar updates
        if title is not None:
            tx.title = title
        if description is not None:
            tx.description = description
        if notes is not None:
            tx.notes = notes
        if merchant is not None:
            tx.merchant = merchant
        if necessity is not None:
            tx.necessity = necessity

        financial_change = (
            amount is not None
            or occurred_on is not None
            or category_id is not None
            or splits is not None
            or status is not None
        )

        new_status = status or tx.status
        new_occurred_on = occurred_on or tx.occurred_on
        new_amount_minor = (
            Money.parse(amount, tx.currency_id).amount_minor
            if amount is not None
            else tx.amount_minor
        )

        if financial_change:
            # Reverse prior entry if posted
            prior_entry = tx.current_journal_entry
            if prior_entry and prior_entry.status == JournalEntryStatus.POSTED:
                reverse_entry(
                    workspace=workspace,
                    actor=actor,
                    entry=prior_entry,
                    reason=f"Edited transaction #{tx.id}: {reason}",
                )
                tx.current_journal_entry = None

            if splits is not None:
                tx.is_split = True
                tx.category_id = None
                TransactionSplit.objects.filter(transaction=tx).delete()
                new_splits = []
                for sp in splits:
                    cat = Category.objects.get(id=sp.category_id, workspace_id=workspace.id)
                    sp_minor = Money.parse(sp.amount, tx.currency_id).amount_minor
                    new_splits.append(
                        TransactionSplit(
                            workspace=workspace,
                            transaction=tx,
                            category=cat,
                            amount_minor=sp_minor,
                            memo=sp.memo,
                        )
                    )
                TransactionSplit.objects.bulk_create(new_splits)
            elif category_id is not None:
                tx.is_split = False
                tx.category_id = category_id
                TransactionSplit.objects.filter(transaction=tx).delete()

            tx.amount_minor = new_amount_minor
            tx.occurred_on = new_occurred_on
            tx.status = new_status

            # Post new entry if completed
            if new_status == TransactionStatus.COMPLETED:
                account_ledger_acc = get_or_create_account_ledger_account(account=tx.account)
                postings_spec: list[PostingSpec] = []

                if tx.transaction_type == TransactionType.EXPENSE:
                    postings_spec.append(
                        PostingSpec(
                            ledger_account_id=account_ledger_acc.id,
                            amount_minor=-tx.amount_minor,
                            currency=tx.currency_id,
                            memo=tx.title,
                        )
                    )
                    if tx.is_split:
                        for sp in tx.splits.all():
                            cat_acc = get_or_create_category_ledger_account(
                                category_id=sp.category_id,
                                workspace_id=workspace.id,
                                kind="expense",
                                name=sp.category.name,
                                currency_code=tx.currency_id,
                            )
                            postings_spec.append(
                                PostingSpec(
                                    ledger_account_id=cat_acc.id,
                                    amount_minor=sp.amount_minor,
                                    currency=tx.currency_id,
                                    memo=sp.memo or tx.title,
                                )
                            )
                    elif tx.category:
                        cat_acc = get_or_create_category_ledger_account(
                            category_id=tx.category_id,
                            workspace_id=workspace.id,
                            kind="expense",
                            name=tx.category.name,
                            currency_code=tx.currency_id,
                        )
                        postings_spec.append(
                            PostingSpec(
                                ledger_account_id=cat_acc.id,
                                amount_minor=tx.amount_minor,
                                currency=tx.currency_id,
                                memo=tx.title,
                            )
                        )
                elif tx.transaction_type == TransactionType.INCOME:
                    postings_spec.append(
                        PostingSpec(
                            ledger_account_id=account_ledger_acc.id,
                            amount_minor=tx.amount_minor,
                            currency=tx.currency_id,
                            memo=tx.title,
                        )
                    )
                    if tx.is_split:
                        for sp in tx.splits.all():
                            cat_acc = get_or_create_category_ledger_account(
                                category_id=sp.category_id,
                                workspace_id=workspace.id,
                                kind="income",
                                name=sp.category.name,
                                currency_code=tx.currency_id,
                            )
                            postings_spec.append(
                                PostingSpec(
                                    ledger_account_id=cat_acc.id,
                                    amount_minor=-sp.amount_minor,
                                    currency=tx.currency_id,
                                    memo=sp.memo or tx.title,
                                )
                            )
                    elif tx.category:
                        cat_acc = get_or_create_category_ledger_account(
                            category_id=tx.category_id,
                            workspace_id=workspace.id,
                            kind="income",
                            name=tx.category.name,
                            currency_code=tx.currency_id,
                        )
                        postings_spec.append(
                            PostingSpec(
                                ledger_account_id=cat_acc.id,
                                amount_minor=-tx.amount_minor,
                                currency=tx.currency_id,
                                memo=tx.title,
                            )
                        )

                if postings_spec:
                    entry_spec = EntrySpec(
                        entry_type=tx.transaction_type,
                        status=str(JournalEntryStatus.POSTED),
                        effective_date=tx.occurred_on,
                        source_type="transaction",
                        source_id=tx.id,
                        postings=postings_spec,
                        description=tx.title,
                    )
                    entry = post_entry(workspace=workspace, actor=actor, spec=entry_spec)
                    tx.current_journal_entry = entry

        tx.version += 1
        tx.save()

        after_state: dict[str, Any] = {
            "title": tx.title,
            "amount_minor": tx.amount_minor,
            "status": tx.status,
            "occurred_on": tx.occurred_on.isoformat(),
            "category_id": str(tx.category_id) if tx.category_id else None,
            "is_split": tx.is_split,
            "description": tx.description,
            "notes": tx.notes,
            "merchant": tx.merchant,
            "necessity": tx.necessity,
        }

        changed_fields = [
            k for k in after_state if before_state.get(k) != after_state.get(k)
        ]

        # Check if amount changed, note in changed fields
        if amount is not None and "amount_minor" in changed_fields:
            changed_fields.append("amount")

        TransactionAudit.objects.create(
            workspace=workspace,
            transaction=tx,
            revision=tx.version,
            actor=actor,
            reason=reason,
            changed_fields=changed_fields,
            before=before_state,
            after=after_state,
        )

        return tx
