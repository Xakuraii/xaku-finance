"""API integration tests for Net Worth endpoints."""

from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import AccountType
from apps.accounts.services import create_account
from apps.debts.services import create_liability
from apps.identity.services.registration import register_user
from apps.ledger.models import ExchangeRate, ExchangeRateSource
from apps.transactions.services.opening import create_opening_balance


@pytest.fixture
def api_net_worth_setup(db):
    user = register_user(
        email="nw_api@example.com",
        password="StrongPassword123!",
        display_name="NW API User",
    )
    ws = user.workspace

    checking = create_account(
        workspace=ws,
        actor=user,
        name="Checking Account",
        account_type=AccountType.CHECKING,
        currency="USD",
    )
    create_opening_balance(
        workspace=ws,
        account=checking,
        amount="5000.00",
        as_of=date(2026, 11, 1),
        actor=user,
    )

    liability = create_liability(
        workspace=ws,
        actor=user,
        name="Auto Loan",
        currency="USD",
        original_principal="2000.00",
        disbursement_date=date(2026, 11, 2),
        initial_disbursement_account_id=str(checking.id),
    )

    client = APIClient()
    client.force_authenticate(user=user)

    return {
        "user": user,
        "workspace": ws,
        "checking": checking,
        "liability": liability,
        "client": client,
    }


def test_get_net_worth_endpoint(api_net_worth_setup):
    client = api_net_worth_setup["client"]

    # Checking has 5000 opening + 2000 loan disbursement = 7000.
    # Liability = 2000.
    # Net worth = 5000.
    res = client.get("/api/v1/net-worth/")
    assert res.status_code == 200
    data = res.json()

    assert data["currency"] == "USD"
    assert data["assets"] == "7000.00"
    assert data["liabilities"] == "2000.00"
    assert data["net_worth"] == "5000.00"
    assert data["rate_policy"] == "period_end"
    assert "breakdown" in data
    assert len(data["breakdown"]["assets"]) >= 1
    assert len(data["breakdown"]["liabilities"]) >= 1


def test_get_net_worth_as_of_endpoint(api_net_worth_setup):
    client = api_net_worth_setup["client"]

    # As of Nov 1 (before loan disbursement):
    # Checking = 5000, Liability = 0, Net worth = 5000
    res = client.get("/api/v1/net-worth/?as_of=2026-11-01")
    assert res.status_code == 200
    data = res.json()

    assert data["assets"] == "5000.00"
    assert data["liabilities"] == "0.00"
    assert data["net_worth"] == "5000.00"


def test_get_net_worth_history_endpoint(api_net_worth_setup):
    client = api_net_worth_setup["client"]

    res = client.get("/api/v1/net-worth/history/?from=2026-10-01&to=2026-11-15&granularity=month")
    assert res.status_code == 200
    data = res.json()

    assert data["currency"] == "USD"
    assert data["granularity"] == "month"
    assert len(data["series"]) >= 2
    assert len(data["table"]) >= 2


def test_net_worth_history_invalid_range(api_net_worth_setup):
    client = api_net_worth_setup["client"]

    res = client.get("/api/v1/net-worth/history/?from=2026-12-01&to=2026-11-15")
    assert res.status_code == 400


def test_net_worth_unauthenticated():
    client = APIClient()
    res = client.get("/api/v1/net-worth/")
    assert res.status_code == 401
