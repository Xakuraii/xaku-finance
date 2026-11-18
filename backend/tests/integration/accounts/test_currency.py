"""Tests for account currency modifications and constraints."""

from __future__ import annotations

from datetime import date

import pytest

from apps.accounts.models import AccountType
from apps.accounts.services import (
    CurrencyImmutable,
    change_currency,
    create_account,
)
from tests.factories.users import UserFactory


@pytest.mark.django_db
def test_change_currency_succeeds_before_postings():
    user = UserFactory()
    ws = user.workspace

    account = create_account(
        workspace=ws,
        actor=user,
        name="New Account",
        account_type=AccountType.CHECKING,
        currency="USD",
    )

    updated = change_currency(
        workspace=ws,
        actor=user,
        account_id=account.id,
        currency="KHR",
    )

    assert updated.currency_id == "KHR"


@pytest.mark.django_db
def test_currency_change_blocked_after_posting():
    user = UserFactory()
    ws = user.workspace

    account = create_account(
        workspace=ws,
        actor=user,
        name="Funded Account",
        account_type=AccountType.CHECKING,
        currency="USD",
        opening_balance="100.00",
        opening_balance_date=date(2026, 11, 1),
    )

    with pytest.raises(CurrencyImmutable):
        change_currency(
            workspace=ws,
            actor=user,
            account_id=account.id,
            currency="KHR",
        )
