"""Integration tests for Net Worth calculation, FX conversion, and snapshot caching."""

from datetime import date
from decimal import Decimal

import pytest

from apps.accounts.models import AccountType
from apps.accounts.services import create_account
from apps.analytics.models import NetWorthSnapshot
from apps.analytics.net_worth import (
    calculate_net_worth,
    get_net_worth_history,
    get_or_create_snapshot,
)
from apps.categories.models import Category, CategoryKind
from apps.debts.services import create_liability
from apps.identity.services.registration import register_user
from apps.ledger.models import ExchangeRate, ExchangeRateSource
from apps.transactions.services.create import create_transaction
from apps.transactions.services.opening import create_opening_balance


@pytest.fixture
def net_worth_setup(db):
    user = register_user(
        email="networth_test@example.com",
        password="StrongPassword123!",
        display_name="Net Worth User",
    )
    ws = user.workspace

    checking = create_account(
        workspace=ws,
        actor=user,
        name="Main Checking",
        account_type=AccountType.CHECKING,
        currency="USD",
    )
    savings = create_account(
        workspace=ws,
        actor=user,
        name="High Yield Savings",
        account_type=AccountType.SAVINGS,
        currency="USD",
    )

    # Day 1: 2026-11-01
    d1 = date(2026, 11, 1)
    create_opening_balance(
        workspace=ws,
        account=checking,
        amount="3000.00",
        as_of=d1,
        actor=user,
    )
    create_opening_balance(
        workspace=ws,
        account=savings,
        amount="2000.00",
        as_of=d1,
        actor=user,
    )

    # Debt: $1,000 liability created on 2026-11-05
    d2 = date(2026, 11, 5)
    liability = create_liability(
        workspace=ws,
        actor=user,
        name="Personal Loan",
        currency="USD",
        original_principal="1000.00",
        disbursement_date=d2,
        initial_disbursement_account_id=str(checking.id),
    )

    return {
        "user": user,
        "workspace": ws,
        "checking": checking,
        "savings": savings,
        "liability": liability,
    }


def test_standard_net_worth_calculation(net_worth_setup):
    ws = net_worth_setup["workspace"]
    # Checking started at 3000, got 1000 loan disbursement = 4000.
    # Savings = 2000.
    # Total assets = 6000.
    # Total liabilities = 1000.
    # Net worth = 5000.
    nw = calculate_net_worth(ws, as_of=date(2026, 11, 10))

    assert nw.assets == "6000.00"
    assert nw.liabilities == "1000.00"
    assert nw.net_worth == "5000.00"
    assert nw.computed_from == "ledger"
    assert len(nw.breakdown["assets"]) >= 2
    assert len(nw.breakdown["liabilities"]) >= 1


def test_as_of_historical_net_worth(net_worth_setup):
    ws = net_worth_setup["workspace"]

    # Before debt was disbursed (as of 2026-11-02):
    # Assets: checking 3000 + savings 2000 = 5000
    # Liabilities: 0
    # Net worth = 5000
    nw_past = calculate_net_worth(ws, as_of=date(2026, 11, 2))
    assert nw_past.assets == "5000.00"
    assert nw_past.liabilities == "0.00"
    assert nw_past.net_worth == "5000.00"

    # After debt disbursement (as of 2026-11-06):
    # Checking received 1000 (disbursement) -> 4000
    # Savings 2000 -> Total assets 6000
    # Liability -> 1000
    # Net worth = 5000 (debt disbursement does not change net worth!)
    nw_after = calculate_net_worth(ws, as_of=date(2026, 11, 6))
    assert nw_after.assets == "6000.00"
    assert nw_after.liabilities == "1000.00"
    assert nw_after.net_worth == "5000.00"


def test_multi_currency_net_worth_conversion(net_worth_setup):
    ws = net_worth_setup["workspace"]
    user = net_worth_setup["user"]

    # Create KHR account
    khr_acc = create_account(
        workspace=ws,
        actor=user,
        name="Cambodia Bank",
        account_type=AccountType.CHECKING,
        currency="KHR",
    )
    create_opening_balance(
        workspace=ws,
        account=khr_acc,
        amount="4100000",
        as_of=date(2026, 11, 1),
        actor=user,
    )

    # Without exchange rate: conversion unavailable
    nw_no_rate = calculate_net_worth(ws, as_of=date(2026, 11, 10))
    assert nw_no_rate.conversion_unavailable is True

    # Add exchange rate: 1 USD = 4100 KHR -> KHR to USD rate = 1 / 4100
    ExchangeRate.objects.create(
        workspace=ws,
        base_currency_id="USD",
        quote_currency_id="KHR",
        rate=Decimal("4100.0000000000"),
        effective_date=date(2026, 11, 1),
        source=ExchangeRateSource.MANUAL,
        set_by=user,
    )

    nw_with_rate = calculate_net_worth(ws, as_of=date(2026, 11, 10))
    assert nw_with_rate.conversion_unavailable is False
    # 4,100,000 KHR at 4100 = 1000.00 USD
    # Previous assets: 6000.00 USD + 1000.00 USD = 7000.00 USD
    assert nw_with_rate.assets == "7000.00"
    assert nw_with_rate.net_worth == "6000.00"


def test_snapshot_caching_and_stale_invalidation(net_worth_setup):
    ws = net_worth_setup["workspace"]
    user = net_worth_setup["user"]
    checking = net_worth_setup["checking"]

    # 1. Fresh computation creates snapshot
    calc1 = get_or_create_snapshot(ws, as_of=date(2026, 11, 10))
    assert calc1.computed_from == "ledger"
    snapshot = NetWorthSnapshot.objects.get(workspace=ws, as_of_date=date(2026, 11, 10))
    assert snapshot.ledger_seq == ws.ledger_seq

    # 2. Second read uses snapshot cache
    calc2 = get_or_create_snapshot(ws, as_of=date(2026, 11, 10))
    assert calc2.computed_from == "snapshot"
    assert calc2.net_worth == calc1.net_worth

    # 3. Post a new expense on 2026-11-08 to bump ledger sequence
    cat = Category.objects.create(
        workspace=ws,
        name="Groceries",
        kind=CategoryKind.EXPENSE,
    )
    create_transaction(
        workspace=ws,
        actor=user,
        kind="expense",
        account_id=checking.id,
        category_id=cat.id,
        amount="50.00",
        currency="USD",
        occurred_on=date(2026, 11, 8),
        title="Weekly groceries",
    )
    ws.refresh_from_db()
    assert ws.ledger_seq > snapshot.ledger_seq

    # 4. Snapshot query detects stale sequence and recomputes
    calc3 = get_or_create_snapshot(ws, as_of=date(2026, 11, 10))
    assert calc3.computed_from == "ledger"
    # Net worth dropped by 50.00 USD
    assert calc3.net_worth == "4950.00"


def test_get_net_worth_history(net_worth_setup):
    ws = net_worth_setup["workspace"]
    history = get_net_worth_history(
        ws,
        from_date=date(2026, 9, 1),
        to_date=date(2026, 11, 15),
        granularity="month",
    )

    assert history["currency"] == "USD"
    assert len(history["series"]) >= 2
    assert len(history["table"]) == len(history["series"])
    # Last point has net worth
    assert history["series"][-1]["net_worth"] == "5000.00"
