"""Tests for account creation and opening balance integration."""

from __future__ import annotations

from datetime import date

import pytest

from apps.accounts.models import AccountNature, AccountType
from apps.accounts.selectors import account_balance
from apps.accounts.services import create_account
from apps.transactions.selectors import expense_total, income_total
from tests.factories.users import UserFactory


@pytest.mark.django_db
def test_create_account_defaults():
    user = UserFactory()
    ws = user.workspace

    account = create_account(
        workspace=ws,
        actor=user,
        name="Main Checking",
        account_type=AccountType.CHECKING,
        currency="USD",
    )

    assert account.name == "Main Checking"
    assert account.currency_id == "USD"
    assert account.nature == AccountNature.ASSET
    assert account.is_spendable is True
    assert account.is_archived is False
    assert account_balance(account=account).amount_minor == 0


@pytest.mark.django_db
def test_create_savings_forced_not_spendable():
    user = UserFactory()
    ws = user.workspace

    account = create_account(
        workspace=ws,
        actor=user,
        name="Emergency Savings",
        account_type=AccountType.SAVINGS,
        currency="USD",
        is_spendable=True,  # should be overridden or raise, but savings cannot be spendable
    )

    assert account.account_type == AccountType.SAVINGS
    assert account.is_spendable is False


@pytest.mark.django_db
def test_opening_balance_is_not_income():
    user = UserFactory()
    ws = user.workspace

    account = create_account(
        workspace=ws,
        actor=user,
        name="Bank of America Checking",
        account_type=AccountType.CHECKING,
        currency="USD",
        opening_balance="2000.00",
        opening_balance_date=date(2026, 11, 1),
    )

    bal = account_balance(account=account)
    assert bal.amount_minor == 200000
    assert bal.currency == "USD"

    # Crucial accounting rule: opening balance is never income or expense
    assert income_total(ws) == 0
    assert expense_total(ws) == 0
