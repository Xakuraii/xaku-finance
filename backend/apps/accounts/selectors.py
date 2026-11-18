"""Read selectors for accounts."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from apps.common.money import Money
from apps.ledger.models import LedgerAccount
from apps.ledger.selectors import postings_balance

if TYPE_CHECKING:
    from apps.accounts.models import Account


def account_balance(*, account: Account, as_of: date | None = None) -> Money:
    """Compute the Money balance for a user account derived strictly from the ledger."""
    ledger_acc = LedgerAccount.objects.filter(
        owner_type="account",
        owner_id=account.id,
    ).first()

    minor_unit = account.currency.minor_unit if account.currency else 2

    if not ledger_acc:
        return Money(
            amount_minor=0,
            currency=account.currency_id,
            minor_unit=minor_unit,
        )

    balance_minor = postings_balance(ledger_account_id=ledger_acc.id, as_of=as_of)
    return Money(
        amount_minor=balance_minor,
        currency=account.currency_id,
        minor_unit=minor_unit,
    )
