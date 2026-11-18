"""Tests for debt double-entry domain services and selectors."""

from datetime import date

import pytest

from apps.accounts.models import AccountType
from apps.accounts.selectors import account_balance
from apps.accounts.services import create_account
from apps.debts.models import (
    InterestType,
    LiabilityStatus,
)
from apps.debts.selectors import (
    get_debt_payoff_projection,
    get_liability_outstanding,
    get_liability_progress,
)
from apps.debts.services import (
    LiabilityArchivedError,
    OverpaymentError,
    archive_liability,
    create_liability,
    record_accrued_interest,
    record_debt_repayment,
    restore_liability,
)
from apps.identity.services.registration import register_user
from apps.transactions.services.opening import create_opening_balance


@pytest.fixture
def debt_service_setup(db):
    user = register_user(
        email="debt_svc@example.com",
        password="StrongPassword123!",
        display_name="Debt Service User",
    )
    ws = user.workspace
    checking = create_account(
        workspace=ws,
        actor=user,
        name="Operating Checking",
        account_type=AccountType.CHECKING,
        currency="USD",
    )
    # Give checking account $5,000 initial balance
    create_opening_balance(
        workspace=ws,
        account=checking,
        amount="5000.00",
        as_of=date.today(),
        actor=user,
    )
    return user, ws, checking


@pytest.mark.django_db
def test_create_liability_without_disbursement(debt_service_setup):
    user, ws, checking = debt_service_setup

    liability = create_liability(
        workspace=ws,
        actor=user,
        name="Student Loan",
        original_principal="10000.00",
        currency="USD",
        interest_rate="5.0000",
        interest_type=InterestType.SIMPLE,
    )
    assert liability.id is not None
    assert liability.ledger_account is not None

    # Outstanding derived strictly from ledger
    outstanding = get_liability_outstanding(liability)
    assert outstanding == 1000000  # $10,000.00 in minor units

    prog = get_liability_progress(liability)
    assert prog.outstanding_principal == "10000.00"
    assert prog.paid_principal == "0.00"
    assert prog.progress_percent == 0.0


@pytest.mark.django_db
def test_create_liability_with_disbursement(debt_service_setup):
    user, ws, checking = debt_service_setup

    initial_balance = account_balance(account=checking).amount_minor
    assert initial_balance == 500000  # $5,000.00

    # Borrow $2,000.00 disbursed into checking
    liability = create_liability(
        workspace=ws,
        actor=user,
        name="Personal Loan",
        original_principal="2000.00",
        currency="USD",
        initial_disbursement_account_id=str(checking.id),
        lender="Local Credit Union",
    )

    # Checking balance increased by $2,000.00 to $7,000.00
    new_balance = account_balance(account=checking).amount_minor
    assert new_balance == 700000

    # Liability ledger owes $2,000.00
    outstanding = get_liability_outstanding(liability)
    assert outstanding == 200000


@pytest.mark.django_db
def test_record_debt_repayment_and_overpayment_guard(debt_service_setup):
    user, ws, checking = debt_service_setup

    # Create $1,000 loan
    liability = create_liability(
        workspace=ws,
        actor=user,
        name="Short-term Loan",
        original_principal="1000.00",
        currency="USD",
    )
    assert get_liability_outstanding(liability) == 100000

    # 1. Overpayment guard: attempt to repay $1,200 principal on $1,000 loan
    with pytest.raises(OverpaymentError, match="exceeds remaining outstanding principal"):
        record_debt_repayment(
            workspace=ws,
            actor=user,
            liability=liability,
            paying_account_id=str(checking.id),
            principal_amount="1200.00",
        )

    # 2. Make split repayment: $300 principal + $25 interest + $5 fee = $330 total
    repayment = record_debt_repayment(
        workspace=ws,
        actor=user,
        liability=liability,
        paying_account_id=str(checking.id),
        principal_amount="300.00",
        interest_amount="25.00",
        fee_amount="5.00",
        note="Monthly installment",
    )
    assert repayment.id is not None
    assert repayment.principal_minor == 30000
    assert repayment.interest_minor == 2500
    assert repayment.fee_minor == 500
    assert repayment.total_amount_minor == 33000

    # Checking balance reduced by $330 (5000 - 330 = 4670)
    assert account_balance(account=checking).amount_minor == 467000

    # Outstanding liability reduced from 1,000 to 700
    assert get_liability_outstanding(liability) == 70000

    prog = get_liability_progress(liability)
    assert prog.outstanding_principal == "700.00"
    assert prog.paid_principal == "300.00"
    assert prog.progress_percent == 30.0

    # 3. Pay off remaining $700 principal
    record_debt_repayment(
        workspace=ws,
        actor=user,
        liability=liability,
        paying_account_id=str(checking.id),
        principal_amount="700.00",
    )
    assert get_liability_outstanding(liability) == 0
    liability.refresh_from_db()
    assert liability.status == LiabilityStatus.PAID_OFF


@pytest.mark.django_db
def test_record_accrued_interest(debt_service_setup):
    user, ws, checking = debt_service_setup

    liability = create_liability(
        workspace=ws,
        actor=user,
        name="Credit Card",
        original_principal="500.00",
        currency="USD",
    )
    assert get_liability_outstanding(liability) == 50000

    # Accrue $15.50 finance charge (interest)
    record_accrued_interest(
        workspace=ws,
        actor=user,
        liability=liability,
        amount="15.50",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 31),
        note="January APR charge",
    )

    # Outstanding principal is now $515.50 (51,550 minor units)
    assert get_liability_outstanding(liability) == 51550


@pytest.mark.django_db
def test_archive_and_restore_liability(debt_service_setup):
    user, ws, checking = debt_service_setup

    liability = create_liability(
        workspace=ws,
        actor=user,
        name="Archived Loan",
        original_principal="800.00",
        currency="USD",
    )

    archive_liability(liability=liability, actor=user)
    liability.refresh_from_db()
    assert liability.is_archived is True
    assert liability.status == LiabilityStatus.ARCHIVED

    # Cannot repay archived liability
    with pytest.raises(LiabilityArchivedError):
        record_debt_repayment(
            workspace=ws,
            actor=user,
            liability=liability,
            paying_account_id=str(checking.id),
            principal_amount="100.00",
        )

    restore_liability(liability=liability, actor=user)
    liability.refresh_from_db()
    assert liability.is_archived is False
    assert liability.status == LiabilityStatus.ACTIVE


@pytest.mark.django_db
def test_debt_projection(debt_service_setup):
    user, ws, checking = debt_service_setup

    liability = create_liability(
        workspace=ws,
        actor=user,
        name="Auto Loan",
        original_principal="12000.00",
        currency="USD",
        interest_rate="6.0000",
    )

    proj = get_debt_payoff_projection(liability, monthly_payment="400.00")
    assert proj.liability_id == str(liability.id)
    assert proj.outstanding_principal_minor == 1200000
    assert proj.estimated_months_to_payoff is not None
    # $12,000 at 6% with $400/mo pays off in ~33-35 months
    assert 30 <= proj.estimated_months_to_payoff <= 40
    assert proj.projected_payoff_date is not None
