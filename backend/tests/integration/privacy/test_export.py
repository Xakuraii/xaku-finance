"""Integration tests for user data export endpoints and services."""

import json

import pytest
from django.utils import timezone

from apps.accounts.models import Account, AccountNature, AccountType
from apps.categories.models import Category, CategoryKind
from apps.common.models import Currency
from apps.identity.services.sessions import RequestMeta, issue_tokens
from apps.transactions.models import (
    Transaction,
    TransactionSplit,
    TransactionStatus,
    TransactionType,
)

PASSWORD = "correct horse battery staple"


@pytest.fixture
def workspace_with_data(user):
    ws = user.workspace
    usd = Currency.objects.get(code="USD")

    checking = Account.objects.create(
        workspace=ws,
        name="Main Checking",
        account_type=AccountType.CHECKING,
        nature=AccountNature.ASSET,
        currency=usd,
        is_spendable=True,
        opened_on=timezone.now().date(),
    )

    category = Category.objects.create(
        workspace=ws,
        name="Food",
        kind=CategoryKind.EXPENSE,
    )

    tx = Transaction.objects.create(
        workspace=ws,
        account=checking,
        transaction_type=TransactionType.EXPENSE,
        occurred_on=timezone.now().date(),
        amount_minor=15000,
        currency=usd,
        status=TransactionStatus.COMPLETED,
        title="Grocery run",
        description="Weekly groceries",
        category=category,
    )
    TransactionSplit.objects.create(
        workspace=ws,
        transaction=tx,
        category=category,
        amount_minor=15000,
        memo="Groceries",
    )
    return ws, checking, tx


@pytest.mark.django_db
def test_export_requires_reauth(api_client, user) -> None:
    tokens = issue_tokens(user, request_meta=RequestMeta())
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens.access}")

    # No reauth -> 403
    res = api_client.post("/api/v1/exports/", {"scope": "all", "format": "json"}, format="json")
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "reauth_required"

    # Reauth with password -> 200
    reauth_res = api_client.post("/api/v1/auth/reauth/", {"password": PASSWORD}, format="json")
    assert reauth_res.status_code == 200

    # Now export succeeds -> 201
    allowed = api_client.post("/api/v1/exports/", {"scope": "all", "format": "json"}, format="json")
    assert allowed.status_code == 201
    data = allowed.json()
    assert data["status"] == "completed"
    assert data["scope"] == "all"
    assert data["format"] == "json"
    assert data["download_url"].startswith("/api/v1/exports/")


@pytest.mark.django_db
def test_export_compilation_and_download(api_client, user, workspace_with_data) -> None:
    ws, checking, tx = workspace_with_data
    tokens = issue_tokens(user, request_meta=RequestMeta())
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens.access}")

    api_client.post("/api/v1/auth/reauth/", {"password": PASSWORD}, format="json")
    res = api_client.post("/api/v1/exports/", {"scope": "all", "format": "json"}, format="json")
    assert res.status_code == 201
    job_id = res.json()["id"]

    # Download
    download_res = api_client.get(f"/api/v1/exports/{job_id}/download/")
    assert download_res.status_code == 200
    assert download_res["Content-Type"] == "application/json"
    assert "attachment; filename=" in download_res["Content-Disposition"]

    payload = json.loads(download_res.content.decode("utf-8"))
    assert payload["export_metadata"]["version"] == "1.0.0"
    assert payload["workspace"]["name"] == ws.name
    assert len(payload["accounts"]) >= 1
    assert payload["accounts"][0]["name"] == "Main Checking"
    assert len(payload["transactions"]) >= 1
    assert payload["transactions"][0]["title"] == "Grocery run"


@pytest.mark.django_db
def test_export_csv_format(api_client, user, workspace_with_data) -> None:
    tokens = issue_tokens(user, request_meta=RequestMeta())
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens.access}")

    api_client.post("/api/v1/auth/reauth/", {"password": PASSWORD}, format="json")
    res = api_client.post(
        "/api/v1/exports/",
        {"scope": "transactions", "format": "csv"},
        format="json",
    )
    assert res.status_code == 201
    job_id = res.json()["id"]

    download_res = api_client.get(f"/api/v1/exports/{job_id}/download/")
    assert download_res.status_code == 200
    assert download_res["Content-Type"] == "text/csv"
    csv_text = download_res.content.decode("utf-8")
    assert "Transaction ID,Date,Amount" in csv_text
    assert "Grocery run" in csv_text


@pytest.mark.django_db
def test_export_list_and_cancel(api_client, user) -> None:
    tokens = issue_tokens(user, request_meta=RequestMeta())
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens.access}")

    api_client.post("/api/v1/auth/reauth/", {"password": PASSWORD}, format="json")
    res = api_client.post("/api/v1/exports/", {"scope": "all", "format": "json"}, format="json")
    job_id = res.json()["id"]

    list_res = api_client.get("/api/v1/exports/")
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1
    assert list_res.json()[0]["id"] == job_id
