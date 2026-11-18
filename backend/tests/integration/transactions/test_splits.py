"""Integration tests for multi-category transaction splitting."""

from __future__ import annotations

from datetime import date

import pytest

from apps.categories.models import Category, CategoryKind
from apps.transactions.models import TransactionSplit, TransactionType
from apps.transactions.services.create import (
    SplitInput,
    SplitTotalMismatch,
    create_transaction,
)
from tests.factories.accounts import AccountFactory
from tests.factories.users import UserFactory


@pytest.fixture
def split_workspace(db):
    user = UserFactory()
    ws = user.workspace
    account = AccountFactory(workspace=ws, currency_id="USD")
    groceries = Category.objects.create(workspace=ws, name="Groceries", kind=CategoryKind.EXPENSE)
    supplies = Category.objects.create(
        workspace=ws, name="Household Supplies", kind=CategoryKind.EXPENSE
    )
    care = Category.objects.create(workspace=ws, name="Personal Care", kind=CategoryKind.EXPENSE)
    return {
        "user": user,
        "workspace": ws,
        "account": account,
        "groceries": groceries,
        "supplies": supplies,
        "care": care,
    }


@pytest.mark.django_db
def test_create_valid_split_transaction(split_workspace):
    ctx = split_workspace
    ws = ctx["workspace"]

    # $100.00 split: Groceries $60, Supplies $25, Care $15
    splits = [
        SplitInput(category_id=ctx["groceries"].id, amount="60.00"),
        SplitInput(category_id=ctx["supplies"].id, amount="25.00"),
        SplitInput(category_id=ctx["care"].id, amount="15.00"),
    ]

    tx = create_transaction(
        workspace=ws,
        actor=ctx["user"],
        kind=TransactionType.EXPENSE,
        account_id=ctx["account"].id,
        amount="100.00",
        currency="USD",
        occurred_on=date(2026, 11, 18),
        title="Supermarket run",
        splits=splits,
    )

    assert tx.is_split is True
    assert tx.category_id is None
    assert TransactionSplit.objects.filter(transaction=tx).count() == 3

    groceries_split = TransactionSplit.objects.get(transaction=tx, category=ctx["groceries"])
    assert groceries_split.amount_minor == 6000


@pytest.mark.django_db
def test_split_total_mismatch_raises_error(split_workspace):
    ctx = split_workspace
    ws = ctx["workspace"]

    # Total $100.00, but splits sum to $99.99 (difference 1 minor unit)
    splits = [
        SplitInput(category_id=ctx["groceries"].id, amount="60.00"),
        SplitInput(category_id=ctx["supplies"].id, amount="39.99"),
    ]

    with pytest.raises(SplitTotalMismatch) as exc_info:
        create_transaction(
            workspace=ws,
            actor=ctx["user"],
            kind=TransactionType.EXPENSE,
            account_id=ctx["account"].id,
            amount="100.00",
            currency="USD",
            occurred_on=date(2026, 11, 18),
            title="Supermarket run",
            splits=splits,
        )

    assert exc_info.value.difference_minor == 1
