"""Integration tests for Debts & Liabilities REST API."""

from datetime import date

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import AccountType
from apps.accounts.services import create_account
from apps.identity.services.registration import register_user
from apps.transactions.services.opening import create_opening_balance


@pytest.fixture
def debt_api_client(db):
    user = register_user(
        email="debt_api@example.com",
        password="StrongPassword123!",
        display_name="Debt API User",
    )
    ws = user.workspace
    checking = create_account(
        workspace=ws,
        actor=user,
        name="Main Checking",
        account_type=AccountType.CHECKING,
        currency="USD",
    )
    create_opening_balance(
        workspace=ws,
        account=checking,
        amount="5000.00",
        as_of=date.today(),
        actor=user,
    )

    client = APIClient()
    client.force_authenticate(user=user)
    return client, user, ws, checking


@pytest.mark.django_db
def test_liability_crud_and_disbursement_api(debt_api_client):
    client, user, ws, checking = debt_api_client

    # 1. Create liability with initial disbursement
    payload = {
        "name": "Auto Loan",
        "original_principal": "3000.00",
        "currency": "USD",
        "liability_type": "personal_loan",
        "interest_rate": "4.5000",
        "interest_type": "simple",
        "lender": "Chase Auto",
        "initial_disbursement_account_id": str(checking.id),
        "notes": "New commuter vehicle",
    }
    res = client.post("/api/v1/debts/", payload, format="json")
    assert res.status_code == status.HTTP_201_CREATED, res.data
    debt_id = res.data["id"]
    assert res.data["name"] == "Auto Loan"
    assert res.data["original_principal"] == "3000.00"
    assert res.data["outstanding_principal"] == "3000.00"
    assert res.data["outstanding_principal_minor"] == 300000
    assert res.data["status"] == "active"

    # 2. List liabilities
    list_res = client.get("/api/v1/debts/")
    assert list_res.status_code == status.HTTP_200_OK
    assert len(list_res.data) == 1

    # 3. Retrieve detail
    detail_res = client.get(f"/api/v1/debts/{debt_id}/")
    assert detail_res.status_code == status.HTTP_200_OK
    assert detail_res.data["lender"] == "Chase Auto"

    # 4. Partial update
    patch_res = client.patch(
        f"/api/v1/debts/{debt_id}/",
        {"lender": "JPMorgan Chase"},
        format="json",
    )
    assert patch_res.status_code == status.HTTP_200_OK
    assert patch_res.data["lender"] == "JPMorgan Chase"


@pytest.mark.django_db
def test_debt_repayment_and_overpayment_api(debt_api_client):
    client, user, ws, checking = debt_api_client

    debt_res = client.post(
        "/api/v1/debts/",
        {
            "name": "Medical Bill",
            "original_principal": "1000.00",
            "currency": "USD",
        },
        format="json",
    )
    debt_id = debt_res.data["id"]

    # 1. Overpayment rejection: repay $1500 on $1000 loan
    overpay_res = client.post(
        f"/api/v1/debts/{debt_id}/repayments/",
        {
            "paying_account_id": str(checking.id),
            "principal_amount": "1500.00",
        },
        format="json",
    )
    assert overpay_res.status_code == status.HTTP_400_BAD_REQUEST
    assert "exceeds remaining outstanding principal" in str(overpay_res.data)

    # 2. Valid split repayment: $400 principal + $20 interest + $5 fee = $425
    repay_res = client.post(
        f"/api/v1/debts/{debt_id}/repayments/",
        {
            "paying_account_id": str(checking.id),
            "principal_amount": "400.00",
            "interest_amount": "20.00",
            "fee_amount": "5.00",
            "note": "Payment #1",
        },
        format="json",
    )
    assert repay_res.status_code == status.HTTP_201_CREATED, repay_res.data
    assert repay_res.data["principal_amount"] == "400.00"
    assert repay_res.data["total_amount"] == "425.00"

    # Verify updated debt progress
    detail_res = client.get(f"/api/v1/debts/{debt_id}/")
    assert detail_res.data["outstanding_principal"] == "600.00"
    assert detail_res.data["paid_principal"] == "400.00"
    assert detail_res.data["progress_percent"] == 40.0

    # 3. List repayments
    repay_list = client.get(f"/api/v1/debts/{debt_id}/repayments/")
    assert repay_list.status_code == status.HTTP_200_OK
    assert len(repay_list.data) == 1


@pytest.mark.django_db
def test_debt_accrued_interest_and_projection_api(debt_api_client):
    client, user, ws, checking = debt_api_client

    debt_res = client.post(
        "/api/v1/debts/",
        {
            "name": "Store Credit",
            "original_principal": "500.00",
            "currency": "USD",
            "interest_rate": "18.0000",
        },
        format="json",
    )
    debt_id = debt_res.data["id"]

    # 1. Accrue interest
    accrue_res = client.post(
        f"/api/v1/debts/{debt_id}/interest/",
        {
            "amount": "12.50",
            "period_start": "2026-01-01",
            "period_end": "2026-01-31",
            "note": "January interest",
        },
        format="json",
    )
    assert accrue_res.status_code == status.HTTP_201_CREATED, accrue_res.data
    assert accrue_res.data["amount"] == "12.50"

    # Verify interest record list
    int_list = client.get(f"/api/v1/debts/{debt_id}/interest/")
    assert len(int_list.data) == 1

    # Outstanding is now 512.50
    detail_res = client.get(f"/api/v1/debts/{debt_id}/")
    assert detail_res.data["outstanding_principal"] == "512.50"

    # 2. Payoff projection
    proj_res = client.get(f"/api/v1/debts/{debt_id}/projection/?monthly_payment=100.00")
    assert proj_res.status_code == status.HTTP_200_OK
    assert proj_res.data["estimated_months_to_payoff"] is not None
    assert proj_res.data["projected_payoff_date"] is not None

    # 3. Archive and restore
    arch_res = client.post(f"/api/v1/debts/{debt_id}/archive/")
    assert arch_res.status_code == status.HTTP_200_OK
    assert arch_res.data["is_archived"] is True

    rest_res = client.post(f"/api/v1/debts/{debt_id}/restore/")
    assert rest_res.status_code == status.HTTP_200_OK
    assert rest_res.data["is_archived"] is False
