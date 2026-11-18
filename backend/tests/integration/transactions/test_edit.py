"""Integration tests for transaction editing, versioning, reversal, and audit."""

from __future__ import annotations

from datetime import date

import pytest

from apps.categories.models import Category, CategoryKind
from apps.ledger.models import JournalEntryStatus
from apps.ledger.selectors import postings_balance
from apps.ledger.services.accounts import get_or_create_account_ledger_account
from apps.transactions.models import TransactionAudit, TransactionStatus, TransactionType
from apps.transactions.services.archive import archive_transaction, restore_transaction
from apps.transactions.services.create import create_transaction
from apps.transactions.services.update import VersionConflict, update_transaction
from tests.factories.accounts import AccountFactory
from tests.factories.users import UserFactory


@pytest.fixture
def edit_workspace(db):
    user = UserFactory()
    ws = user.workspace
    account = AccountFactory(workspace=ws, currency_id="USD")
    food = Category.objects.create(workspace=ws, name="Food", kind=CategoryKind.EXPENSE)
    travel = Category.objects.create(workspace=ws, name="Travel", kind=CategoryKind.EXPENSE)
    return {"user": user, "workspace": ws, "account": account, "food": food, "travel": travel}


@pytest.mark.django_db
def test_edit_reverses_and_appends_audit(edit_workspace):
    ctx = edit_workspace
    ws = ctx["workspace"]

    tx = create_transaction(
        workspace=ws,
        actor=ctx["user"],
        kind=TransactionType.EXPENSE,
        account_id=ctx["account"].id,
        amount="100.00",
        currency="USD",
        occurred_on=date(2026, 11, 18),
        title="Original dinner",
        category_id=ctx["food"].id,
        status=TransactionStatus.COMPLETED,
    )
    first_entry = tx.current_journal_entry
    assert first_entry is not None

    # Update amount to 110.00
    updated = update_transaction(
        workspace=ws,
        actor=ctx["user"],
        transaction_id=tx.id,
        expected_version=1,
        reason="Updated bill amount",
        amount="110.00",
    )

    first_entry.refresh_from_db()
    assert first_entry.status == JournalEntryStatus.REVERSED
    assert updated.current_journal_entry_id != first_entry.id
    assert updated.version == 2
    assert updated.amount_minor == 11000

    # Account balance reflects updated amount (-110.00)
    acc_ledger = get_or_create_account_ledger_account(account=ctx["account"])
    assert postings_balance(ledger_account_id=acc_ledger.id) == -11000

    # Audit records exist
    assert TransactionAudit.objects.filter(transaction=tx).count() == 2
    audit2 = TransactionAudit.objects.get(transaction=tx, revision=2)
    assert audit2.reason == "Updated bill amount"
    assert "amount" in audit2.changed_fields


@pytest.mark.django_db
def test_stale_version_writes_nothing(edit_workspace):
    ctx = edit_workspace
    ws = ctx["workspace"]

    tx = create_transaction(
        workspace=ws,
        actor=ctx["user"],
        kind=TransactionType.EXPENSE,
        account_id=ctx["account"].id,
        amount="100.00",
        currency="USD",
        occurred_on=date(2026, 11, 18),
        title="Dinner",
        category_id=ctx["food"].id,
    )

    # First update bumps version to 2
    update_transaction(
        workspace=ws,
        actor=ctx["user"],
        transaction_id=tx.id,
        expected_version=1,
        reason="Update 1",
        title="Dinner v2",
    )

    # Stale update attempting expected_version=1 should raise VersionConflict
    with pytest.raises(VersionConflict):
        update_transaction(
            workspace=ws,
            actor=ctx["user"],
            transaction_id=tx.id,
            expected_version=1,
            reason="Update stale",
            title="Dinner stale",
        )


@pytest.mark.django_db
def test_archive_and_restore_transaction(edit_workspace):
    ctx = edit_workspace
    ws = ctx["workspace"]

    tx = create_transaction(
        workspace=ws,
        actor=ctx["user"],
        kind=TransactionType.EXPENSE,
        account_id=ctx["account"].id,
        amount="80.00",
        currency="USD",
        occurred_on=date(2026, 11, 18),
        title="Taxi",
        category_id=ctx["travel"].id,
        status=TransactionStatus.COMPLETED,
    )

    acc_ledger = get_or_create_account_ledger_account(account=ctx["account"])
    assert postings_balance(ledger_account_id=acc_ledger.id) == -8000

    # Archiving reverses the entry so balance goes back to 0
    archived = archive_transaction(
        workspace=ws,
        actor=ctx["user"],
        transaction_id=tx.id,
        reason="Entered in wrong account",
    )
    assert archived.is_archived is True
    assert postings_balance(ledger_account_id=acc_ledger.id) == 0

    # Restoring re-posts the entry so balance is -8000 again
    restored = restore_transaction(
        workspace=ws,
        actor=ctx["user"],
        transaction_id=tx.id,
    )
    assert restored.is_archived is False
    assert postings_balance(ledger_account_id=acc_ledger.id) == -8000
