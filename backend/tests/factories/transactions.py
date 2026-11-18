"""Factories for transaction tests."""

from __future__ import annotations

from datetime import date

import factory

from apps.transactions.models import Transaction, TransactionStatus, TransactionType
from tests.factories.accounts import AccountFactory
from tests.factories.workspaces import WorkspaceFactory


class TransactionFactory(factory.Factory):
    class Meta:
        model = Transaction

    workspace = factory.SubFactory(WorkspaceFactory)
    account = factory.SubFactory(AccountFactory)
    currency_id = "USD"
    transaction_type = TransactionType.EXPENSE
    status = TransactionStatus.COMPLETED
    amount_minor = 1000
    occurred_on = factory.LazyFunction(date.today)
    title = factory.Sequence(lambda n: f"Transaction {n}")
    version = 1

    @classmethod
    def _create(cls, model_class: type[Transaction], **kwargs: object) -> Transaction:
        return model_class.objects.create(**kwargs)
