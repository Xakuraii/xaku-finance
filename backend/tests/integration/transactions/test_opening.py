"""Integration tests for account opening balances."""

from __future__ import annotations

from datetime import date

import pytest

from apps.ledger.selectors import postings_balance
from apps.ledger.services.accounts import get_or_create_account_ledger_account
from apps.transactions.models import TransactionType
from apps.transactions.selectors import expense_total, income_total
from apps.transactions.services.opening import (
    DuplicateOpeningBalance,
    create_opening_balance,
)
from tests.factories.accounts import AccountFactory
from tests.factories.users import UserFactory


@pytest.fixture
def opening_workspace(db):
    user = UserFactory()
    ws = user.workspace
    account = AccountFactory(workspace=ws, currency_id="USD")
    return {"user": user, "workspace": ws, "account": account}


@pytest.mark.django_db
def test_opening_balance_posts_to_equity_not_income(opening_workspace):
    ctx = opening_workspace
    ws = ctx["workspace"]
    account = ctx["account"]

    tx = create_opening_balance(
        workspace=ws,
        actor=ctx["user"],
        account=account,
        amount="500.00",
        as_of=date(2026, 11, 1),
    )

    assert tx.transaction_type == TransactionType.OPENING_BALANCE
    assert tx.amount_minor == 50000

    # Account balance reflects the opening balance
    acc_ledger = get_or_create_account_ledger_account(account=account)
    assert postings_balance(ledger_account_id=acc_ledger.id) == 50000

    # Crucial accounting rule: Neither income nor expense is created!
    assert expense_total(workspace=ws) == 0
    assert income_total(workspace=ws) == 0


@pytest.mark.django_db
def test_duplicate_opening_balance_rejected(opening_workspace):
    ctx = opening_workspace
    ws = ctx["workspace"]
    account = ctx["account"]

    create_opening_balance(
        workspace=ws,
        actor=ctx["user"],
        account=account,
        amount="500.00",
        as_of=date(2026, 11, 1),
    )

    with pytest.raises(DuplicateOpeningBalance):
        create_opening_balance(
            workspace=ws,
            actor=ctx["user"],
            account=account,
            amount="200.00",
            as_of=date(2026, 11, 2),
        )
