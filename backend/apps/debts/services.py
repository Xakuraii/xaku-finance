"""Debt domain services: double-entry disbursement, split repayments, and interest accrual."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from django.db import transaction

from apps.accounts.models import Account
from apps.common.money import Money
from apps.debts.models import (
    DebtInterestRecord,
    DebtRepayment,
    InterestType,
    Liability,
    LiabilityStatus,
)
from apps.ledger.models import (
    JournalEntryStatus,
    JournalEntryType,
    LedgerAccount,
    LedgerAccountKind,
)
from apps.ledger.selectors import postings_balance
from apps.ledger.services.accounts import (
    get_or_create_account_ledger_account,
    provision_system_accounts,
)
from apps.ledger.services.posting import EntrySpec, PostingSpec, post_entry
from apps.transactions.models import Transaction, TransactionStatus, TransactionType

if TYPE_CHECKING:
    from apps.identity.models import User
    from apps.workspaces.models import Workspace


class DebtError(ValueError):
    """Base error for debt operations."""


class OverpaymentError(DebtError):
    """Raised when a principal repayment exceeds the outstanding liability balance."""


class LiabilityArchivedError(DebtError):
    """Raised when attempting to operate on an archived liability."""


def get_or_create_system_ledger_account(
    *,
    workspace: Workspace,
    code: str,
    name: str,
    kind: str,
    currency_code: str,
) -> LedgerAccount:
    """Ensure a system ledger account exists."""
    acc, _ = LedgerAccount.objects.get_or_create(
        workspace=workspace,
        code=code,
        defaults={
            "name": name,
            "kind": kind,
            "currency_id": currency_code,
            "is_system": True,
        },
    )
    return acc


@transaction.atomic
def create_liability(
    *,
    workspace: Workspace,
    actor: User,
    name: str,
    original_principal: str | Decimal | int,
    currency: str,
    liability_type: str = "personal_loan",
    interest_rate: str | Decimal | None = None,
    interest_type: str = "none",
    lender: str | None = None,
    due_day: int | None = None,
    next_due_date: date | None = None,
    linked_account_id: str | None = None,
    initial_disbursement_account_id: str | None = None,
    disbursement_date: date | None = None,
    notes: str | None = None,
) -> Liability:
    """Create a liability with its 1:1 ledger account and optional disbursement."""
    currency_code = currency.strip().upper()
    if isinstance(original_principal, (int, Decimal)):
        money = Money(
            int(original_principal)
            if isinstance(original_principal, int)
            else int(Decimal(original_principal) * 100),
            currency_code,
            2,
        )
    else:
        money = Money.parse(str(original_principal), currency_code, 2)

    if money.amount_minor <= 0:
        raise DebtError("Original principal must be strictly positive.")

    rate_dec = None
    if interest_rate is not None:
        rate_dec = Decimal(str(interest_rate))
        if rate_dec < 0:
            raise DebtError("Interest rate cannot be negative.")

    linked_account = None
    if linked_account_id:
        try:
            linked_account = Account.objects.get(
                id=linked_account_id,
                workspace=workspace,
                is_archived=False,
            )
        except Account.DoesNotExist as exc:
            raise DebtError("Linked account not found or archived.") from exc

    # Create dedicated 1:1 LedgerAccount for this liability
    ledger_account = LedgerAccount.objects.create(
        workspace=workspace,
        kind=LedgerAccountKind.LIABILITY,
        code=f"liability:{uuid.uuid4()}",
        name=f"Liability: {name.strip()}",
        currency_id=currency_code,
        is_system=False,
        owner_type="liability",
    )

    liability = Liability.objects.create(
        workspace=workspace,
        name=name.strip(),
        liability_type=liability_type,
        currency_code=currency_code,
        original_principal_minor=money.amount_minor,
        interest_rate=rate_dec,
        interest_type=interest_type if rate_dec else InterestType.NONE,
        lender=lender.strip() if lender else None,
        due_day=due_day,
        next_due_date=next_due_date,
        linked_account=linked_account,
        ledger_account=ledger_account,
        notes=notes,
        status=LiabilityStatus.ACTIVE,
    )
    ledger_account.owner_id = liability.id
    ledger_account.save(update_fields=["owner_id"])

    effective_date = disbursement_date or date.today()

    if initial_disbursement_account_id:
        # Disburse funds into an asset account
        try:
            disburse_account = Account.objects.select_for_update().get(
                id=initial_disbursement_account_id,
                workspace=workspace,
                is_archived=False,
            )
        except Account.DoesNotExist as exc:
            raise DebtError("Disbursement account not found or archived.") from exc

        if disburse_account.currency_id != currency_code:
            raise DebtError(
                f"Disbursement account currency ({disburse_account.currency_id}) "
                f"does not match loan currency ({currency_code})."
            )

        asset_ledger_acc = get_or_create_account_ledger_account(account=disburse_account)

        # Journal Entry: Debit asset (cash received), Credit liability (debt owed)
        entry_spec = EntrySpec(
            entry_type=str(JournalEntryType.DEBT_DISBURSEMENT),
            status=str(JournalEntryStatus.POSTED),
            effective_date=effective_date,
            source_type="debt_disbursement",
            source_id=liability.id,
            description=f"Disbursement for {liability.name}",
            postings=[
                PostingSpec(
                    ledger_account_id=asset_ledger_acc.id,
                    amount_minor=money.amount_minor,  # Debit asset
                    currency=currency_code,
                    memo=f"Disbursement to {disburse_account.name}",
                ),
                PostingSpec(
                    ledger_account_id=ledger_account.id,
                    amount_minor=-money.amount_minor,  # Credit liability
                    currency=currency_code,
                    memo=f"Liability incurred for {liability.name}",
                ),
            ],
        )
        post_entry(workspace=workspace, actor=actor, spec=entry_spec)

        # Create Transaction record
        Transaction.objects.create(
            workspace=workspace,
            account=disburse_account,
            transaction_type=TransactionType.DEBT_DISBURSEMENT,
            status=TransactionStatus.COMPLETED,
            amount_minor=money.amount_minor,
            currency_id=currency_code,
            title=f"Disbursement: {liability.name}",
            occurred_on=effective_date,
            notes=f"Initial loan disbursement from {lender or 'lender'}",
        )
    else:
        # Opening balance equity for pre-existing liability
        provision_system_accounts(workspace=workspace)
        equity_acc = get_or_create_system_ledger_account(
            workspace=workspace,
            code=f"equity:opening_balance:{currency_code}",
            name=f"Opening Balance Equity ({currency_code})",
            kind=str(LedgerAccountKind.EQUITY),
            currency_code=currency_code,
        )

        entry_spec = EntrySpec(
            entry_type=str(JournalEntryType.OPENING_BALANCE),
            status=str(JournalEntryStatus.POSTED),
            effective_date=effective_date,
            source_type="liability_opening",
            source_id=liability.id,
            description=f"Opening liability for {liability.name}",
            postings=[
                PostingSpec(
                    ledger_account_id=equity_acc.id,
                    amount_minor=money.amount_minor,  # Debit equity
                    currency=currency_code,
                    memo="Opening balance equity offset",
                ),
                PostingSpec(
                    ledger_account_id=ledger_account.id,
                    amount_minor=-money.amount_minor,  # Credit liability
                    currency=currency_code,
                    memo="Initial liability balance",
                ),
            ],
        )
        post_entry(workspace=workspace, actor=actor, spec=entry_spec)

    return liability


@transaction.atomic
def record_debt_repayment(
    *,
    workspace: Workspace,
    actor: User,
    liability: Liability,
    paying_account_id: str,
    principal_amount: str | Decimal | int = "0.00",
    interest_amount: str | Decimal | int = "0.00",
    fee_amount: str | Decimal | int = "0.00",
    paid_on: date | None = None,
    note: str | None = None,
) -> DebtRepayment:
    """Record an atomic debt repayment, splitting principal reduction from interest and fees."""
    if liability.is_archived or liability.status == LiabilityStatus.ARCHIVED:
        raise LiabilityArchivedError("Cannot make repayment to an archived liability.")

    currency_code = liability.currency_code

    p_minor = (
        Money.parse(str(principal_amount), currency_code, 2).amount_minor
        if isinstance(principal_amount, (str, Decimal))
        else int(principal_amount)
    )
    i_minor = (
        Money.parse(str(interest_amount), currency_code, 2).amount_minor
        if isinstance(interest_amount, (str, Decimal))
        else int(interest_amount)
    )
    f_minor = (
        Money.parse(str(fee_amount), currency_code, 2).amount_minor
        if isinstance(fee_amount, (str, Decimal))
        else int(fee_amount)
    )

    if p_minor < 0 or i_minor < 0 or f_minor < 0:
        raise DebtError("Repayment components must be non-negative.")

    total_payment_minor = p_minor + i_minor + f_minor
    if total_payment_minor <= 0:
        raise DebtError("Total repayment amount must be strictly positive.")

    # Lock paying account and liability's ledger account
    try:
        paying_account = Account.objects.select_for_update().get(
            id=paying_account_id, workspace=workspace, is_archived=False
        )
    except Account.DoesNotExist as exc:
        raise DebtError("Paying account not found or archived.") from exc

    if paying_account.currency_id != currency_code:
        raise DebtError(
            f"Paying account currency ({paying_account.currency_id}) "
            f"does not match liability currency ({currency_code})."
        )

    # Derive outstanding principal from ledger postings
    current_postings = postings_balance(ledger_account_id=liability.ledger_account_id)
    outstanding_principal = -current_postings

    if p_minor > outstanding_principal:
        raise OverpaymentError(
            f"Principal repayment of {p_minor} minor units exceeds remaining "
            f"outstanding principal ({outstanding_principal}) for '{liability.name}'."
        )

    event_date = paid_on or date.today()
    asset_ledger_acc = get_or_create_account_ledger_account(account=paying_account)

    # Construct balanced journal entry postings
    postings: list[PostingSpec] = [
        # Credit asset (reduces checking/cash)
        PostingSpec(
            ledger_account_id=asset_ledger_acc.id,
            amount_minor=-total_payment_minor,
            currency=currency_code,
            memo=f"Repayment for {liability.name}",
        ),
    ]

    if p_minor > 0:
        # Debit liability (reduces debt)
        postings.append(
            PostingSpec(
                ledger_account_id=liability.ledger_account_id,
                amount_minor=p_minor,
                currency=currency_code,
                memo="Principal reduction",
            )
        )

    if i_minor > 0:
        # Debit interest expense
        interest_exp_acc = get_or_create_system_ledger_account(
            workspace=workspace,
            code=f"expense:interest:{currency_code}",
            name=f"Interest Expense ({currency_code})",
            kind=str(LedgerAccountKind.EXPENSE),
            currency_code=currency_code,
        )
        postings.append(
            PostingSpec(
                ledger_account_id=interest_exp_acc.id,
                amount_minor=i_minor,
                currency=currency_code,
                memo=f"Interest on {liability.name}",
            )
        )

    if f_minor > 0:
        # Debit bank / financing fee expense
        fee_exp_acc = get_or_create_system_ledger_account(
            workspace=workspace,
            code=f"expense:bank_fees:{currency_code}",
            name=f"Bank & Financing Fees ({currency_code})",
            kind=str(LedgerAccountKind.EXPENSE),
            currency_code=currency_code,
        )
        postings.append(
            PostingSpec(
                ledger_account_id=fee_exp_acc.id,
                amount_minor=f_minor,
                currency=currency_code,
                memo=f"Repayment fee on {liability.name}",
            )
        )

    # Post balanced entry
    entry_spec = EntrySpec(
        entry_type=str(JournalEntryType.DEBT_REPAYMENT),
        status=str(JournalEntryStatus.POSTED),
        effective_date=event_date,
        source_type="debt_repayment",
        source_id=liability.id,
        description=f"Debt repayment to {liability.name}",
        postings=postings,
    )
    post_entry(workspace=workspace, actor=actor, spec=entry_spec)

    # Create Transaction
    tx = Transaction.objects.create(
        workspace=workspace,
        account=paying_account,
        transaction_type=TransactionType.DEBT_REPAYMENT,
        status=TransactionStatus.COMPLETED,
        amount_minor=total_payment_minor,
        currency_id=currency_code,
        title=f"Repayment: {liability.name}",
        occurred_on=event_date,
        notes=note,
    )

    # Create DebtRepayment detail
    repayment = DebtRepayment.objects.create(
        workspace=workspace,
        liability=liability,
        transaction=tx,
        principal_minor=p_minor,
        interest_minor=i_minor,
        fee_minor=f_minor,
        currency_code=currency_code,
        paid_on=event_date,
        note=note,
    )

    # Update status if paid off
    if outstanding_principal - p_minor == 0:
        liability.status = LiabilityStatus.PAID_OFF
        liability.save(update_fields=["status", "updated_at"])

    return repayment


@transaction.atomic
def record_accrued_interest(
    *,
    workspace: Workspace,
    actor: User,
    liability: Liability,
    amount: str | Decimal | int,
    period_start: date,
    period_end: date,
    rate_used: str | Decimal | None = None,
    note: str | None = None,
) -> DebtInterestRecord:
    """Record accrued interest charged to the loan (increasing outstanding principal)."""
    if liability.is_archived:
        raise LiabilityArchivedError("Cannot accrue interest on an archived liability.")

    currency_code = liability.currency_code
    if isinstance(amount, (int, Decimal)):
        money = Money(
            int(amount) if isinstance(amount, int) else int(Decimal(amount) * 100), currency_code, 2
        )
    else:
        money = Money.parse(str(amount), currency_code, 2)

    if money.amount_minor <= 0:
        raise DebtError("Interest amount must be strictly positive.")

    interest_exp_acc = get_or_create_system_ledger_account(
        workspace=workspace,
        code=f"expense:interest:{currency_code}",
        name=f"Interest Expense ({currency_code})",
        kind=str(LedgerAccountKind.EXPENSE),
        currency_code=currency_code,
    )

    # Journal Entry: Debit interest expense, Credit liability (increases outstanding)
    entry_spec = EntrySpec(
        entry_type=str(JournalEntryType.ADJUSTMENT),
        status=str(JournalEntryStatus.POSTED),
        effective_date=period_end,
        source_type="accrued_interest",
        source_id=liability.id,
        description=f"Interest accrued on {liability.name}",
        postings=[
            PostingSpec(
                ledger_account_id=interest_exp_acc.id,
                amount_minor=money.amount_minor,  # Debit expense
                currency=currency_code,
                memo=f"Interest accrual {period_start} to {period_end}",
            ),
            PostingSpec(
                ledger_account_id=liability.ledger_account_id,
                amount_minor=-money.amount_minor,  # Credit liability (adds debt)
                currency=currency_code,
                memo="Interest added to principal",
            ),
        ],
    )
    post_entry(workspace=workspace, actor=actor, spec=entry_spec)

    rec = DebtInterestRecord.objects.create(
        workspace=workspace,
        liability=liability,
        period_start=period_start,
        period_end=period_end,
        amount_minor=money.amount_minor,
        rate_used=Decimal(str(rate_used)) if rate_used is not None else None,
        note=note,
    )
    return rec


@transaction.atomic
def archive_liability(*, liability: Liability, actor: User) -> Liability:
    """Archive a liability."""
    liability.is_archived = True
    liability.status = LiabilityStatus.ARCHIVED
    liability.save(update_fields=["is_archived", "status", "updated_at"])
    return liability


@transaction.atomic
def restore_liability(*, liability: Liability, actor: User) -> Liability:
    """Restore an archived liability."""
    liability.is_archived = False
    current_postings = postings_balance(ledger_account_id=liability.ledger_account_id)
    liability.status = LiabilityStatus.PAID_OFF if current_postings == 0 else LiabilityStatus.ACTIVE
    liability.save(update_fields=["is_archived", "status", "updated_at"])
    return liability
