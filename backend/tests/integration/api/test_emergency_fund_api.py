"""Integration tests for Emergency Fund REST API."""

from datetime import date

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import AccountType
from apps.accounts.services import create_account
from apps.identity.services.registration import register_user
from apps.transactions.services.opening import create_opening_balance


@pytest.fixture
def emergency_api_client(db):
    user = register_user(
        email="emergency_api@example.com",
        password="StrongPassword123!",
        display_name="Emergency API User",
    )
    ws = user.workspace
    savings = create_account(
        workspace=ws,
        actor=user,
        name="Emergency Stash",
        account_type=AccountType.SAVINGS,
        currency="USD",
    )
    create_opening_balance(
        workspace=ws,
        account=savings,
        amount="1200.00",
        as_of=date.today(),
        actor=user,
    )

    client = APIClient()
    client.force_authenticate(user=user)
    return client, user, ws, savings


@pytest.mark.django_db
def test_get_emergency_fund_status(emergency_api_client):
    client, user, ws, savings = emergency_api_client

    response = client.get("/api/v1/emergency-fund/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["target_months"] == 6
    assert data["is_override"] is False
    assert "target_amount" in data
    assert "progress_percent" in data
    assert "has_earmark_conflict" in data
    assert data["has_earmark_conflict"] is False


@pytest.mark.django_db
def test_update_emergency_fund_config(emergency_api_client):
    client, user, ws, savings = emergency_api_client

    payload = {
        "target_months": 3,
        "designated_account_id": str(savings.id),
        "monthly_expense_override": "400.00",
    }
    response = client.patch("/api/v1/emergency-fund/", payload, format="json")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["target_months"] == 3
    assert data["designated_account_id"] == str(savings.id)
    assert data["is_override"] is True
    assert data["monthly_essential_expense"] == "400.00"
    # Target = 3 * 400.00 = 1200.00
    assert data["target_amount"] == "1200.00"
    assert data["target_amount_minor"] == 120000
    # Current savings = 1200.00 from account opening balance
    assert data["current_savings"] == "1200.00"
    assert data["remaining_target"] == "0.00"
    assert data["progress_percent"] == 100.0


@pytest.mark.django_db
def test_emergency_fund_projection_api(emergency_api_client):
    client, user, ws, savings = emergency_api_client

    # Set target higher than current savings ($2,400 target vs $1,200 savings -> $1,200 remaining)
    client.patch(
        "/api/v1/emergency-fund/",
        {
            "target_months": 6,
            "designated_account_id": str(savings.id),
            "monthly_expense_override": "400.00",
        },
        format="json",
    )

    proj_payload = {"monthly_contribution": "300.00"}
    response = client.post("/api/v1/emergency-fund/projection/", proj_payload, format="json")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["target_amount_minor"] == 240000
    assert data["current_savings_minor"] == 120000
    assert data["remaining_target_minor"] == 120000
    assert data["monthly_contribution_minor"] == 30000
    # $1,200 / $300 = 4.0 months
    assert data["months_to_target"] == 4.0
    assert data["projected_completion_date"] is not None
