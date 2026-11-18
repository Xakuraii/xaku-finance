"""Tests for debt models and constraints."""

from datetime import date
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from apps.accounts.models import AccountType
from apps.accounts.services import create_account
from apps.debts.models import (
    DebtInterestRecord,
    DebtRepayment,
    InterestType,
    Liability,
    LiabilityStatus,
    LiabilityType,
)
from apps.identity.services.registration import register_user
from apps.ledger.models import LedgerAccount, LedgerAccountKind
from apps.transactions.models import Transaction, TransactionType


@pytest.fixture
def debt_model_setup(db):
    user = register_user(
        email="debt_models@example.com",
        password="StrongPassword123!",
        display_name="Debt Models User",
    )
    ws = user.workspace
    account = create_account(
        workspace=ws,
        actor=user,
        name="Checking Account",
        account_type=AccountType.CHECKING,
        currency="USD",
    )
    ledger_acc = LedgerAccount.objects.create(
        workspace=ws,
        kind=LedgerAccountKind.LIABILITY,
        code="liability:test_setup",
        name="Test Loan Ledger",
        currency_id="USD",
    )
    return user, ws, account, ledger_acc


@pytest.mark.django_db
def test_liability_model_and_constraints(debt_model_setup):
    user, ws, account, ledger_acc = debt_model_setup

    liability = Liability.objects.create(
        workspace=ws,
        name="Car Loan",
        liability_type=LiabilityType.PERSONAL_LOAN,
        currency_code="USD",
        original_principal_minor=2500000,
        interest_rate=Decimal("4.5000"),
        interest_type=InterestType.SIMPLE,
        lender="Toyota Financial",
        ledger_account=ledger_acc,
    )
    assert liability.id is not None
    assert liability.original_principal == "25000.00"
    assert liability.status == LiabilityStatus.ACTIVE

    # Non-positive original principal violates constraint
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Liability.objects.create(
                workspace=ws,
                name="Zero Principal",
                liability_type=LiabilityType.PERSONAL_LOAN,
                currency_code="USD",
                original_principal_minor=0,
                ledger_account=LedgerAccount.objects.create(
                    workspace=ws,
                    kind=LedgerAccountKind.LIABILITY,
                    code="liability:zero_test",
                    name="Zero Test",
                    currency_id="USD",
                ),
            )

    # Negative interest rate violates constraint
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Liability.objects.create(
                workspace=ws,
                name="Negative Rate",
                liability_type=LiabilityType.PERSONAL_LOAN,
                currency_code="USD",
                original_principal_minor=100000,
                interest_rate=Decimal("-2.0000"),
                ledger_account=LedgerAccount.objects.create(
                    workspace=ws,
                    kind=LedgerAccountKind.LIABILITY,
                    code="liability:neg_rate_test",
                    name="Neg Rate Test",
                    currency_id="USD",
                ),
            )


@pytest.mark.django_db
def test_debt_repayment_constraints(debt_model_setup):
    user, ws, account, ledger_acc = debt_model_setup

    liability = Liability.objects.create(
        workspace=ws,
        name="Student Loan",
        currency_code="USD",
        original_principal_minor=1000000,
        ledger_account=ledger_acc,
    )

    tx = Transaction.objects.create(
        workspace=ws,
        account=account,
        title="Repayment TX",
        transaction_type=TransactionType.DEBT_REPAYMENT,
        amount_minor=50000,
        currency_id="USD",
        occurred_on=date.today(),
    )

    repayment = DebtRepayment.objects.create(
        workspace=ws,
        liability=liability,
        transaction=tx,
        principal_minor=40000,
        interest_minor=9000,
        fee_minor=1000,
        currency_code="USD",
        paid_on=date.today(),
    )
    assert repayment.id is not None
    assert repayment.total_amount_minor == 50000

    # Total 0 violates constraint
    tx2 = Transaction.objects.create(
        workspace=ws,
        account=account,
        title="Zero Repayment TX",
        transaction_type=TransactionType.DEBT_REPAYMENT,
        amount_minor=1000,
        currency_id="USD",
        occurred_on=date.today(),
    )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            DebtRepayment.objects.create(
                workspace=ws,
                liability=liability,
                transaction=tx2,
                principal_minor=0,
                interest_minor=0,
                fee_minor=0,
                currency_code="USD",
                paid_on=date.today(),
            )


@pytest.mark.django_db
def test_debt_interest_record_constraints(debt_model_setup):
    user, ws, account, ledger_acc = debt_model_setup

    liability = Liability.objects.create(
        workspace=ws,
        name="Line of Credit",
        currency_code="USD",
        original_principal_minor=500000,
        ledger_account=ledger_acc,
    )

    rec = DebtInterestRecord.objects.create(
        workspace=ws,
        liability=liability,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 31),
        amount_minor=1500,
    )
    assert rec.id is not None

    # End date before start date violates constraint
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            DebtInterestRecord.objects.create(
                workspace=ws,
                liability=liability,
                period_start=date(2026, 2, 1),
                period_end=date(2026, 1, 1),
                amount_minor=1000,
            )
