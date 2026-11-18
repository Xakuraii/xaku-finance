"""Integration tests for Idempotency-Key support."""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import AccountType
from apps.accounts.services import create_account
from apps.categories.models import Category, CategoryKind
from apps.transactions.models import Transaction
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
    )


@pytest.fixture
def category(auth_user):
    return Category.objects.create(
        workspace=auth_user.workspace,
        name="Groceries",
        kind=CategoryKind.EXPENSE,
    )


@pytest.mark.django_db
def test_idempotent_replay_creates_one_transaction(api, auth_user, account, category):
    api.force_authenticate(auth_user)
    payload = {
        "type": "expense",
        "account_id": str(account.id),
        "amount": "45.00",
        "currency": "USD",
        "occurred_on": "2026-11-16",
        "title": "Weekly groceries",
        "category_id": str(category.id),
    }
    key = "9f1c73a0-test-idempotency-key"

    first = api.post(
        "/api/v1/transactions/",
        payload,
        format="json",
        HTTP_IDEMPOTENCY_KEY=key,
    )
    assert first.status_code == 201

    second = api.post(
        "/api/v1/transactions/",
        payload,
        format="json",
        HTTP_IDEMPOTENCY_KEY=key,
    )
    assert second.status_code == 201
    assert second.get("Idempotent-Replay") == "true"
    assert first.json()["id"] == second.json()["id"]

    # Exactly one transaction row created
    assert Transaction.objects.filter(workspace=auth_user.workspace).count() == 1


@pytest.mark.django_db
def test_idempotency_conflict_with_different_payload(api, auth_user, account, category):
    api.force_authenticate(auth_user)
    key = "conflict-key-12345"

    payload1 = {
        "type": "expense",
        "account_id": str(account.id),
        "amount": "10.00",
        "currency": "USD",
        "occurred_on": "2026-11-16",
        "title": "Coffee",
        "category_id": str(category.id),
    }
    first = api.post(
        "/api/v1/transactions/",
        payload1,
        format="json",
        HTTP_IDEMPOTENCY_KEY=key,
    )
    assert first.status_code == 201

    # Same key, different amount
    payload2 = dict(payload1, amount="20.00")
    second = api.post(
        "/api/v1/transactions/",
        payload2,
        format="json",
        HTTP_IDEMPOTENCY_KEY=key,
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "idempotency_conflict"
