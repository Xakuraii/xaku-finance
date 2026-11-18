"""Factories for accounts and ledger accounts."""

from __future__ import annotations

from datetime import date

import factory

from apps.accounts.models import Account, AccountNature, AccountType
from apps.ledger.models import LedgerAccount, LedgerAccountKind
from tests.factories.workspaces import WorkspaceFactory


class AccountFactory(factory.Factory):
    class Meta:
        model = Account

    workspace = factory.SubFactory(WorkspaceFactory)
    name = factory.Sequence(lambda n: f"Account {n}")
    account_type = AccountType.CHECKING
    currency_id = "USD"
    nature = AccountNature.ASSET
    is_spendable = True
    allows_negative_balance = False
    opened_on = factory.LazyFunction(date.today)

    @classmethod
    def _create(cls, model_class: type[Account], **kwargs: object) -> Account:
        return model_class.objects.create(**kwargs)


class LedgerAccountFactory(factory.Factory):
    class Meta:
        model = LedgerAccount

    workspace = factory.SubFactory(WorkspaceFactory)
    kind = LedgerAccountKind.ASSET
    code = factory.Sequence(lambda n: f"asset:test_{n}")
    name = factory.Sequence(lambda n: f"Ledger Account {n}")
    currency_id = "USD"
    is_system = False

    @classmethod
    def _create(cls, model_class: type[LedgerAccount], **kwargs: object) -> LedgerAccount:
        return model_class.objects.create(**kwargs)
