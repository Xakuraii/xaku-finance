"""Database constraint tests for ledger integrity."""

from __future__ import annotations

from datetime import date

import pytest
from django.db import DatabaseError, IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import Account, AccountNature, AccountType
from apps.ledger.models import (
    JournalEntry,
    JournalEntryStatus,
    JournalEntryType,
    LedgerAccount,
    LedgerAccountKind,
    Posting,
)
from tests.factories.accounts import AccountFactory, LedgerAccountFactory
from tests.factories.users import UserFactory


@pytest.fixture
def workspace_with_accounts(db):
    user = UserFactory()
    ws = user.workspace

    cash_acc = LedgerAccountFactory(
        workspace=ws,
        kind=LedgerAccountKind.ASSET,
        code=f"asset:cash_{ws.id}",
        currency_id="USD",
    )
    expense_acc = LedgerAccountFactory(
        workspace=ws,
        kind=LedgerAccountKind.EXPENSE,
        code=f"expense:food_{ws.id}",
        currency_id="USD",
    )
    khr_acc = LedgerAccountFactory(
        workspace=ws,
        kind=LedgerAccountKind.ASSET,
        code=f"asset:khr_{ws.id}",
        currency_id="KHR",
    )
    return {
        "user": user,
        "workspace": ws,
        "cash": cash_acc,
        "expense": expense_acc,
        "khr": khr_acc,
    }


@pytest.mark.django_db(transaction=True)
def test_unbalanced_entry_is_rejected_at_commit(workspace_with_accounts):
    ctx = workspace_with_accounts
    ws = ctx["workspace"]

    with pytest.raises((IntegrityError, DatabaseError)):
        with transaction.atomic():
            entry = JournalEntry.objects.create(
                workspace=ws,
                entry_type=JournalEntryType.EXPENSE,
                status=JournalEntryStatus.POSTED,
                effective_date=date(2026, 11, 18),
                posted_at=timezone.now(),
                source_type="transaction",
                ledger_seq=1,
            )
            # Only one posting: unbalanced entry (+1000 minor)
            Posting.objects.create(
                journal_entry=entry,
                ledger_account=ctx["expense"],
                workspace=ws,
                currency_id="USD",
                amount_minor=1000,
            )


@pytest.mark.django_db(transaction=True)
def test_balanced_entry_is_accepted_at_commit(workspace_with_accounts):
    ctx = workspace_with_accounts
    ws = ctx["workspace"]

    with transaction.atomic():
        entry = JournalEntry.objects.create(
            workspace=ws,
            entry_type=JournalEntryType.EXPENSE,
            status=JournalEntryStatus.POSTED,
            effective_date=date(2026, 11, 18),
            posted_at=timezone.now(),
            source_type="transaction",
            ledger_seq=1,
        )
        Posting.objects.create(
            journal_entry=entry,
            ledger_account=ctx["expense"],
            workspace=ws,
            currency_id="USD",
            amount_minor=1000,
        )
        Posting.objects.create(
            journal_entry=entry,
            ledger_account=ctx["cash"],
            workspace=ws,
            currency_id="USD",
            amount_minor=-1000,
        )

    assert JournalEntry.objects.filter(id=entry.id).exists()
    assert Posting.objects.filter(journal_entry=entry).count() == 2


@pytest.mark.django_db(transaction=True)
def test_posting_currency_mismatch_rejected(workspace_with_accounts):
    ctx = workspace_with_accounts
    ws = ctx["workspace"]

    with pytest.raises((IntegrityError, DatabaseError)):
        with transaction.atomic():
            entry = JournalEntry.objects.create(
                workspace=ws,
                entry_type=JournalEntryType.EXPENSE,
                status=JournalEntryStatus.POSTED,
                effective_date=date(2026, 11, 18),
                posted_at=timezone.now(),
                source_type="transaction",
                ledger_seq=2,
            )
            # Cash is USD, but posting specifies KHR
            Posting.objects.create(
                journal_entry=entry,
                ledger_account=ctx["cash"],
                workspace=ws,
                currency_id="KHR",
                amount_minor=1000,
            )


@pytest.mark.django_db(transaction=True)
def test_posted_entry_immutability_rejects_delete_and_unauthorized_update(workspace_with_accounts):
    ctx = workspace_with_accounts
    ws = ctx["workspace"]

    with transaction.atomic():
        entry = JournalEntry.objects.create(
            workspace=ws,
            entry_type=JournalEntryType.EXPENSE,
            status=JournalEntryStatus.POSTED,
            effective_date=date(2026, 11, 18),
            posted_at=timezone.now(),
            source_type="transaction",
            ledger_seq=3,
        )
        Posting.objects.create(
            journal_entry=entry,
            ledger_account=ctx["expense"],
            workspace=ws,
            currency_id="USD",
            amount_minor=500,
        )
        Posting.objects.create(
            journal_entry=entry,
            ledger_account=ctx["cash"],
            workspace=ws,
            currency_id="USD",
            amount_minor=-500,
        )

    # Deleting a posted entry must be rejected
    with pytest.raises((IntegrityError, DatabaseError)):
        with transaction.atomic():
            entry.delete()

    # Changing effective date of a posted entry must be rejected
    with pytest.raises((IntegrityError, DatabaseError)):
        with transaction.atomic():
            entry.effective_date = date(2026, 11, 19)
            entry.save(update_fields=["effective_date"])


@pytest.mark.django_db
def test_one_ledger_account_per_account(workspace_with_accounts):
    ctx = workspace_with_accounts
    ws = ctx["workspace"]
    account = AccountFactory(workspace=ws)

    # First ledger account for this owner
    LedgerAccount.objects.create(
        workspace=ws,
        kind=LedgerAccountKind.ASSET,
        code=f"asset:acc_{account.id}",
        name=account.name,
        currency_id="USD",
        owner_type="account",
        owner_id=account.id,
    )

    # Duplicate owner should violate unique constraint
    with pytest.raises(IntegrityError):
        LedgerAccount.objects.create(
            workspace=ws,
            kind=LedgerAccountKind.ASSET,
            code=f"asset:acc2_{account.id}",
            name=account.name,
            currency_id="USD",
            owner_type="account",
            owner_id=account.id,
        )


@pytest.mark.django_db
def test_account_constraints(workspace_with_accounts):
    ws = workspace_with_accounts["workspace"]

    # Savings account cannot be spendable by default rule
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Account.objects.create(
                workspace=ws,
                name="Savings High Yield",
                account_type=AccountType.SAVINGS,
                currency_id="USD",
                nature=AccountNature.ASSET,
                is_spendable=True,  # Violates constraint
                opened_on=date.today(),
            )

    # Credit card must have nature liability
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Account.objects.create(
                workspace=ws,
                name="Credit Card A",
                account_type=AccountType.CREDIT_CARD,
                currency_id="USD",
                nature=AccountNature.ASSET,  # Violates constraint
                opened_on=date.today(),
            )
