"""Property-based tests for ledger balancing invariants."""

from __future__ import annotations

from datetime import date

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from apps.ledger.models import JournalEntryStatus, JournalEntryType, LedgerAccountKind
from apps.ledger.selectors import postings_balance
from apps.ledger.services.posting import EntrySpec, PostingSpec, post_entry
from apps.ledger.services.reconciliation import reconcile_workspace
from apps.ledger.services.reversal import reverse_entry
from tests.factories.accounts import LedgerAccountFactory
from tests.factories.users import UserFactory


@pytest.mark.django_db
@settings(max_examples=10, deadline=None)
@given(
    st.lists(
        st.integers(min_value=-100_000, max_value=100_000).filter(lambda x: x != 0),
        min_size=1,
        max_size=5,
    )
)
def test_generated_postings_always_balance_and_reverse_cleanly(amounts: list[int]):
    # Form a zero-sum list of amounts by construction
    balancing_amount = -sum(amounts)
    if balancing_amount == 0:
        return
    all_amounts = [*amounts, balancing_amount]

    user = UserFactory()
    ws = user.workspace

    accounts = [
        LedgerAccountFactory(
            workspace=ws,
            kind=LedgerAccountKind.ASSET,
            code=f"asset:acc_{i}_{ws.id}",
            currency_id="USD",
        )
        for i in range(len(all_amounts))
    ]

    postings = [
        PostingSpec(ledger_account_id=acc.id, amount_minor=amt, currency="USD")
        for acc, amt in zip(accounts, all_amounts, strict=True)
    ]

    spec = EntrySpec(
        entry_type=JournalEntryType.ADJUSTMENT,
        status=JournalEntryStatus.POSTED,
        effective_date=date(2026, 11, 18),
        source_type="property_test",
        source_id=None,
        postings=postings,
    )

    entry = post_entry(workspace=ws, actor=user, spec=spec)
    assert entry.status == JournalEntryStatus.POSTED

    # Invariant: workspace reconciliation must be clean
    report = reconcile_workspace(ws)
    assert report.is_valid is True

    # Invariant: reversal brings every single account's net balance back to zero
    reverse_entry(workspace=ws, actor=user, entry=entry, reason="Hypothesis test reversal")
    for acc in accounts:
        assert postings_balance(ledger_account_id=acc.id) == 0
