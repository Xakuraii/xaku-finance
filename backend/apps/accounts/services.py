"""Account lifecycle services: creation, archiving, restoration, and currency change."""

from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Account, AccountNature, AccountType
from apps.accounts.selectors import account_balance
from apps.ledger.models import Posting
from apps.ledger.services.accounts import get_or_create_account_ledger_account
from apps.transactions.services.opening import create_opening_balance

if TYPE_CHECKING:
    from apps.identity.models import User
    from apps.workspaces.models import Workspace


class AccountHasBalance(ValueError):
    """Raised when an account with a non-zero balance is archived without acknowledgement."""


class CurrencyImmutable(ValueError):
    """Raised when attempting to change the currency of an account with existing ledger postings."""


class ArchivedAccount(ValueError):
    """Raised when attempting an operation not permitted on an archived account."""


def create_account(
    *,
    workspace: Workspace,
    actor: User | None,
    name: str,
    account_type: str,
    currency: str,
    opening_balance: str | None = None,
    opening_balance_date: date | None = None,
    is_spendable: bool | None = None,
    description: str = "",
    allows_negative_balance: bool = False,
    opened_on: date | None = None,
) -> Account:
    """Create a new financial account and its backing ledger account atomically."""
    # Determine default nature
    if account_type == AccountType.CREDIT_CARD:
        nature = AccountNature.LIABILITY
    else:
        nature = AccountNature.ASSET

    # Savings account cannot be spendable
    if account_type == AccountType.SAVINGS:
        resolved_is_spendable = False
    elif is_spendable is not None:
        resolved_is_spendable = is_spendable
    else:
        resolved_is_spendable = account_type in (
            AccountType.CHECKING,
            AccountType.CASH,
            AccountType.EWALLET,
        )

    resolved_opened_on = opened_on or opening_balance_date or date.today()

    with transaction.atomic():
        account = Account.objects.create(
            workspace=workspace,
            name=name.strip(),
            account_type=account_type,
            currency_id=currency,
            nature=nature,
            description=description or "",
            is_spendable=resolved_is_spendable,
            allows_negative_balance=allows_negative_balance,
            opened_on=resolved_opened_on,
        )

        # Create backing ledger account
        get_or_create_account_ledger_account(account=account)

        # Record opening balance if provided
        if opening_balance:
            create_opening_balance(
                workspace=workspace,
                actor=actor,
                account=account,
                amount=opening_balance,
                as_of=opening_balance_date or resolved_opened_on,
            )

    return account


def archive_account(
    *,
    workspace: Workspace,
    actor: User | None,
    account_id: uuid.UUID,
    reason: str,
    acknowledge_balance: bool = False,
) -> Account:
    """Archive an account, requiring explicit acknowledgement if the balance is non-zero."""
    with transaction.atomic():
        account = Account.objects.select_for_update().get(
            id=account_id,
            workspace_id=workspace.id,
        )

        if account.is_archived:
            return account

        bal = account_balance(account=account)
        if bal.amount_minor != 0 and not acknowledge_balance:
            raise AccountHasBalance(
                f"Account '{account.name}' has non-zero balance ({bal.serialize()}). "
                "Explicit acknowledgement is required to archive."
            )

        account.is_archived = True
        account.archived_at = timezone.now()
        account.archive_reason = reason.strip()
        account.save(update_fields=["is_archived", "archived_at", "archive_reason", "updated_at"])

    return account


def restore_account(
    *,
    workspace: Workspace,
    actor: User | None,
    account_id: uuid.UUID,
) -> Account:
    """Restore an archived account."""
    with transaction.atomic():
        account = Account.objects.select_for_update().get(
            id=account_id,
            workspace_id=workspace.id,
        )

        if not account.is_archived:
            return account

        account.is_archived = False
        account.archived_at = None
        account.archive_reason = None
        account.save(update_fields=["is_archived", "archived_at", "archive_reason", "updated_at"])

    return account


def change_currency(
    *,
    workspace: Workspace,
    actor: User | None,
    account_id: uuid.UUID,
    currency: str,
) -> Account:
    """Change the currency of an account, blocked if any postings exist."""
    with transaction.atomic():
        account = Account.objects.select_for_update().get(
            id=account_id,
            workspace_id=workspace.id,
        )

        if account.currency_id == currency:
            return account

        ledger_account = get_or_create_account_ledger_account(account=account)
        has_postings = Posting.objects.filter(ledger_account=ledger_account).exists()

        if has_postings:
            raise CurrencyImmutable(
                f"Cannot change currency for account '{account.name}' "
                "because ledger postings already exist."
            )

        account.currency_id = currency
        account.save(update_fields=["currency", "updated_at"])

        ledger_account.currency_id = currency
        ledger_account.save(update_fields=["currency", "updated_at"])

    return account
