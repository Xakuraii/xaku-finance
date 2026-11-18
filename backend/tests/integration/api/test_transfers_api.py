"""Integration tests for the Transfers REST API endpoints."""

from __future__ import annotations

from datetime import date

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import AccountType
from apps.accounts.services import create_account
from apps.categories.models import Category, CategoryKind
from apps.ledger.services.reconciliation import reconcile_workspace
from tests.factories.users import UserFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def transfer_api_setup():
    user = UserFactory()
    ws = user.workspace

    usd_checking = create_account(
        workspace=ws,
        actor=user,
        name="USD Checking",
        account_type=AccountType.CHECKING,
        currency="USD",
        opening_balance="2500.00",
        opening_balance_date=date(2026, 11, 1),
    )
    usd_savings = create_account(
        workspace=ws,
        actor=user,
        name="USD Savings",
        account_type=AccountType.SAVINGS,
        currency="USD",
        opening_balance="1000.00",
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
def test_create_same_currency_transfer_api(api_client, transfer_api_setup):
    s = transfer_api_setup
    api_client.force_authenticate(s["user"])

    payload = {
        "source_account_id": str(s["usd_checking"].id),
        "destination_account_id": str(s["usd_savings"].id),
        "amount": "500.00",
        "transfer_fee": "3.50",
        "transfer_fee_category_id": str(s["fee_cat"].id),
        "occurred_on": "2026-11-17",
        "notes": "Emergency buffer top up",
    }

    res = api_client.post("/api/v1/transfers/", payload, format="json")
    assert res.status_code == 201
    data = res.json()
    assert data["source_account"]["id"] == str(s["usd_checking"].id)
    assert data["destination_account"]["id"] == str(s["usd_savings"].id)
    assert data["amount"] == "500.00"
    assert data["amount_minor"] == 50000
    assert data["destination_amount"] == "500.00"
    assert data["destination_amount_minor"] == 50000
    assert data["transfer_fee"] == "3.50"
    assert data["transfer_fee_minor"] == 350
    assert data["status"] == "completed"

    # Ledger check
    assert reconcile_workspace(workspace=s["workspace"]).is_valid is True


@pytest.mark.django_db
def test_create_cross_currency_transfer_api(api_client, transfer_api_setup):
    s = transfer_api_setup
    api_client.force_authenticate(s["user"])

    payload = {
        "source_account_id": str(s["usd_checking"].id),
        "destination_account_id": str(s["khr_savings"].id),
        "amount": "100.00",
        "destination_amount": "405000.00",
        "rate": "4050.00",
        "reference_rate": "4100.00",
        "conversion_fee_category_id": str(s["fx_fee_cat"].id),
        "occurred_on": "2026-11-17",
        "notes": "FX transfer",
    }

    res = api_client.post("/api/v1/transfers/", payload, format="json")
    assert res.status_code == 201
    data = res.json()
    assert data["amount"] == "100.00"
    assert data["amount_minor"] == 10000
    assert data["currency"] == "USD"
    assert data["destination_amount"] == "405000.00"
    assert data["destination_amount_minor"] == 40500000
    assert data["destination_currency"] == "KHR"
    assert data["conversion_fee_minor"] == 500000
    assert data["conversion"]["spread_amount_minor"] == 500000
    assert data["conversion"]["spread_currency"] == "KHR"

    # Ledger check
    assert reconcile_workspace(workspace=s["workspace"]).is_valid is True


@pytest.mark.django_db
def test_transfer_idempotency_api(api_client, transfer_api_setup):
    s = transfer_api_setup
    api_client.force_authenticate(s["user"])

    payload = {
        "source_account_id": str(s["usd_checking"].id),
        "destination_account_id": str(s["usd_savings"].id),
        "amount": "250.00",
        "occurred_on": "2026-11-17",
    }
    headers = {"HTTP_IDEMPOTENCY_KEY": "transfer-idem-key-123"}

    res1 = api_client.post("/api/v1/transfers/", payload, format="json", **headers)
    assert res1.status_code == 201

    res2 = api_client.post("/api/v1/transfers/", payload, format="json", **headers)
    assert res2.status_code == 201
    assert res1.json()["id"] == res2.json()["id"]

    # Reconcile confirms only one movement posted
    assert reconcile_workspace(workspace=s["workspace"]).is_valid is True


@pytest.mark.django_db
def test_archive_transfer_api(api_client, transfer_api_setup):
    s = transfer_api_setup
    api_client.force_authenticate(s["user"])

    create_res = api_client.post(
        "/api/v1/transfers/",
        {
            "source_account_id": str(s["usd_checking"].id),
            "destination_account_id": str(s["usd_savings"].id),
            "amount": "150.00",
            "occurred_on": "2026-11-17",
        },
        format="json",
    )
    assert create_res.status_code == 201
    transfer_id = create_res.json()["id"]

    archive_res = api_client.post(
        f"/api/v1/transfers/{transfer_id}/archive/",
        {"reason": "User requested reversal"},
        format="json",
    )
    assert archive_res.status_code == 200
    assert archive_res.json()["is_archived"] is True
    assert reconcile_workspace(workspace=s["workspace"]).is_valid is True
