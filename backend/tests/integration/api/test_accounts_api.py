"""Integration tests for Accounts API endpoints."""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from tests.factories.accounts import AccountFactory
from tests.factories.users import UserFactory


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def auth_user():
    user = UserFactory()
    return user


@pytest.mark.django_db
def test_list_accounts_empty(api, auth_user):
    api.force_authenticate(auth_user)
    response = api.get("/api/v1/accounts/")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.django_db
def test_create_account_with_opening_balance(api, auth_user):
    api.force_authenticate(auth_user)
    payload = {
        "name": "KBank Checking",
        "account_type": "checking",
        "currency": "USD",
        "opening_balance": "2000.00",
        "opening_balance_date": "2026-11-01",
        "is_spendable": True,
        "description": "Main checking account",
    }
    response = api.post("/api/v1/accounts/", payload, format="json")
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "KBank Checking"
    assert data["currency"] == "USD"
    assert data["balance_minor"] == 200000
    assert data["balance"] == "2000.00"
    assert data["is_spendable"] is True
    assert data["is_archived"] is False


@pytest.mark.django_db
def test_archive_account_with_balance_requires_acknowledgement(api, auth_user):
    api.force_authenticate(auth_user)
    account = AccountFactory(workspace=auth_user.workspace, currency_id="USD")
    # Record opening balance
    api.post(
        f"/api/v1/accounts/{account.id}/opening-balance/",
        {"amount": "500.00", "as_of": "2026-11-01"},
        format="json",
    )

    # Attempt archive without acknowledge
    fail_res = api.post(
        f"/api/v1/accounts/{account.id}/archive/",
        {"reason": "Closing account", "acknowledge_balance": False},
        format="json",
    )
    assert fail_res.status_code == 422
    assert fail_res.json()["error"]["code"] == "account_balance_not_zero"

    # With acknowledge
    success_res = api.post(
        f"/api/v1/accounts/{account.id}/archive/",
        {"reason": "Closing account", "acknowledge_balance": True},
        format="json",
    )
    assert success_res.status_code == 200
    assert success_res.json()["is_archived"] is True
    assert success_res.json()["archive_reason"] == "Closing account"


@pytest.mark.django_db
def test_restore_archived_account(api, auth_user):
    api.force_authenticate(auth_user)
    account = AccountFactory(
        workspace=auth_user.workspace,
        is_archived=True,
        archive_reason="Old",
    )

    response = api.post(f"/api/v1/accounts/{account.id}/restore/")
    assert response.status_code == 200
    assert response.json()["is_archived"] is False


@pytest.mark.django_db
def test_account_isolation_between_workspaces(api, auth_user):
    other_user = UserFactory()
    other_account = AccountFactory(workspace=other_user.workspace)

    api.force_authenticate(auth_user)
    # Detail of another user's account must return 404
    response = api.get(f"/api/v1/accounts/{other_account.id}/")
    assert response.status_code == 404
