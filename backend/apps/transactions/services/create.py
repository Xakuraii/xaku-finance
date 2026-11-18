"""Transaction creation service."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

from django.db import transaction

from apps.accounts.models import Account
from apps.categories.models import Category
from apps.common.money import Money
from apps.ledger.models import JournalEntryStatus
from apps.ledger.services.accounts import (
    get_or_create_account_ledger_account,
    get_or_create_category_ledger_account,
)
from apps.ledger.services.posting import EntrySpec, PostingSpec, post_entry
from apps.tags.models import Tag
from apps.transactions.models import (
    Transaction,
    TransactionAudit,
    TransactionSplit,
    TransactionStatus,
    TransactionTag,
    TransactionType,
)
from apps.workspaces.models import Workspace

if TYPE_CHECKING:
    from apps.identity.models import User


class SplitTotalMismatch(ValueError):
    """Raised when the sum of splits does not equal the transaction amount."""

    def __init__(self, message: str, difference_minor: int) -> None:
        super().__init__(message)
        self.difference_minor = difference_minor


@dataclass(frozen=True)
class SplitInput:
    category_id: uuid.UUID
    amount: str
    memo: str = ""


def create_transaction(
    *,
    workspace: Workspace,
    actor: User | None,
    kind: str,
    account_id: uuid.UUID,
    amount: str,
    currency: str,
    occurred_on: date,
    title: str,
    category_id: uuid.UUID | None = None,
    splits: list[SplitInput] | None = None,
    tags: list[str] | None = None,
    necessity: str | None = None,
    status: str = "completed",
    description: str = "",
    notes: str = "",
    merchant: str = "",
) -> Transaction:
    """Create a new financial transaction atomically."""
    money = Money.parse(amount, currency)
    total_minor = money.amount_minor
    if total_minor <= 0:
        raise ValueError("Transaction amount must be positive")

    with transaction.atomic():
        account = Account.objects.select_for_update().get(id=account_id, workspace_id=workspace.id)
        if account.is_archived:
            raise ValueError(f"Cannot record transaction on archived account {account.id}")
        if account.currency_id != currency:
            raise ValueError(
                f"Currency {currency} does not match account currency {account.currency_id}"
            )

        is_split = bool(splits)
        split_records: list[tuple[Category, int, str]] = []

        if is_split:
            if splits is None or len(splits) < 2:
                raise ValueError("A split transaction must have at least 2 splits")
            category_id = None

            split_sum = 0
            for sp in splits:
                cat = Category.objects.get(id=sp.category_id, workspace_id=workspace.id)
                sp_money = Money.parse(sp.amount, currency)
                if sp_money.amount_minor <= 0:
                    raise ValueError("Split amount must be positive")
                split_sum += sp_money.amount_minor
                split_records.append((cat, sp_money.amount_minor, sp.memo))

            if split_sum != total_minor:
                diff = abs(split_sum - total_minor)
                raise SplitTotalMismatch(
                    f"Splits total ({split_sum}) does not equal amount ({total_minor})",
                    difference_minor=diff,
                )
        else:
            if kind in (TransactionType.INCOME, TransactionType.EXPENSE):
                if category_id is None:
                    raise ValueError(f"{kind.capitalize()} transaction requires a category")
                cat = Category.objects.get(id=category_id, workspace_id=workspace.id)
                split_records.append((cat, total_minor, ""))

        tx = Transaction.objects.create(
            workspace=workspace,
            account=account,
            currency_id=currency,
            transaction_type=kind,
            status=status,
            amount_minor=total_minor,
            occurred_on=occurred_on,
            title=title,
            description=description,
            notes=notes,
            merchant=merchant,
            category_id=category_id,
            necessity=necessity,
            is_split=is_split,
            version=1,
            created_by=actor,
        )

        if is_split:
            TransactionSplit.objects.bulk_create(
                [
                    TransactionSplit(
                        workspace=workspace,
                        transaction=tx,
                        category=cat,
                        amount_minor=amt,
                        memo=memo,
                    )
                    for cat, amt, memo in split_records
                ]
            )

        if tags:
            for tag_name in tags:
                tag, _ = Tag.objects.get_or_create(
                    workspace=workspace,
                    name=tag_name.strip(),
                )
                TransactionTag.objects.create(
                    transaction=tx,
                    tag=tag,
                    workspace=workspace,
                )

        if status == TransactionStatus.COMPLETED:
            account_ledger_acc = get_or_create_account_ledger_account(account=account)
            postings_spec: list[PostingSpec] = []

            if kind == TransactionType.EXPENSE:
                postings_spec.append(
                    PostingSpec(
                        ledger_account_id=account_ledger_acc.id,
                        amount_minor=-total_minor,
                        currency=currency,
                        memo=title,
                    )
                )
                for cat, amt, memo in split_records:
                    cat_ledger_acc = get_or_create_category_ledger_account(
                        category_id=cat.id,
                        workspace_id=workspace.id,
                        kind="expense",
                        name=cat.name,
                        currency_code=currency,
                    )
                    postings_spec.append(
                        PostingSpec(
                            ledger_account_id=cat_ledger_acc.id,
                            amount_minor=amt,
                            currency=currency,
                            memo=memo or title,
                        )
                    )
            elif kind == TransactionType.INCOME:
                postings_spec.append(
                    PostingSpec(
                        ledger_account_id=account_ledger_acc.id,
                        amount_minor=total_minor,
                        currency=currency,
                        memo=title,
                    )
                )
                for cat, amt, memo in split_records:
                    cat_ledger_acc = get_or_create_category_ledger_account(
                        category_id=cat.id,
                        workspace_id=workspace.id,
                        kind="income",
                        name=cat.name,
                        currency_code=currency,
                    )
                    postings_spec.append(
                        PostingSpec(
                            ledger_account_id=cat_ledger_acc.id,
                            amount_minor=-amt,
                            currency=currency,
                            memo=memo or title,
                        )
                    )

            if postings_spec:
                entry_spec = EntrySpec(
                    entry_type=kind,
                    status=str(JournalEntryStatus.POSTED),
                    effective_date=occurred_on,
                    source_type="transaction",
                    source_id=tx.id,
                    postings=postings_spec,
                    description=title,
                )
                entry = post_entry(workspace=workspace, actor=actor, spec=entry_spec)
                tx.current_journal_entry = entry
                tx.save(update_fields=["current_journal_entry"])

        after_state = {
            "title": title,
            "amount": amount,
            "currency": currency,
            "status": status,
            "kind": kind,
            "occurred_on": (
                occurred_on.isoformat() if hasattr(occurred_on, "isoformat") else str(occurred_on)
            ),
            "category_id": str(category_id) if category_id else None,
            "is_split": is_split,
        }
        TransactionAudit.objects.create(
            workspace=workspace,
            transaction=tx,
            revision=1,
            actor=actor,
            reason="Created",
            changed_fields=list(after_state.keys()),
            before={},
            after=after_state,
        )

        return tx
