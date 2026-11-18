"""Provisioning and management of system and account ledger accounts."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from apps.ledger.models import LedgerAccount, LedgerAccountKind
from apps.workspaces.models import Workspace

if TYPE_CHECKING:
    from apps.accounts.models import Account


SYSTEM_ACCOUNTS = [
    # (code, name, kind, currency_code)
    ("equity:opening_balance:USD", "Opening Balance Equity (USD)", LedgerAccountKind.EQUITY, "USD"),
    ("equity:opening_balance:KHR", "Opening Balance Equity (KHR)", LedgerAccountKind.EQUITY, "KHR"),
    ("equity:adjustment:USD", "Balance Adjustments (USD)", LedgerAccountKind.EQUITY, "USD"),
    ("equity:adjustment:KHR", "Balance Adjustments (KHR)", LedgerAccountKind.EQUITY, "KHR"),
    ("fx_clearing:USD", "FX Clearing (USD)", LedgerAccountKind.EQUITY, "USD"),
    ("fx_clearing:KHR", "FX Clearing (KHR)", LedgerAccountKind.EQUITY, "KHR"),
    ("fx_gain_loss:USD", "FX Gain / Loss (USD)", LedgerAccountKind.EXPENSE, "USD"),
    ("fx_gain_loss:KHR", "FX Gain / Loss (KHR)", LedgerAccountKind.EXPENSE, "KHR"),
]


def provision_system_accounts(*, workspace: Workspace) -> dict[str, LedgerAccount]:
    """Ensure all required system ledger accounts exist for the workspace."""
    accounts = {}
    for code, name, kind, curr in SYSTEM_ACCOUNTS:
        acc, _ = LedgerAccount.objects.get_or_create(
            workspace=workspace,
            code=code,
            defaults={
                "name": name,
                "kind": kind,
                "currency_id": curr,
                "is_system": True,
            },
        )
        accounts[code] = acc
    return accounts


def get_or_create_account_ledger_account(*, account: Account) -> LedgerAccount:
    """Ensure a financial Account has exactly one backing LedgerAccount."""
    code = f"asset:{account.id}" if account.nature == "asset" else f"liability:{account.id}"
    kind = LedgerAccountKind.ASSET if account.nature == "asset" else LedgerAccountKind.LIABILITY

    acc, _ = LedgerAccount.objects.get_or_create(
        workspace_id=account.workspace_id,
        owner_type="account",
        owner_id=account.id,
        defaults={
            "code": code,
            "name": account.name,
            "kind": kind,
            "currency_id": account.currency_id,
            "is_system": False,
        },
    )
    return acc


def get_or_create_category_ledger_account(
    *,
    category_id: uuid.UUID,
    workspace_id: uuid.UUID,
    kind: str,
    name: str,
    currency_code: str,
) -> LedgerAccount:
    """Ensure a Category has a backing LedgerAccount for the given currency."""
    acc_kind = (
        LedgerAccountKind.EXPENSE if kind == "expense" else LedgerAccountKind.INCOME
    )
    code = f"{kind}:{category_id}:{currency_code}"

    acc, _ = LedgerAccount.objects.get_or_create(
        workspace_id=workspace_id,
        code=code,
        defaults={
            "name": f"{name} ({currency_code})",
            "kind": acc_kind,
            "currency_id": currency_code,
            "is_system": True,
        },
    )
    return acc
