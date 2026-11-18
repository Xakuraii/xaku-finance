"""Opening balance service."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from django.db import transaction

from apps.common.money import Money
from apps.ledger.models import JournalEntryStatus, JournalEntryType
from apps.ledger.services.accounts import (
    get_or_create_account_ledger_account,
    provision_system_accounts,
)
from apps.ledger.services.posting import EntrySpec, PostingSpec, post_entry
from apps.transactions.models import (
    OpeningBalance,
    Transaction,
    TransactionAudit,
    TransactionStatus,
    TransactionType,
)
from apps.workspaces.models import Workspace

if TYPE_CHECKING:
    from apps.accounts.models import Account
    from apps.identity.models import User


class DuplicateOpeningBalance(ValueError):
    """Raised when an opening balance is recorded more than once for an account."""


def create_opening_balance(
    *,
    workspace: Workspace,
    actor: User | None,
    account: Account,
    amount: str,
    as_of: date,
) -> Transaction:
    """Record an opening balance for an account backed by equity postings."""
    with transaction.atomic():
        if OpeningBalance.objects.filter(account=account).exists():
            raise DuplicateOpeningBalance(
                f"Opening balance already recorded for account {account.id}"
            )

        money = Money.parse(amount, account.currency_id)
        amount_minor = money.amount_minor

        tx = Transaction.objects.create(
            workspace=workspace,
            account=account,
            currency_id=account.currency_id,
            transaction_type=TransactionType.OPENING_BALANCE,
            status=TransactionStatus.COMPLETED,
            amount_minor=amount_minor,
            occurred_on=as_of,
            title=f"Opening balance for {account.name}",
            version=1,
            created_by=actor,
        )

        OpeningBalance.objects.create(
            workspace=workspace,
            transaction=tx,
            account=account,
            as_of=as_of,
        )

        if amount_minor > 0:
            account_ledger = get_or_create_account_ledger_account(account=account)
            system_accounts = provision_system_accounts(workspace=workspace)
            equity_key = f"equity:opening_balance:{account.currency_id}"
            equity_ledger = system_accounts[equity_key]

            # Debit asset (+), Credit equity (-)
            postings = [
                PostingSpec(
                    ledger_account_id=account_ledger.id,
                    amount_minor=amount_minor,
                    currency=account.currency_id,
                    memo=f"Opening balance: {account.name}",
                ),
                PostingSpec(
                    ledger_account_id=equity_ledger.id,
                    amount_minor=-amount_minor,
                    currency=account.currency_id,
                    memo=f"Opening balance equity: {account.name}",
                ),
            ]

            entry_spec = EntrySpec(
                entry_type=str(JournalEntryType.OPENING_BALANCE),
                status=str(JournalEntryStatus.POSTED),
                effective_date=as_of,
                source_type="transaction",
                source_id=tx.id,
                postings=postings,
                description=f"Opening balance for {account.name}",
            )
            entry = post_entry(workspace=workspace, actor=actor, spec=entry_spec)
            tx.current_journal_entry = entry
            tx.save(update_fields=["current_journal_entry"])

        TransactionAudit.objects.create(
            workspace=workspace,
            transaction=tx,
            revision=1,
            actor=actor,
            reason="Opening balance recorded",
            changed_fields=["amount", "as_of"],
            before={},
            after={"amount": amount, "as_of": as_of.isoformat()},
        )

        return tx
