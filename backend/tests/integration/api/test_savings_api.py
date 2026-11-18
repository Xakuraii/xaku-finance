"""Integration tests for the Savings Goals REST API."""

from datetime import date, timedelta

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import AccountType
from apps.accounts.services import create_account
from apps.identity.services.registration import register_user
from apps.transactions.services.opening import create_opening_balance


@pytest.fixture
def savings_api_client(db):
    user = register_user(
        email="savings_api@example.com",
        password="StrongPassword123!",
        display_name="API User",
    )
    ws = user.workspace
    account = create_account(
        workspace=ws,
        actor=user,
        name="Main Savings",
        account_type=AccountType.SAVINGS,
        currency="USD",
    )
    create_opening_balance(
        workspace=ws,
        account=account,
        amount="1500.00",
        as_of=date.today(),
        actor=user,
    )

    client = APIClient()
    client.force_authenticate(user=user)
    return client, user, ws, account


@pytest.mark.django_db
def test_savings_goal_crud_api(savings_api_client):
    client, user, ws, account = savings_api_client

    # 1. Create Goal
    payload = {
        "name": "Japan Trip",
        "target_amount": "3000.00",
        "currency": "USD",
        "target_date": (date.today() + timedelta(days=180)).isoformat(),
        "linked_account_id": str(account.id),
        "strategy": "linked_account",
        "notes": "Cherry blossom season",
    }
    res = client.post("/api/v1/savings-goals/", payload, format="json")
    assert res.status_code == status.HTTP_201_CREATED, res.data
    goal_id = res.data["id"]
    assert res.data["name"] == "Japan Trip"
    assert res.data["target_amount"] == "3000.00"
    assert res.data["target_amount_minor"] == 300000
    assert res.data["status"] == "active"
    assert res.data["unallocated_capacity"] == 150000

    # 2. List Goals
    list_res = client.get("/api/v1/savings-goals/")
    assert list_res.status_code == status.HTTP_200_OK
    assert len(list_res.data) == 1

    # 3. Retrieve Goal
    detail_res = client.get(f"/api/v1/savings-goals/{goal_id}/")
    assert detail_res.status_code == status.HTTP_200_OK
    assert detail_res.data["name"] == "Japan Trip"

    # 4. Partial Update
    patch_res = client.patch(
        f"/api/v1/savings-goals/{goal_id}/",
        {"target_amount": "3500.00"},
        format="json",
    )
    assert patch_res.status_code == status.HTTP_200_OK
    assert patch_res.data["target_amount"] == "3500.00"


@pytest.mark.django_db
def test_savings_contribution_and_capacity_api(savings_api_client):
    client, user, ws, account = savings_api_client

    goal_res = client.post(
        "/api/v1/savings-goals/",
        {
            "name": "Camera",
            "target_amount": "800.00",
            "currency": "USD",
            "linked_account_id": str(account.id),
            "strategy": "linked_account",
        },
        format="json",
    )
    goal_id = goal_res.data["id"]

    # 1. Earmark $500.00
    contrib_res = client.post(
        f"/api/v1/savings-goals/{goal_id}/contributions/",
        {
            "kind": "earmark",
            "amount": "500.00",
            "account_id": str(account.id),
            "note": "Savings bonus",
        },
        format="json",
    )
    assert contrib_res.status_code == status.HTTP_201_CREATED, contrib_res.data
    assert contrib_res.data["amount"] == "500.00"
    assert contrib_res.data["amount_minor"] == 50000

    # Check goal detail progress
    detail_res = client.get(f"/api/v1/savings-goals/{goal_id}/")
    assert detail_res.data["current_amount"] == "500.00"
    assert detail_res.data["current_amount_minor"] == 50000
    assert detail_res.data["progress_percent"] == 62.5
    # Unallocated capacity: 1500 - 500 = 1000
    assert detail_res.data["unallocated_capacity"] == 100000

    # 2. Try to earmark $1,200.00 -> exceeds 1,000 capacity
    fail_res = client.post(
        f"/api/v1/savings-goals/{goal_id}/contributions/",
        {
            "kind": "earmark",
            "amount": "1200.00",
            "account_id": str(account.id),
        },
        format="json",
    )
    assert fail_res.status_code == status.HTTP_400_BAD_REQUEST
    assert "exceeds available unallocated capacity" in str(fail_res.data)

    # 3. List contributions
    contrib_list = client.get(f"/api/v1/savings-goals/{goal_id}/contributions/")
    assert contrib_list.status_code == status.HTTP_200_OK
    assert len(contrib_list.data) == 1


@pytest.mark.django_db
def test_savings_archive_restore_and_projection_api(savings_api_client):
    client, user, ws, account = savings_api_client

    target_date = (date.today() + timedelta(days=90)).isoformat()
    goal_res = client.post(
        "/api/v1/savings-goals/",
        {
            "name": "New TV",
            "target_amount": "600.00",
            "currency": "USD",
            "target_date": target_date,
            "linked_account_id": str(account.id),
        },
        format="json",
    )
    goal_id = goal_res.data["id"]

    # Earmark 300.00
    client.post(
        f"/api/v1/savings-goals/{goal_id}/contributions/",
        {
            "kind": "earmark",
            "amount": "300.00",
            "account_id": str(account.id),
        },
        format="json",
    )

    # Projection endpoint
    proj_res = client.get(f"/api/v1/savings-goals/{goal_id}/projection/")
    assert proj_res.status_code == status.HTTP_200_OK
    assert proj_res.data["remaining_amount_minor"] == 30000
    assert proj_res.data["days_remaining"] is not None

    # Archive endpoint
    arch_res = client.post(f"/api/v1/savings-goals/{goal_id}/archive/")
    assert arch_res.status_code == status.HTTP_200_OK
    assert arch_res.data["is_archived"] is True
    assert arch_res.data["status"] == "archived"

    # Default list excludes archived
    active_list = client.get("/api/v1/savings-goals/")
    assert len(active_list.data) == 0

    # Include archived
    all_list = client.get("/api/v1/savings-goals/?include_archived=true")
    assert len(all_list.data) == 1

    # Restore endpoint
    rest_res = client.post(f"/api/v1/savings-goals/{goal_id}/restore/")
    assert rest_res.status_code == status.HTTP_200_OK
    assert rest_res.data["is_archived"] is False
    assert rest_res.data["status"] == "active"
