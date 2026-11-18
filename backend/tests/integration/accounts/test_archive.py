"""Tests for account archiving and restoration."""

from __future__ import annotations

from datetime import date

import pytest

from apps.accounts.models import AccountType
from apps.accounts.selectors import account_balance
from apps.accounts.services import (
    AccountHasBalance,
    archive_account,
    create_account,
    restore_account,
)
from apps.transactions.services.create import create_transaction
from tests.factories.users import UserFactory


@pytest.mark.django_db
def test_archive_empty_account_succeeds():
    user = UserFactory()
    ws = user.workspace

    account = create_account(
        workspace=ws,
        actor=user,
        name="Old Wallet",
        account_type=AccountType.CASH,
        currency="USD",
    )

    archived = archive_account(
        workspace=ws,
        actor=user,
        account_id=account.id,
        reason="No longer used",
    )

    assert archived.is_archived is True
    assert archived.archived_at is not None
    assert archived.archive_reason == "No longer used"


@pytest.mark.django_db
def test_archive_requires_acknowledgement_when_balance_nonzero():
    user = UserFactory()
    ws = user.workspace

    account = create_account(
        workspace=ws,
        actor=user,
        name="Active Checking",
        account_type=AccountType.CHECKING,
        currency="USD",
        opening_balance="500.00",
        opening_balance_date=date(2026, 11, 1),
    )

    assert account_balance(account=account).amount_minor == 50000

    # Without acknowledgement: must fail
    with pytest.raises(AccountHasBalance):
        archive_account(
            workspace=ws,
            actor=user,
            account_id=account.id,
            reason="Closing account",
            acknowledge_balance=False,
        )

    # With acknowledgement: succeeds
    archived = archive_account(
        workspace=ws,
        actor=user,
        account_id=account.id,
        reason="Closing account",
        acknowledge_balance=True,
    )
    assert archived.is_archived is True
    assert archived.archive_reason == "Closing account"


@pytest.mark.django_db
def test_restore_account_succeeds():
    user = UserFactory()
    ws = user.workspace

    account = create_account(
        workspace=ws,
        actor=user,
        name="Archived Cash",
        account_type=AccountType.CASH,
        currency="USD",
    )
    archive_account(
        workspace=ws,
        actor=user,
        account_id=account.id,
        reason="Temp dormant",
    )

    restored = restore_account(
        workspace=ws,
        actor=user,
        account_id=account.id,
    )
    assert restored.is_archived is False
    assert restored.archived_at is None
    assert restored.archive_reason is None


@pytest.mark.django_db
def test_archived_account_cannot_create_transaction():
    user = UserFactory()
    ws = user.workspace

    account = create_account(
        workspace=ws,
        actor=user,
        name="Archived Account",
        account_type=AccountType.CHECKING,
        currency="USD",
    )
    archive_account(
        workspace=ws,
        actor=user,
        account_id=account.id,
        reason="Dormant",
    )

    with pytest.raises(ValueError, match="Cannot record transaction on archived account"):
        create_transaction(
            workspace=ws,
            actor=user,
            kind="expense",
            account_id=account.id,
            amount="10.00",
            currency="USD",
            occurred_on=date.today(),
            title="Lunch",
        )
