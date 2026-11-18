"""Integration tests for Category hierarchy, depth limits, and reassignment guards."""

from __future__ import annotations

from datetime import date

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import AccountType
from apps.accounts.services import create_account
from apps.categories.models import CategoryKind
from apps.categories.services import (
    CategoryDepthExceededError,
    CategoryInUseError,
    archive_category,
    create_category,
)
from apps.transactions.services.create import create_transaction
from tests.factories.users import UserFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def workspace_categories():
    user = UserFactory()
    ws = user.workspace

    account = create_account(
        workspace=ws,
        actor=user,
        name="Main Checking",
        account_type=AccountType.CHECKING,
        currency="USD",
        opening_balance="2000.00",
        opening_balance_date=date(2026, 11, 1),
    )

    parent_cat = create_category(
        workspace=ws,
        name="Food & Dining",
        kind=CategoryKind.EXPENSE,
    )

    child_cat = create_category(
        workspace=ws,
        name="Restaurants",
        kind=CategoryKind.EXPENSE,
        parent_id=parent_cat.id,
    )

    return {
        "user": user,
        "workspace": ws,
        "account": account,
        "parent_cat": parent_cat,
        "child_cat": child_cat,
    }


@pytest.mark.django_db
def test_create_subcategory_success(workspace_categories):
    s = workspace_categories
    ws = s["workspace"]

    groceries = create_category(
        workspace=ws,
        name="Groceries",
        kind=CategoryKind.EXPENSE,
        parent_id=s["parent_cat"].id,
    )

    assert groceries.parent_id == s["parent_cat"].id
    assert groceries.kind == CategoryKind.EXPENSE
    assert s["parent_cat"].children.count() == 2


@pytest.mark.django_db
def test_prevent_third_level_nesting(workspace_categories):
    s = workspace_categories
    ws = s["workspace"]

    # Attempting to nest under child_cat (which already has a parent) must fail
    with pytest.raises(CategoryDepthExceededError):
        create_category(
            workspace=ws,
            name="Fast Food",
            kind=CategoryKind.EXPENSE,
            parent_id=s["child_cat"].id,
        )


@pytest.mark.django_db
def test_prevent_mismatched_parent_kind(workspace_categories):
    s = workspace_categories
    ws = s["workspace"]

    with pytest.raises(ValueError, match="same kind"):
        create_category(
            workspace=ws,
            name="Salary Subcategory",
            kind=CategoryKind.INCOME,
            parent_id=s["parent_cat"].id,  # parent is EXPENSE
        )


@pytest.mark.django_db
def test_archive_category_in_use_requires_reassignment(workspace_categories):
    s = workspace_categories
    ws = s["workspace"]
    user = s["user"]

    # Create transaction using child_cat
    create_transaction(
        workspace=ws,
        actor=user,
        kind="expense",
        account_id=s["account"].id,
        amount="45.00",
        currency="USD",
        occurred_on=date(2026, 11, 17),
        title="Dinner at Restaurant",
        category_id=s["child_cat"].id,
    )

    # Attempting to archive without reassignment should fail
    with pytest.raises(CategoryInUseError):
        archive_category(
            workspace=ws,
            category_id=s["child_cat"].id,
        )

    # Reassigning to parent_cat during archive should succeed
    archived = archive_category(
        workspace=ws,
        category_id=s["child_cat"].id,
        reassign_to_category_id=s["parent_cat"].id,
    )
    assert archived.is_archived is True


@pytest.mark.django_db
def test_categories_api_tree(api_client, workspace_categories):
    s = workspace_categories
    api_client.force_authenticate(s["user"])

    res = api_client.get("/api/v1/categories/")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1

    parent_item = next(c for c in data if c["id"] == str(s["parent_cat"].id))
    assert len(parent_item["children"]) == 1
    assert parent_item["children"][0]["id"] == str(s["child_cat"].id)
