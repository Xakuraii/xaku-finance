"""Integration tests for Financial Reports and double-entry ledger reconciliation."""

from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import AccountType
from apps.accounts.services import create_account
from apps.analytics.reports import (
    get_cash_flow_statement,
    get_category_report,
    get_income_expense_report,
)
from apps.categories.models import Category, CategoryKind
from apps.identity.services.registration import register_user
from apps.transactions.services.create import SplitInput, create_transaction
from apps.transactions.services.opening import create_opening_balance
from apps.transactions.services.transfer import create_transfer


@pytest.fixture
def reports_setup(db):
    user = register_user(
        email="reports_user@example.com",
        password="StrongPassword123!",
        display_name="Reports User",
    )
    ws = user.workspace

    checking = create_account(
        workspace=ws,
        actor=user,
        name="Main Checking",
        account_type=AccountType.CHECKING,
        currency="USD",
        is_spendable=True,
    )
    savings = create_account(
        workspace=ws,
        actor=user,
        name="Reserve Savings",
        account_type=AccountType.SAVINGS,
        currency="USD",
        is_spendable=False,
    )

    d1 = date(2026, 11, 1)
    create_opening_balance(
        workspace=ws,
        account=checking,
        amount="1000.00",
        as_of=d1,
        actor=user,
    )

    cat_salary = Category.objects.create(workspace=ws, name="Salary", kind=CategoryKind.INCOME)
    cat_groc = Category.objects.create(workspace=ws, name="Groceries", kind=CategoryKind.EXPENSE)
    cat_dine = Category.objects.create(workspace=ws, name="Dining", kind=CategoryKind.EXPENSE)
    cat_util = Category.objects.create(workspace=ws, name="Utilities", kind=CategoryKind.EXPENSE)

    client = APIClient()
    client.force_authenticate(user=user)

    return {
        "user": user,
        "workspace": ws,
        "checking": checking,
        "savings": savings,
        "cat_salary": cat_salary,
        "cat_groc": cat_groc,
        "cat_dine": cat_dine,
        "cat_util": cat_util,
        "client": client,
        "d1": d1,
    }


def test_income_expense_report_reconciliation(reports_setup):
    ws = reports_setup["workspace"]
    user = reports_setup["user"]
    checking = reports_setup["checking"]
    cat_salary = reports_setup["cat_salary"]
    cat_util = reports_setup["cat_util"]

    d = date(2026, 11, 5)

    # 1. Record income $3,000
    create_transaction(
        workspace=ws,
        actor=user,
        kind="income",
        account_id=checking.id,
        category_id=cat_salary.id,
        amount="3000.00",
        currency="USD",
        occurred_on=d,
        title="Monthly Salary",
    )

    # 2. Record expense $500
    create_transaction(
        workspace=ws,
        actor=user,
        kind="expense",
        account_id=checking.id,
        category_id=cat_util.id,
        amount="500.00",
        currency="USD",
        occurred_on=d,
        title="Electric bill",
    )

    start = date(2026, 11, 1)
    end = date(2026, 11, 30)

    report = get_income_expense_report(ws, start, end)

    assert report["totals"]["income"] == "3000.00"
    assert report["totals"]["expense"] == "500.00"
    assert report["totals"]["net"] == "2500.00"

    # Strict ledger reconciliation verification
    recon = report["reconciliation"]
    assert recon["ledger_income"] == "3000.00"
    assert recon["reported_income"] == "3000.00"
    assert recon["ledger_expense"] == "500.00"
    assert recon["reported_expense"] == "500.00"
    assert recon["difference"] == "0.00"


def test_category_report_with_splits(reports_setup):
    ws = reports_setup["workspace"]
    user = reports_setup["user"]
    checking = reports_setup["checking"]
    cat_util = reports_setup["cat_util"]
    cat_groc = reports_setup["cat_groc"]
    cat_dine = reports_setup["cat_dine"]

    d = date(2026, 11, 10)

    # Direct expense $100 on Utilities
    create_transaction(
        workspace=ws,
        actor=user,
        kind="expense",
        account_id=checking.id,
        category_id=cat_util.id,
        amount="100.00",
        currency="USD",
        occurred_on=d,
        title="Water bill",
    )

    # Split expense $200 ($120 Groceries, $80 Dining)
    create_transaction(
        workspace=ws,
        actor=user,
        kind="expense",
        account_id=checking.id,
        amount="200.00",
        currency="USD",
        occurred_on=d,
        title="Supermarket & Cafe",
        splits=[
            SplitInput(category_id=cat_groc.id, amount="120.00", memo="Food"),
            SplitInput(category_id=cat_dine.id, amount="80.00", memo="Coffee"),
        ],
    )

    start = date(2026, 11, 1)
    end = date(2026, 11, 30)

    cat_rep = get_category_report(ws, start, end)
    assert cat_rep["totals"]["total_spending"] == "300.00"
    assert len(cat_rep["table"]) == 3

    amounts_by_cat = {r["category_name"]: r["amount"] for r in cat_rep["table"]}
    assert amounts_by_cat["Groceries"] == "120.00"
    assert amounts_by_cat["Utilities"] == "100.00"
    assert amounts_by_cat["Dining"] == "80.00"


def test_cash_flow_excludes_internal_transfers(reports_setup):
    ws = reports_setup["workspace"]
    user = reports_setup["user"]
    checking = reports_setup["checking"]
    savings = reports_setup["savings"]
    cat_salary = reports_setup["cat_salary"]
    cat_util = reports_setup["cat_util"]

    d = date(2026, 11, 12)

    # Income $2,000
    create_transaction(
        workspace=ws,
        actor=user,
        kind="income",
        account_id=checking.id,
        category_id=cat_salary.id,
        amount="2000.00",
        currency="USD",
        occurred_on=d,
        title="Freelance",
    )

    # Expense $400
    create_transaction(
        workspace=ws,
        actor=user,
        kind="expense",
        account_id=checking.id,
        category_id=cat_util.id,
        amount="400.00",
        currency="USD",
        occurred_on=d,
        title="Server hosting",
    )

    # Internal transfer $800 from Checking to Savings
    create_transfer(
        workspace=ws,
        actor=user,
        source_account_id=checking.id,
        destination_account_id=savings.id,
        amount="800.00",
        destination_amount="800.00",
        rate=Decimal("1.0000000000"),
        occurred_on=d,
        notes="Transfer to savings",
    )

    start = date(2026, 11, 1)
    end = date(2026, 11, 30)

    cf = get_cash_flow_statement(ws, start, end)

    # Inflows: 2000.00, Outflows: 400.00, Net: 1600.00 (Transfer must NOT appear!)
    assert cf["totals"]["inflows"] == "2000.00"
    assert cf["totals"]["outflows"] == "400.00"
    assert cf["totals"]["net_cash_flow"] == "1600.00"


def test_report_api_endpoints(reports_setup):
    client = reports_setup["client"]

    # 1. Income report
    r_inc = client.get("/api/v1/reports/income/")
    assert r_inc.status_code == 200
    assert "reconciliation" in r_inc.json()

    # 2. Expenses report
    r_exp = client.get("/api/v1/reports/expenses/")
    assert r_exp.status_code == 200
    assert "reconciliation" in r_exp.json()

    # 3. Categories report
    r_cat = client.get("/api/v1/reports/categories/")
    assert r_cat.status_code == 200
    assert "reconciliation" in r_cat.json()

    # 4. Cash flow report
    r_cf = client.get("/api/v1/reports/cashflow/")
    assert r_cf.status_code == 200
    assert "reconciliation" in r_cf.json()
