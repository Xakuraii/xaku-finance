"""Internal transfer service: same-currency and cross-currency FX clearing."""

from __future__ import annotations

import uuid
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Account
from apps.categories.models import Category
from apps.common.money import Money
from apps.ledger.models import JournalEntryStatus, LedgerAccount, LedgerAccountKind
from apps.ledger.services.accounts import (
    get_or_create_account_ledger_account,
    get_or_create_category_ledger_account,
)
from apps.ledger.services.posting import EntrySpec, PostingSpec, post_entry
from apps.ledger.services.reversal import reverse_entry
from apps.transactions.models import (
    Transaction,
    TransactionAudit,
    TransactionStatus,
    TransactionType,
    Transfer,
)

if TYPE_CHECKING:
    from datetime import date

    from apps.identity.models import User
    from apps.workspaces.models import Workspace


class TransferError(ValueError):
    """Base error for transfer failures."""


class SameAccountTransferError(TransferError):
    """Source and destination accounts must be different."""


class ArchivedAccountTransferError(TransferError):
    """Cannot transfer between archived accounts."""


class InsufficientFundsError(TransferError):
    """Insufficient funds in source account."""


def get_or_create_fx_clearing_account(*, workspace: Workspace, currency_code: str) -> LedgerAccount:
    """Ensure an FX clearing ledger account exists for the given currency."""
    acc, _ = LedgerAccount.objects.get_or_create(
        workspace=workspace,
        code=f"fx_clearing:{currency_code}",
        defaults={
            "name": f"FX Clearing ({currency_code})",
            "kind": LedgerAccountKind.EQUITY,
            "currency_id": currency_code,
            "is_system": True,
        },
    )
    return acc


def create_transfer(
    *,
    workspace: Workspace,
    actor: User | None,
    source_account_id: uuid.UUID,
    destination_account_id: uuid.UUID,
    amount: str | Decimal,
    destination_amount: str | Decimal | None = None,
    rate: Decimal | None = None,
    reference_rate: Decimal | None = None,
    transfer_fee: str | Decimal = "0.00",
    transfer_fee_category_id: uuid.UUID | None = None,
    conversion_fee_category_id: uuid.UUID | None = None,
    occurred_on: date,
    notes: str = "",
) -> tuple[Transaction, Transfer]:
    """Execute an atomic internal transfer with double-entry ledger postings."""
    if source_account_id == destination_account_id:
        raise SameAccountTransferError("Source and destination accounts must be different.")

    with transaction.atomic():
        # Lock accounts in deterministic order by UUID to prevent deadlocks
        account_ids = sorted([source_account_id, destination_account_id])
        locked_accounts = {
            acc.id: acc
            for acc in Account.objects.select_for_update().filter(
                id__in=account_ids, workspace=workspace
            )
        }

        if source_account_id not in locked_accounts:
            raise TransferError(f"Source account {source_account_id} not found in workspace.")
        if destination_account_id not in locked_accounts:
            raise TransferError(
                f"Destination account {destination_account_id} not found in workspace."
            )

        source_acc = locked_accounts[source_account_id]
        dest_acc = locked_accounts[destination_account_id]

        if source_acc.is_archived:
            raise ArchivedAccountTransferError(f"Source account '{source_acc.name}' is archived.")
        if dest_acc.is_archived:
            raise ArchivedAccountTransferError(
                f"Destination account '{dest_acc.name}' is archived."
            )

        src_money = Money.parse(str(amount), source_acc.currency_id)
        if src_money.amount_minor <= 0:
            raise TransferError("Transfer amount must be strictly positive.")

        fee_money = Money.parse(str(transfer_fee), source_acc.currency_id)
        if fee_money.amount_minor < 0:
            raise TransferError("Transfer fee cannot be negative.")

        is_cross_currency = source_acc.currency_id != dest_acc.currency_id

        if not is_cross_currency:
            dest_minor = src_money.amount_minor
            rate_val = Decimal("1.0000000000")
            ref_rate_val = Decimal("1.0000000000")
            conversion_fee_minor = 0
        else:
            if rate is None and destination_amount is None:
                raise TransferError(
                    "Cross-currency transfer requires exchange rate or destination amount."
                )

            if destination_amount is not None:
                dest_money = Money.parse(str(destination_amount), dest_acc.currency_id)
                dest_minor = dest_money.amount_minor
            else:
                dest_major = (Decimal(src_money.serialize()) * Decimal(str(rate))).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                dest_money = Money.parse(str(dest_major), dest_acc.currency_id)
                dest_minor = dest_money.amount_minor

            if rate is not None:
                rate_val = Decimal(str(rate))
            else:
                rate_val = (
                    Decimal(dest_money.serialize()) / Decimal(src_money.serialize())
                ).quantize(Decimal("0.0000000001"))

            if reference_rate is not None:
                ref_rate_val = Decimal(str(reference_rate))
                expected_dest_major = (Decimal(src_money.serialize()) * ref_rate_val).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                expected_dest_money = Money.parse(str(expected_dest_major), dest_acc.currency_id)
                conversion_fee_minor = max(0, expected_dest_money.amount_minor - dest_minor)
            else:
                ref_rate_val = rate_val
                conversion_fee_minor = 0

        # Build ledger postings
        postings: list[PostingSpec] = []
        source_ledger_acc = get_or_create_account_ledger_account(account=source_acc)
        dest_ledger_acc = get_or_create_account_ledger_account(account=dest_acc)

        if not is_cross_currency:
            # Single-currency transfer
            # 1. Credit source account
            total_source_deduction = src_money.amount_minor + fee_money.amount_minor
            postings.append(
                PostingSpec(
                    ledger_account_id=source_ledger_acc.id,
                    amount_minor=-total_source_deduction,
                    currency=source_acc.currency_id,
                    memo=f"Transfer to {dest_acc.name}",
                )
            )
            # 2. Debit destination account
            postings.append(
                PostingSpec(
                    ledger_account_id=dest_ledger_acc.id,
                    amount_minor=dest_minor,
                    currency=dest_acc.currency_id,
                    memo=f"Transfer from {source_acc.name}",
                )
            )
            # 3. Debit transfer fee expense if applicable
            if fee_money.amount_minor > 0:
                fee_cat_id = transfer_fee_category_id
                if not fee_cat_id:
                    raise TransferError("Transfer fee category is required when fee > 0.")
                fee_cat = Category.objects.get(id=fee_cat_id, workspace=workspace)
                fee_ledger_acc = get_or_create_category_ledger_account(
                    category_id=fee_cat.id,
                    workspace_id=workspace.id,
                    kind="expense",
                    name=fee_cat.name,
                    currency_code=source_acc.currency_id,
                )
                postings.append(
                    PostingSpec(
                        ledger_account_id=fee_ledger_acc.id,
                        amount_minor=fee_money.amount_minor,
                        currency=source_acc.currency_id,
                        memo=f"Transfer fee: {source_acc.name} -> {dest_acc.name}",
                    )
                )
        else:
            # Cross-currency transfer
            # Leg 1: Source Currency (e.g. USD)
            total_source_deduction = src_money.amount_minor + fee_money.amount_minor
            postings.append(
                PostingSpec(
                    ledger_account_id=source_ledger_acc.id,
                    amount_minor=-total_source_deduction,
                    currency=source_acc.currency_id,
                    memo=f"Transfer out to {dest_acc.name} ({dest_acc.currency_id})",
                )
            )
            fx_clearing_src = get_or_create_fx_clearing_account(
                workspace=workspace, currency_code=source_acc.currency_id
            )
            postings.append(
                PostingSpec(
                    ledger_account_id=fx_clearing_src.id,
                    amount_minor=src_money.amount_minor,
                    currency=source_acc.currency_id,
                    memo=f"FX clearing out -> {dest_acc.currency_id}",
                )
            )
            if fee_money.amount_minor > 0:
                if not transfer_fee_category_id:
                    raise TransferError("Transfer fee category is required when fee > 0.")
                fee_cat = Category.objects.get(id=transfer_fee_category_id, workspace=workspace)
                fee_ledger_acc = get_or_create_category_ledger_account(
                    category_id=fee_cat.id,
                    workspace_id=workspace.id,
                    kind="expense",
                    name=fee_cat.name,
                    currency_code=source_acc.currency_id,
                )
                postings.append(
                    PostingSpec(
                        ledger_account_id=fee_ledger_acc.id,
                        amount_minor=fee_money.amount_minor,
                        currency=source_acc.currency_id,
                        memo="Transfer bank fee",
                    )
                )

            # Leg 2: Destination Currency (e.g. KHR)
            postings.append(
                PostingSpec(
                    ledger_account_id=dest_ledger_acc.id,
                    amount_minor=dest_minor,
                    currency=dest_acc.currency_id,
                    memo=f"Transfer in from {source_acc.name} ({source_acc.currency_id})",
                )
            )
            if conversion_fee_minor > 0:
                if not conversion_fee_category_id:
                    raise TransferError("Conversion fee category is required when spread > 0.")
                conv_cat = Category.objects.get(id=conversion_fee_category_id, workspace=workspace)
                conv_ledger_acc = get_or_create_category_ledger_account(
                    category_id=conv_cat.id,
                    workspace_id=workspace.id,
                    kind="expense",
                    name=conv_cat.name,
                    currency_code=dest_acc.currency_id,
                )
                postings.append(
                    PostingSpec(
                        ledger_account_id=conv_ledger_acc.id,
                        amount_minor=conversion_fee_minor,
                        currency=dest_acc.currency_id,
                        memo="FX conversion fee / spread",
                    )
                )

            fx_clearing_dst = get_or_create_fx_clearing_account(
                workspace=workspace, currency_code=dest_acc.currency_id
            )
            fx_clearing_dest_amount = dest_minor + conversion_fee_minor
            postings.append(
                PostingSpec(
                    ledger_account_id=fx_clearing_dst.id,
                    amount_minor=-fx_clearing_dest_amount,
                    currency=dest_acc.currency_id,
                    memo=f"FX clearing in <- {source_acc.currency_id}",
                )
            )

        entry_spec = EntrySpec(
            entry_type="transfer",
            status=str(JournalEntryStatus.POSTED),
            effective_date=occurred_on,
            source_type="transfer",
            source_id=None,
            postings=postings,
            description=f"Transfer {source_acc.name} -> {dest_acc.name}",
        )

        entry = post_entry(workspace=workspace, spec=entry_spec, actor=actor)

        tx = Transaction.objects.create(
            workspace=workspace,
            account=source_acc,
            currency_id=source_acc.currency_id,
            transaction_type=TransactionType.TRANSFER,
            status=TransactionStatus.COMPLETED,
            amount_minor=src_money.amount_minor,
            occurred_on=occurred_on,
            title=f"Transfer: {source_acc.name} -> {dest_acc.name}",
            notes=notes,
            current_journal_entry=entry,
            version=1,
            created_by=actor,
        )

        transfer_obj = Transfer.objects.create(
            transaction=tx,
            workspace=workspace,
            source_account=source_acc,
            destination_account=dest_acc,
            source_amount_minor=src_money.amount_minor,
            destination_amount_minor=dest_minor,
            rate=rate_val,
            reference_rate=ref_rate_val,
            conversion_fee_minor=conversion_fee_minor,
            conversion_fee_category_id=conversion_fee_category_id,
            transfer_fee_minor=fee_money.amount_minor,
            transfer_fee_category_id=transfer_fee_category_id,
            notes=notes,
        )

        # Audit log revision 1
        TransactionAudit.objects.create(
            workspace=workspace,
            transaction=tx,
            revision=1,
            actor=actor,
            reason="Create transfer",
            changed_fields=[
                "source_account",
                "destination_account",
                "amount",
                "destination_amount",
                "rate",
            ],
            before={},
            after={
                "source_account_id": str(source_acc.id),
                "destination_account_id": str(dest_acc.id),
                "amount": src_money.serialize(),
                "currency": source_acc.currency_id,
                "destination_amount_minor": dest_minor,
                "rate": str(rate_val),
            },
        )

        return tx, transfer_obj


def archive_transfer(
    *,
    transfer_id: uuid.UUID,
    actor: User | None,
    reason: str,
) -> Transaction:
    """Archive a transfer, atomically reversing its ledger entry and recording audit history."""
    with transaction.atomic():
        tx = Transaction.objects.select_for_update().get(id=transfer_id)
        if tx.is_archived:
            return tx

        if tx.current_journal_entry:
            reverse_entry(
                workspace=tx.workspace,
                actor=actor,
                entry=tx.current_journal_entry,
                reason=f"Archive transfer: {reason}",
            )

        tx.is_archived = True
        tx.archived_at = timezone.now()
        tx.version += 1
        tx.save(update_fields=["is_archived", "archived_at", "version", "updated_at"])

        TransactionAudit.objects.create(
            workspace=tx.workspace,
            transaction=tx,
            revision=tx.version,
            actor=actor,
            reason=f"Archive: {reason}",
            changed_fields=["is_archived"],
            before={"is_archived": False},
            after={"is_archived": True, "archive_reason": reason},
        )

        return tx
