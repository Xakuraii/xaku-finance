"""Integration tests for the Imports REST API endpoints."""

from __future__ import annotations

import io
from datetime import date

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import AccountType
from apps.accounts.services import create_account
from apps.categories.models import CategoryKind
from apps.categories.services import create_category
from apps.transactions.models import Transaction
from apps.transactions.services.create import create_transaction
from tests.factories.users import UserFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def import_api_setup():
    user = UserFactory()
    ws = user.workspace

    account = create_account(
        workspace=ws,
        actor=user,
        name="Main Account",
        account_type=AccountType.CHECKING,
        currency="USD",
        opening_balance="5000.00",
        opening_balance_date=date(2026, 11, 1),
    )

    groceries_cat = create_category(
        workspace=ws,
        name="Groceries",
        kind=CategoryKind.EXPENSE,
    )

    return {
        "user": user,
        "workspace": ws,
        "account": account,
        "groceries_cat": groceries_cat,
    }


@pytest.mark.django_db
def test_import_api_upload_resolve_and_commit(api_client, import_api_setup):
    s = import_api_setup
    ws = s["workspace"]
    user = s["user"]
    acc = s["account"]
    api_client.force_authenticate(user)

    # 1. Existing transaction that will trigger a duplicate
    create_transaction(
        workspace=ws,
        actor=user,
        kind="expense",
        account_id=acc.id,
        amount="75.00",
        currency="USD",
        occurred_on=date(2026, 11, 14),
        title="Supermarket",
        category_id=s["groceries_cat"].id,
    )

    # 2. Upload CSV with duplicate + new record
    csv_content = (
        "date,amount,description\n2026-11-14,-75.00,Supermarket\n2026-11-15,-30.00,Bookstore\n"
    )
    csv_file = io.BytesIO(csv_content.encode("utf-8"))
    csv_file.name = "statement.csv"

    upload_res = api_client.post(
        "/api/v1/imports/upload/",
        {"account_id": str(acc.id), "file": csv_file},
        format="multipart",
    )
    assert upload_res.status_code == 201
    job_data = upload_res.json()
    job_id = job_data["id"]
    assert job_data["row_count"] == 2
    assert job_data["duplicate_count"] == 1
    assert job_data["status"] == "awaiting_review"

    # 3. Retrieve staged records
    records_res = api_client.get(f"/api/v1/imports/{job_id}/records/")
    assert records_res.status_code == 200
    records_data = records_res.json()
    # paginated or list
    items = records_data["results"] if "results" in records_data else records_data
    assert len(items) == 2
    dup_item = items[0]
    assert len(dup_item["duplicate_candidates"]) == 1
    candidate_id = dup_item["duplicate_candidates"][0]["id"]

    # 4. Attempt commit before resolution: must fail with 409 Conflict
    commit_res = api_client.post(f"/api/v1/imports/{job_id}/commit/")
    assert commit_res.status_code == 409
    assert commit_res.json()["code"] == "unresolved_duplicates"

    # 5. Resolve duplicate candidate as 'skip'
    resolve_res = api_client.post(
        f"/api/v1/imports/{job_id}/resolve/",
        {"candidate_id": candidate_id, "decision": "skip"},
        format="json",
    )
    assert resolve_res.status_code == 200
    assert resolve_res.json()["decision"] == "skip"

    # 6. Commit after resolution: succeeds
    final_commit_res = api_client.post(f"/api/v1/imports/{job_id}/commit/")
    assert final_commit_res.status_code == 200
    assert final_commit_res.json()["status"] == "completed"
    assert final_commit_res.json()["imported_count"] == 1

    # Only "Bookstore" was imported
    assert Transaction.objects.filter(workspace=ws, title="Bookstore").exists()
