"""Integration tests for Transactions API endpoints."""

from __future__ import annotations

from datetime import date

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import AccountType
from apps.accounts.services import create_account
from apps.categories.models import Category, CategoryKind
from tests.factories.users import UserFactory


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def auth_user():
    return UserFactory()


@pytest.fixture
def account(auth_user):
    return create_account(
        workspace=auth_user.workspace,
        actor=auth_user,
        name="Main Checking",
        account_type=AccountType.CHECKING,
        currency="USD",
        opening_balance="1000.00",
        opening_balance_date=date(2026, 11, 1),
    )


@pytest.fixture
def categories(auth_user):
    groceries = Category.objects.create(
        workspace=auth_user.workspace,
        name="Groceries",
        kind=CategoryKind.EXPENSE,
    )
    household = Category.objects.create(
        workspace=auth_user.workspace,
        name="Household",
        kind=CategoryKind.EXPENSE,
    )
    salary = Category.objects.create(
        workspace=auth_user.workspace,
        name="Salary",
        kind=CategoryKind.INCOME,
    )
    return {
        "groceries": groceries,
        "household": household,
        "salary": salary,
    }


@pytest.mark.django_db
def test_create_expense_with_splits(api, auth_user, account, categories):
    api.force_authenticate(auth_user)
    response = api.post(
        "/api/v1/transactions/",
        {
            "type": "expense",
            "account_id": str(account.id),
            "amount": "100.00",
            "currency": "USD",
            "occurred_on": "2026-11-16",
            "title": "Supermarket",
            "splits": [
                {"category_id": str(categories["groceries"].id), "amount": "60.00"},
                {"category_id": str(categories["household"].id), "amount": "40.00"},
            ],
        },
        format="json",
    )
    assert response.status_code == 201
    data = response.json()
    assert data["amount_minor"] == 10000
    assert data["amount"] == "100.00"
    assert data["is_split"] is True
    assert len(data["splits"]) == 2


@pytest.mark.django_db
def test_split_mismatch_returns_code(api, auth_user, account, categories):
    api.force_authenticate(auth_user)
    response = api.post(
        "/api/v1/transactions/",
        {
            "type": "expense",
            "account_id": str(account.id),
            "amount": "100.00",
            "currency": "USD",
            "occurred_on": "2026-11-16",
            "title": "Supermarket",
            "splits": [
                {"category_id": str(categories["groceries"].id), "amount": "60.00"},
                {"category_id": str(categories["household"].id), "amount": "39.99"},
            ],
        },
        format="json",
    )
    assert response.status_code == 400
    err = response.json()["error"]
    assert err["code"] == "split_total_mismatch"
    assert err["details"]["difference"] == "0.01"


@pytest.mark.django_db
def test_audited_edit_reverses_and_updates_audit(api, auth_user, account, categories):
    api.force_authenticate(auth_user)
    create_res = api.post(
        "/api/v1/transactions/",
        {
            "type": "expense",
            "account_id": str(account.id),
            "amount": "50.00",
            "currency": "USD",
            "occurred_on": "2026-11-16",
            "title": "Dinner",
            "category_id": str(categories["groceries"].id),
        },
        format="json",
    )
    tx_id = create_res.json()["id"]

    # Audited patch
    patch_res = api.patch(
        f"/api/v1/transactions/{tx_id}/",
        {
            "expected_version": 1,
            "reason": "Corrected price",
            "amount": "55.00",
        },
        format="json",
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["amount"] == "55.00"
    assert patch_res.json()["version"] == 2

    # Query audit history
    audit_res = api.get(f"/api/v1/transactions/{tx_id}/audit/")
    assert audit_res.status_code == 200
    revisions = audit_res.json()
    assert len(revisions) == 2
    assert revisions[0]["revision"] == 1
    assert revisions[0]["action"] == "create"
    assert revisions[1]["revision"] == 2
    assert revisions[1]["action"] == "update"
    assert (
        "amount" in revisions[1]["changed_fields"]
        or "amount_minor" in revisions[1]["changed_fields"]
    )


@pytest.mark.django_db
def test_version_conflict_rejected(api, auth_user, account, categories):
    api.force_authenticate(auth_user)
    create_res = api.post(
        "/api/v1/transactions/",
        {
            "type": "expense",
            "account_id": str(account.id),
            "amount": "50.00",
            "currency": "USD",
            "occurred_on": "2026-11-16",
            "title": "Dinner",
            "category_id": str(categories["groceries"].id),
        },
        format="json",
    )
    tx_id = create_res.json()["id"]

    # Provide stale expected_version
    fail_res = api.patch(
        f"/api/v1/transactions/{tx_id}/",
        {
            "expected_version": 99,
            "reason": "Stale edit",
            "amount": "60.00",
        },
        format="json",
    )
    assert fail_res.status_code == 409
    assert fail_res.json()["error"]["code"] == "version_conflict"
