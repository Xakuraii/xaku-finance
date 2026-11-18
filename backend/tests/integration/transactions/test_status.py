"""Integration tests for transaction statuses: pending, completed, cancelled."""

from __future__ import annotations

from datetime import date

import pytest

from apps.categories.models import Category, CategoryKind
from apps.ledger.selectors import postings_balance
from apps.ledger.services.accounts import get_or_create_account_ledger_account
from apps.transactions.models import TransactionStatus, TransactionType
from apps.transactions.services.create import create_transaction
from apps.transactions.services.update import update_transaction
from tests.factories.accounts import AccountFactory
from tests.factories.users import UserFactory


@pytest.fixture
def status_workspace(db):
    user = UserFactory()
    ws = user.workspace
    account = AccountFactory(workspace=ws, currency_id="USD")
    cat = Category.objects.create(workspace=ws, name="Shopping", kind=CategoryKind.EXPENSE)
    return {"user": user, "workspace": ws, "account": account, "cat": cat}


@pytest.mark.django_db
def test_pending_transaction_does_not_affect_balances(status_workspace):
    ctx = status_workspace
    ws = ctx["workspace"]
    account = ctx["account"]

    tx = create_transaction(
        workspace=ws,
        actor=ctx["user"],
        kind=TransactionType.EXPENSE,
        account_id=account.id,
        amount="150.00",
        currency="USD",
        occurred_on=date(2026, 11, 18),
        title="Pending online order",
        category_id=ctx["cat"].id,
        status=TransactionStatus.PENDING,
    )

    assert tx.status == TransactionStatus.PENDING
    assert tx.current_journal_entry_id is None

    acc_ledger = get_or_create_account_ledger_account(account=account)
    # Balance must remain untouched (0)
    assert postings_balance(ledger_account_id=acc_ledger.id) == 0

    # Now transition to completed
    updated = update_transaction(
        workspace=ws,
        actor=ctx["user"],
        transaction_id=tx.id,
        expected_version=1,
        reason="Order delivered",
        status=TransactionStatus.COMPLETED,
    )

    assert updated.status == TransactionStatus.COMPLETED
    assert updated.current_journal_entry_id is not None
    # Now balance is -150.00
    assert postings_balance(ledger_account_id=acc_ledger.id) == -15000


@pytest.mark.django_db
def test_cancelled_transaction_does_not_affect_balances(status_workspace):
    ctx = status_workspace
    ws = ctx["workspace"]
    account = ctx["account"]

    tx = create_transaction(
        workspace=ws,
        actor=ctx["user"],
        kind=TransactionType.EXPENSE,
        account_id=account.id,
        amount="75.00",
        currency="USD",
        occurred_on=date(2026, 11, 18),
        title="Dinner reservation",
        category_id=ctx["cat"].id,
        status=TransactionStatus.COMPLETED,
    )

    acc_ledger = get_or_create_account_ledger_account(account=account)
    assert postings_balance(ledger_account_id=acc_ledger.id) == -7500

    # Cancel transaction
    cancelled = update_transaction(
        workspace=ws,
        actor=ctx["user"],
        transaction_id=tx.id,
        expected_version=1,
        reason="Reservation cancelled and refunded",
        status=TransactionStatus.CANCELLED,
    )

    assert cancelled.status == TransactionStatus.CANCELLED
    # Balance must return to 0
    assert postings_balance(ledger_account_id=acc_ledger.id) == 0
