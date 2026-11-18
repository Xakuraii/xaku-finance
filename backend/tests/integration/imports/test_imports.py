"""Integration tests for CSV parsing, duplicate detection, and atomic import commit."""

from __future__ import annotations

from datetime import date

import pytest

from apps.accounts.models import AccountType
from apps.accounts.services import create_account
from apps.categories.models import CategoryKind
from apps.categories.services import create_category
from apps.imports.models import (
    DuplicateCandidateDecision,
    ImportJobStatus,
    ImportRecordStatus,
)
from apps.imports.services.commit import (
    UnresolvedDuplicatesError,
    commit_import_job,
    resolve_duplicate_candidate,
)
from apps.imports.services.duplicate import detect_duplicates
from apps.imports.services.parser import stage_csv_import
from apps.transactions.models import Transaction
from apps.transactions.services.create import create_transaction
from tests.factories.users import UserFactory


@pytest.fixture
def import_test_setup():
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
def test_stage_csv_and_atomic_commit(import_test_setup):
    s = import_test_setup
    ws = s["workspace"]
    user = s["user"]
    acc = s["account"]

    csv_data = (
        b"Date,Amount,Description\n"
        b"2026-11-10,-45.50,Whole Foods Market\n"
        b"2026-11-12,-12.00,Starbucks Coffee\n"
        b"2026-11-14,500.00,Client Invoice Payment\n"
    )

    job = stage_csv_import(
        workspace=ws,
        account=acc,
        actor=user,
        file_name="bank_statement.csv",
        file_bytes=csv_data,
        mapping={"date": "Date", "amount": "Amount", "title": "Description"},
    )

    assert job.status == ImportJobStatus.VALIDATED
    assert job.row_count == 3
    assert job.valid_count == 3
    assert job.invalid_count == 0

    # Commit the job
    completed_job = commit_import_job(workspace=ws, actor=user, import_job_id=job.id)
    assert completed_job.status == ImportJobStatus.COMPLETED
    assert completed_job.imported_count == 3

    # Check transactions created
    txs = Transaction.objects.filter(workspace=ws, account=acc, is_archived=False).order_by(
        "occurred_on"
    )
    # opening balance + 3 imported transactions = 4
    assert txs.count() == 4
    titles = [t.title for t in txs]
    assert "Whole Foods Market" in titles
    assert "Starbucks Coffee" in titles


@pytest.mark.django_db
def test_duplicate_detection_and_resolution_blocking(import_test_setup):
    s = import_test_setup
    ws = s["workspace"]
    user = s["user"]
    acc = s["account"]

    # 1. Create an existing transaction in the account
    existing_tx = create_transaction(
        workspace=ws,
        actor=user,
        kind="expense",
        account_id=acc.id,
        amount="85.00",
        currency="USD",
        occurred_on=date(2026, 11, 15),
        title="Costco Wholesale",
        category_id=s["groceries_cat"].id,
    )

    # 2. Stage a CSV containing an exact duplicate of this transaction, plus a new one
    csv_data = (
        b"Date,Amount,Description\n"
        b"2026-11-15,-85.00,Costco Wholesale\n"
        b"2026-11-16,-25.00,Gas Station\n"
    )

    job = stage_csv_import(
        workspace=ws,
        account=acc,
        actor=user,
        file_name="november_costs.csv",
        file_bytes=csv_data,
        mapping={"date": "Date", "amount": "Amount", "title": "Description"},
    )

    # 3. Run duplicate detection
    dup_count = detect_duplicates(job)
    assert dup_count == 1
    assert job.status == ImportJobStatus.AWAITING_REVIEW

    dup_rec = job.records.get(row_number=1)
    assert dup_rec.status == ImportRecordStatus.DUPLICATE_EXACT
    assert dup_rec.duplicate_candidates.count() == 1
    candidate = dup_rec.duplicate_candidates.first()
    assert candidate.existing_transaction_id == existing_tx.id
    assert candidate.score >= 0.900

    # 4. Attempting commit while candidate is pending MUST fail!
    with pytest.raises(UnresolvedDuplicatesError):
        commit_import_job(workspace=ws, actor=user, import_job_id=job.id)

    # 5. Resolve duplicate candidate as 'skip'
    resolve_duplicate_candidate(
        workspace=ws,
        actor=user,
        candidate_id=candidate.id,
        decision=DuplicateCandidateDecision.SKIP,
    )

    # 6. Commit succeeds: duplicate row is skipped, only row 2 is imported!
    completed_job = commit_import_job(workspace=ws, actor=user, import_job_id=job.id)
    assert completed_job.status == ImportJobStatus.COMPLETED
    assert completed_job.imported_count == 1

    gas_tx = Transaction.objects.get(workspace=ws, title="Gas Station")
    assert gas_tx.amount_minor == 2500
