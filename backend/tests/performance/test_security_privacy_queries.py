"""Performance query count budget tests for Security and Privacy endpoints."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import AccountType
from apps.accounts.services import create_account
from apps.categories.models import Category, CategoryKind
from apps.privacy.models import ExportFormat, ExportScope, ExportStatus, DataExportJob
from apps.transactions.models import Transaction, TransactionStatus, TransactionType
from apps.transactions.services.opening import create_opening_balance
from tests.factories.users import UserFactory


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def security_populated_workspace():
    user = UserFactory()
    ws = user.workspace

    checking = create_account(
        workspace=ws,
        actor=user,
        name="Primary Checking",
        account_type=AccountType.CHECKING,
        currency="USD",
        is_spendable=True,
    )
    create_opening_balance(
        workspace=ws,
        account=checking,
        amount="5000.00",
        as_of=date.today(),
        actor=user,
    )

    cat = Category.objects.create(workspace=ws, name="General", kind=CategoryKind.EXPENSE)

    for i in range(10):
        Transaction.objects.create(
            workspace=ws,
            account=checking,
            category=cat,
            title=f"Sample Expense {i}",
            transaction_type=TransactionType.EXPENSE,
            status=TransactionStatus.COMPLETED,
            amount_minor=1500,
            currency_id="USD",
            occurred_on=date.today() - timedelta(days=i),
        )

    for i in range(3):
        DataExportJob.objects.create(
            user=user,
            workspace=ws,
            scope=ExportScope.ALL,
            format=ExportFormat.JSON,
            status=ExportStatus.COMPLETED,
        )

    return user


@pytest.mark.django_db
def test_privacy_data_map_query_budget(
    api, security_populated_workspace, django_assert_num_queries
):
    user = security_populated_workspace
    api.force_authenticate(user)

    # Data transparency map counts data categories across models
    # Bound to <= 15 queries
    with django_assert_num_queries(15, exact=False):
        response = api.get("/api/v1/privacy/data-map/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 5
        assert any(item.get("category") == "Financial Accounts & Balances" for item in data)


@pytest.mark.django_db
def test_export_jobs_list_query_budget(
    api, security_populated_workspace, django_assert_num_queries
):
    user = security_populated_workspace
    api.force_authenticate(user)

    # Listing export jobs with workspace isolation
    # Bound to <= 6 queries
    with django_assert_num_queries(6, exact=False):
        response = api.get("/api/v1/exports/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 3


@pytest.mark.django_db
def test_account_deletion_status_query_budget(
    api, security_populated_workspace, django_assert_num_queries
):
    user = security_populated_workspace
    api.force_authenticate(user)

    # When no deletion request exists, returns 404 cleanly within <= 5 queries
    with django_assert_num_queries(5, exact=False):
        response = api.get("/api/v1/privacy/deletion-requests/current/")
        assert response.status_code == 404

    # When an active deletion request exists, queries request within <= 5 queries
    from apps.privacy.models import AccountDeletionRequest, DeletionRequestStatus
    from django.utils import timezone
    AccountDeletionRequest.objects.create(
        user=user,
        workspace=user.workspace,
        status=DeletionRequestStatus.REQUESTED,
        execute_after=timezone.now() + timedelta(days=7),
        backup_expiry_date=timezone.now().date() + timedelta(days=37),
    )

    with django_assert_num_queries(5, exact=False):
        response = api.get("/api/v1/privacy/deletion-requests/current/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == DeletionRequestStatus.REQUESTED


@pytest.mark.django_db
def test_auth_me_query_budget_with_two_factor_status(
    api, security_populated_workspace, django_assert_num_queries
):
    user = security_populated_workspace
    api.force_authenticate(user)

    # /api/v1/me/ includes two_factor_enabled flag
    # Bound to <= 5 queries
    with django_assert_num_queries(5, exact=False):
        response = api.get("/api/v1/me/")
        assert response.status_code == 200
        data = response.json()
        assert "two_factor_enabled" in data
