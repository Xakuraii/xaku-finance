"""Integration tests for creating transactions."""

from __future__ import annotations

from datetime import date

import pytest

from apps.categories.models import Category, CategoryKind
from apps.ledger.selectors import postings_balance
from apps.ledger.services.accounts import get_or_create_account_ledger_account
from apps.transactions.models import (
    TransactionAudit,
    TransactionStatus,
    TransactionTag,
    TransactionType,
)
from apps.transactions.services.create import create_transaction
from tests.factories.accounts import AccountFactory
from tests.factories.users import UserFactory


@pytest.fixture
def workspace_setup(db):
    user = UserFactory()
    ws = user.workspace
    account = AccountFactory(workspace=ws, currency_id="USD")
    food_cat = Category.objects.create(
        workspace=ws,
        name="Food",
        kind=CategoryKind.EXPENSE,
    )
    salary_cat = Category.objects.create(
        workspace=ws,
        name="Salary",
        kind=CategoryKind.INCOME,
    )
    return {
        "user": user,
        "workspace": ws,
        "account": account,
        "food": food_cat,
        "salary": salary_cat,
    }


@pytest.mark.django_db
def test_create_expense_transaction(workspace_setup):
    ctx = workspace_setup
    ws = ctx["workspace"]

    tx = create_transaction(
        workspace=ws,
        actor=ctx["user"],
        kind=TransactionType.EXPENSE,
        account_id=ctx["account"].id,
        amount="50.00",
        currency="USD",
        occurred_on=date(2026, 11, 18),
        title="Dinner",
        category_id=ctx["food"].id,
        tags=["Weekend", "Dining"],
        status=TransactionStatus.COMPLETED,
    )

    assert tx.amount_minor == 5000
    assert tx.status == TransactionStatus.COMPLETED
    assert tx.current_journal_entry_id is not None

    # Account balance should be -5000 minor units
    acc_ledger = get_or_create_account_ledger_account(account=ctx["account"])
    assert postings_balance(ledger_account_id=acc_ledger.id) == -5000

    # Tags should be created
    assert TransactionTag.objects.filter(transaction=tx).count() == 2

    # Audit revision 1 exists
    audit = TransactionAudit.objects.get(transaction=tx, revision=1)
    assert audit.reason == "Created"
    assert "amount" in audit.changed_fields


@pytest.mark.django_db
def test_create_income_transaction(workspace_setup):
    ctx = workspace_setup
    ws = ctx["workspace"]

    tx = create_transaction(
        workspace=ws,
        actor=ctx["user"],
        kind=TransactionType.INCOME,
        account_id=ctx["account"].id,
        amount="1000.00",
        currency="USD",
        occurred_on=date(2026, 11, 18),
        title="Paycheck",
        category_id=ctx["salary"].id,
        status=TransactionStatus.COMPLETED,
    )

    assert tx.amount_minor == 100_000
    acc_ledger = get_or_create_account_ledger_account(account=ctx["account"])
    assert postings_balance(ledger_account_id=acc_ledger.id) == 100_000
