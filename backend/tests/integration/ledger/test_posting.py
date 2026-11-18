"""Integration tests for ledger posting, reversal, and reconciliation."""

from __future__ import annotations

from datetime import date

import pytest

from apps.common.money import Money
from apps.ledger.models import JournalEntry, JournalEntryStatus, JournalEntryType, LedgerAccountKind
from apps.ledger.selectors import get_ledger_balance, postings_balance
from apps.ledger.services.accounts import provision_system_accounts
from apps.ledger.services.posting import EntrySpec, PostingSpec, UnbalancedEntry, post_entry
from apps.ledger.services.reconciliation import reconcile_workspace
from apps.ledger.services.reversal import reverse_entry
from tests.factories.accounts import LedgerAccountFactory
from tests.factories.users import UserFactory


@pytest.fixture
def workspace_with_accounts(db):
    user = UserFactory()
    ws = user.workspace

    cash = LedgerAccountFactory(
        workspace=ws,
        kind=LedgerAccountKind.ASSET,
        code=f"asset:cash_{ws.id}",
        currency_id="USD",
    )
    groceries = LedgerAccountFactory(
        workspace=ws,
        kind=LedgerAccountKind.EXPENSE,
        code=f"expense:groceries_{ws.id}",
        currency_id="USD",
    )
    return {"user": user, "workspace": ws, "cash": cash, "groceries": groceries}


@pytest.mark.django_db
def test_post_entry_increments_ledger_seq_and_balances(workspace_with_accounts):
    ctx = workspace_with_accounts
    ws = ctx["workspace"]

    spec = EntrySpec(
        entry_type=JournalEntryType.EXPENSE,
        status=JournalEntryStatus.POSTED,
        effective_date=date(2026, 11, 18),
        source_type="transaction",
        source_id=None,
        postings=[
            PostingSpec(ledger_account_id=ctx["groceries"].id, amount_minor=6000, currency="USD"),
            PostingSpec(ledger_account_id=ctx["cash"].id, amount_minor=-6000, currency="USD"),
        ],
    )

    entry = post_entry(workspace=ws, actor=ctx["user"], spec=spec)
    assert entry.ledger_seq == 1
    assert entry.status == JournalEntryStatus.POSTED

    assert postings_balance(ledger_account_id=ctx["cash"].id) == -6000
    assert postings_balance(ledger_account_id=ctx["groceries"].id) == 6000

    cash_money = get_ledger_balance(workspace=ws, ledger_account=ctx["cash"])
    assert cash_money == Money(amount_minor=-6000, currency="USD", minor_unit=2)


@pytest.mark.django_db
def test_reverse_entry_negates_and_marks_original(workspace_with_accounts):
    ctx = workspace_with_accounts
    ws = ctx["workspace"]

    spec = EntrySpec(
        entry_type=JournalEntryType.EXPENSE,
        status=JournalEntryStatus.POSTED,
        effective_date=date(2026, 11, 18),
        source_type="transaction",
        source_id=None,
        postings=[
            PostingSpec(ledger_account_id=ctx["groceries"].id, amount_minor=6000, currency="USD"),
            PostingSpec(ledger_account_id=ctx["cash"].id, amount_minor=-6000, currency="USD"),
        ],
    )
    original_entry = post_entry(workspace=ws, actor=ctx["user"], spec=spec)

    reversal = reverse_entry(
        workspace=ws,
        actor=ctx["user"],
        entry=original_entry,
        reason="Entered in error",
    )

    original_entry.refresh_from_db()
    assert original_entry.status == JournalEntryStatus.REVERSED
    assert original_entry.reversed_by_entry_id == reversal.id

    assert reversal.status == JournalEntryStatus.POSTED
    assert reversal.entry_type == JournalEntryType.REVERSAL
    assert reversal.reverses_entry_id == original_entry.id

    # Net balance after reversal should be zero
    assert postings_balance(ledger_account_id=ctx["cash"].id) == 0
    assert postings_balance(ledger_account_id=ctx["groceries"].id) == 0


@pytest.mark.django_db
def test_unbalanced_spec_raises_before_write(workspace_with_accounts):
    ctx = workspace_with_accounts
    ws = ctx["workspace"]

    spec = EntrySpec(
        entry_type=JournalEntryType.EXPENSE,
        status=JournalEntryStatus.POSTED,
        effective_date=date(2026, 11, 18),
        source_type="transaction",
        source_id=None,
        postings=[
            PostingSpec(ledger_account_id=ctx["groceries"].id, amount_minor=6000, currency="USD"),
        ],
    )

    with pytest.raises(UnbalancedEntry):
        post_entry(workspace=ws, actor=ctx["user"], spec=spec)

    assert not JournalEntry.objects.filter(workspace=ws).exists()


@pytest.mark.django_db
def test_provision_system_accounts_is_idempotent(workspace_with_accounts):
    ws = workspace_with_accounts["workspace"]

    first_run = provision_system_accounts(workspace=ws)
    assert len(first_run) >= 8

    second_run = provision_system_accounts(workspace=ws)
    assert len(second_run) == len(first_run)
    assert {k: v.id for k, v in first_run.items()} == {k: v.id for k, v in second_run.items()}


@pytest.mark.django_db
def test_reconcile_workspace_reports_clean(workspace_with_accounts):
    ctx = workspace_with_accounts
    ws = ctx["workspace"]

    spec = EntrySpec(
        entry_type=JournalEntryType.EXPENSE,
        status=JournalEntryStatus.POSTED,
        effective_date=date(2026, 11, 18),
        source_type="transaction",
        source_id=None,
        postings=[
            PostingSpec(ledger_account_id=ctx["groceries"].id, amount_minor=3000, currency="USD"),
            PostingSpec(ledger_account_id=ctx["cash"].id, amount_minor=-3000, currency="USD"),
        ],
    )
    post_entry(workspace=ws, actor=ctx["user"], spec=spec)

    report = reconcile_workspace(ws)
    assert report.is_valid is True
    assert len(report.errors) == 0
