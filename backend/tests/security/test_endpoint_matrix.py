"""Security matrix tests verifying cross-workspace isolation across all endpoints."""

from datetime import date

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import AccountType
from apps.accounts.services import create_account
from apps.categories.models import Category, CategoryKind
from apps.transactions.services.create import create_transaction
from tests.factories.users import UserFactory


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def user_a():
    return UserFactory()


@pytest.fixture
def user_b():
    return UserFactory()


@pytest.fixture
def account_b(user_b):
    return create_account(
        workspace=user_b.workspace,
        actor=user_b,
        name="User B Private Checking",
        account_type=AccountType.CHECKING,
        currency="USD",
    )


@pytest.fixture
def tx_b(user_b, account_b):
    cat = Category.objects.create(
        workspace=user_b.workspace, name="User B Category", kind=CategoryKind.EXPENSE
    )
    return create_transaction(
        workspace=user_b.workspace,
        actor=user_b,
        kind="expense",
        account_id=account_b.id,
        amount="50.00",
        currency="USD",
        occurred_on=date(2026, 11, 16),
        title="User B Secret Spending",
        category_id=cat.id,
    )


@pytest.mark.django_db
def test_cross_workspace_account_detail_is_404(api, user_a, account_b):
    api.force_authenticate(user_a)
    res = api.get(f"/api/v1/accounts/{account_b.id}/")
    assert res.status_code == 404
    assert "User B Private" not in res.content.decode()


@pytest.mark.django_db
def test_cross_workspace_account_mutation_is_404(api, user_a, account_b):
    api.force_authenticate(user_a)

    patch_res = api.patch(
        f"/api/v1/accounts/{account_b.id}/", {"name": "Hacked Name"}, format="json"
    )
    assert patch_res.status_code == 404

    archive_res = api.post(
        f"/api/v1/accounts/{account_b.id}/archive/", {"reason": "Attack"}, format="json"
    )
    assert archive_res.status_code == 404

    restore_res = api.post(f"/api/v1/accounts/{account_b.id}/restore/", format="json")
    assert restore_res.status_code == 404


@pytest.mark.django_db
def test_cross_workspace_transaction_detail_and_audit_is_404(api, user_a, tx_b):
    api.force_authenticate(user_a)

    get_res = api.get(f"/api/v1/transactions/{tx_b.id}/")
    assert get_res.status_code == 404
    assert "User B Secret" not in get_res.content.decode()

    audit_res = api.get(f"/api/v1/transactions/{tx_b.id}/audit/")
    assert audit_res.status_code == 404


@pytest.mark.django_db
def test_cross_workspace_transaction_mutations_are_404(api, user_a, tx_b):
    api.force_authenticate(user_a)

    patch_res = api.patch(
        f"/api/v1/transactions/{tx_b.id}/",
        {"expected_version": 1, "reason": "Attack", "amount": "99.00"},
        format="json",
    )
    assert patch_res.status_code == 404

    archive_res = api.post(
        f"/api/v1/transactions/{tx_b.id}/archive/",
        {"reason": "Attack"},
        format="json",
    )
    assert archive_res.status_code == 404
