"""Tests for Analytics models (NetWorthSnapshot and RecurringObligation)."""

from datetime import date

import pytest
from django.db import IntegrityError

from apps.analytics.models import (
    NetWorthSnapshot,
    ObligationCadence,
    ObligationKind,
    RecurringObligation,
)
from apps.identity.services.registration import register_user


@pytest.fixture
def analytics_ws(db):
    user = register_user(
        email="snapshot_test@example.com",
        password="StrongPassword123!",
        display_name="Snapshot User",
    )
    return user.workspace


def test_net_worth_snapshot_creation(analytics_ws):
    snapshot = NetWorthSnapshot.objects.create(
        workspace=analytics_ws,
        as_of_date=date(2026, 11, 15),
        reporting_currency_code="USD",
        assets_minor=100000,
        liabilities_minor=30000,
        net_worth_minor=70000,
        ledger_seq=1,
    )
    assert snapshot.id is not None
    assert snapshot.net_worth_minor == 70000
    assert str(snapshot).startswith("NetWorthSnapshot")


def test_net_worth_snapshot_equality_constraint(analytics_ws):
    with pytest.raises(IntegrityError):
        NetWorthSnapshot.objects.create(
            workspace=analytics_ws,
            as_of_date=date(2026, 11, 16),
            reporting_currency_code="USD",
            assets_minor=100000,
            liabilities_minor=30000,
            net_worth_minor=50000,  # wrong: 100000 - 30000 != 50000
            ledger_seq=1,
        )


def test_net_worth_snapshot_unique_constraint(analytics_ws):
    NetWorthSnapshot.objects.create(
        workspace=analytics_ws,
        as_of_date=date(2026, 11, 15),
        reporting_currency_code="USD",
        assets_minor=100000,
        liabilities_minor=30000,
        net_worth_minor=70000,
        ledger_seq=1,
    )
    with pytest.raises(IntegrityError):
        NetWorthSnapshot.objects.create(
            workspace=analytics_ws,
            as_of_date=date(2026, 11, 15),
            reporting_currency_code="USD",
            assets_minor=120000,
            liabilities_minor=20000,
            net_worth_minor=100000,
            ledger_seq=2,
        )


def test_recurring_obligation_creation(analytics_ws):
    obligation = RecurringObligation.objects.create(
        workspace=analytics_ws,
        name="Rent",
        kind=ObligationKind.BILL,
        amount_minor=120000,
        currency_code="USD",
        cadence=ObligationCadence.MONTHLY,
        next_due_date=date(2026, 12, 1),
        is_reserved=True,
    )
    assert obligation.id is not None
    assert obligation.amount_minor == 120000
    assert str(obligation).startswith("Rent")


def test_recurring_obligation_amount_constraint(analytics_ws):
    with pytest.raises(IntegrityError):
        RecurringObligation.objects.create(
            workspace=analytics_ws,
            name="Free subscription",
            kind=ObligationKind.SUBSCRIPTION,
            amount_minor=0,
            currency_code="USD",
            next_due_date=date(2026, 12, 1),
        )
