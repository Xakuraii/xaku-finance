"""Integration tests for internal account transfers and foreign exchange clearing."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from apps.accounts.models import AccountType
from apps.accounts.selectors import account_balance
from apps.accounts.services import archive_account, create_account
from apps.categories.models import Category, CategoryKind
from apps.ledger.services.reconciliation import reconcile_workspace
from apps.transactions.services.transfer import (
    ArchivedAccountTransferError,
    SameAccountTransferError,
    archive_transfer,
    create_transfer,
)
from tests.factories.users import UserFactory


@pytest.fixture
def workspace_setup():
    user = UserFactory()
    ws = user.workspace

    usd_checking = create_account(
        workspace=ws,
        actor=user,
        name="USD Checking",
        account_type=AccountType.CHECKING,
        currency="USD",
        opening_balance="1000.00",
        opening_balance_date=date(2026, 11, 1),
    )
    usd_savings = create_account(
        workspace=ws,
        actor=user,
        name="USD Savings",
        account_type=AccountType.SAVINGS,
        currency="USD",
        opening_balance="500.00",
        opening_balance_date=date(2026, 11, 1),
    )
    khr_savings = create_account(
        workspace=ws,
        actor=user,
        name="KHR Savings",
        account_type=AccountType.SAVINGS,
        currency="KHR",
    )

    fee_cat = Category.objects.create(
        workspace=ws,
        name="Bank Fees",
        kind=CategoryKind.EXPENSE,
    )
    fx_fee_cat = Category.objects.create(
        workspace=ws,
        name="FX Conversion Fees",
        kind=CategoryKind.EXPENSE,
    )

    return {
        "user": user,
        "workspace": ws,
        "usd_checking": usd_checking,
        "usd_savings": usd_savings,
        "khr_savings": khr_savings,
        "fee_cat": fee_cat,
        "fx_fee_cat": fx_fee_cat,
    }


@pytest.mark.django_db
def test_same_currency_transfer_success(workspace_setup):
    s = workspace_setup
    ws = s["workspace"]
    user = s["user"]

    tx, transfer = create_transfer(
        workspace=ws,
        actor=user,
        source_account_id=s["usd_checking"].id,
        destination_account_id=s["usd_savings"].id,
        amount="200.00",
        occurred_on=date(2026, 11, 17),
        notes="Monthly savings allocation",
        transfer_fee="2.00",
        transfer_fee_category_id=s["fee_cat"].id,
    )

    assert tx.transaction_type == "transfer"
    assert tx.status == "completed"
    assert transfer.source_amount_minor == 20000
    assert transfer.destination_amount_minor == 20000
    assert transfer.transfer_fee_minor == 200
    assert transfer.rate == Decimal("1.0000000000")

    # Balances:
    # Checking started at 1000.00, deducted 200.00 principal + 2.00 fee -> 798.00 (79800 minor)
    bal_checking = account_balance(account=s["usd_checking"])
    assert bal_checking.amount_minor == 79800

    # Savings started at 500.00, received 200.00 principal -> 700.00 (70000 minor)
    bal_savings = account_balance(account=s["usd_savings"])
    assert bal_savings.amount_minor == 70000

    # Ledger integrity must be 100% clean
    assert reconcile_workspace(workspace=ws).is_valid is True


@pytest.mark.django_db
def test_cross_currency_transfer_with_spread(workspace_setup):
    s = workspace_setup
    ws = s["workspace"]
    user = s["user"]

    # Send 100.00 USD -> receive 405,000.00 KHR (rate 4050.0)
    # Market reference rate 4100.0 -> spread 5000.00 KHR (500,000 minor units)
    tx, transfer = create_transfer(
        workspace=ws,
        actor=user,
        source_account_id=s["usd_checking"].id,
        destination_account_id=s["khr_savings"].id,
        amount="100.00",
        destination_amount="405000.00",
        rate=Decimal("4050.0000000000"),
        reference_rate=Decimal("4100.0000000000"),
        conversion_fee_category_id=s["fx_fee_cat"].id,
        occurred_on=date(2026, 11, 17),
        notes="Cambodia trip allowance",
    )

    assert tx.transaction_type == "transfer"
    assert transfer.source_amount_minor == 10000
    assert transfer.destination_amount_minor == 40500000
    # Expected conversion fee: (100 * 4100 - 405,000) = 5,000 KHR = 500,000 minor units
    assert transfer.conversion_fee_minor == 500000

    # USD Checking decreased by $100.00 -> 900.00 (90000 minor)
    bal_checking = account_balance(account=s["usd_checking"])
    assert bal_checking.amount_minor == 90000

    # KHR Savings increased by 405,000.00 KHR -> 40,500,000 minor
    bal_khr = account_balance(account=s["khr_savings"])
    assert bal_khr.amount_minor == 40500000

    # Workspace ledger must balance completely per currency
    assert reconcile_workspace(workspace=ws).is_valid is True


@pytest.mark.django_db
def test_transfer_same_account_rejected(workspace_setup):
    s = workspace_setup
    with pytest.raises(SameAccountTransferError):
        create_transfer(
            workspace=s["workspace"],
            actor=s["user"],
            source_account_id=s["usd_checking"].id,
            destination_account_id=s["usd_checking"].id,
            amount="50.00",
            occurred_on=date(2026, 11, 17),
        )


@pytest.mark.django_db
def test_transfer_archived_account_rejected(workspace_setup):
    s = workspace_setup
    # Archive the savings account
    archive_account(
        workspace=s["workspace"],
        account_id=s["usd_savings"].id,
        actor=s["user"],
        reason="Account closed",
        acknowledge_balance=True,
    )

    with pytest.raises(ArchivedAccountTransferError):
        create_transfer(
            workspace=s["workspace"],
            actor=s["user"],
            source_account_id=s["usd_checking"].id,
            destination_account_id=s["usd_savings"].id,
            amount="50.00",
            occurred_on=date(2026, 11, 17),
        )


@pytest.mark.django_db
def test_archive_transfer_reverses_ledger(workspace_setup):
    s = workspace_setup
    ws = s["workspace"]
    user = s["user"]

    tx, transfer = create_transfer(
        workspace=ws,
        actor=user,
        source_account_id=s["usd_checking"].id,
        destination_account_id=s["usd_savings"].id,
        amount="300.00",
        occurred_on=date(2026, 11, 17),
        notes="Will be cancelled",
    )

    assert account_balance(account=s["usd_checking"]).amount_minor == 70000
    assert account_balance(account=s["usd_savings"]).amount_minor == 80000

    # Archive the transfer
    archive_transfer(
        transfer_id=tx.id,
        actor=user,
        reason="Mistaken transfer",
    )

    # Balances restored to initial 1000.00 and 500.00
    assert account_balance(account=s["usd_checking"]).amount_minor == 100000
    assert account_balance(account=s["usd_savings"]).amount_minor == 50000
    assert reconcile_workspace(workspace=ws).is_valid is True
