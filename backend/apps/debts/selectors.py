"""Debt selectors: outstanding principal derived from ledger, payoff projections, and progress."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from apps.common.money import Money
from apps.debts.models import Liability
from apps.ledger.selectors import postings_balance


@dataclass(frozen=True)
class LiabilityProgress:
    original_principal_minor: int
    outstanding_principal_minor: int
    paid_principal_minor: int
    progress_percent: float
    original_principal: str
    outstanding_principal: str
    paid_principal: str


@dataclass(frozen=True)
class DebtProjection:
    liability_id: str
    currency: str
    outstanding_principal_minor: int
    interest_rate: float | None
    monthly_payment_minor: int | None
    estimated_months_to_payoff: float | None
    total_interest_minor: int | None
    projected_payoff_date: str | None


def get_liability_outstanding(liability: Liability) -> int:
    """Derive outstanding principal strictly from the ledger account postings.

    In the double-entry engine, liabilities have a credit normal balance (negative posting sum).
    Outstanding debt is `-SUM(postings)`.
    """
    postings_sum = postings_balance(ledger_account_id=liability.ledger_account_id)
    return max(0, -postings_sum)


def get_liability_progress(liability: Liability) -> LiabilityProgress:
    """Calculate the repayment progress for a liability."""
    orig_minor = liability.original_principal_minor
    out_minor = get_liability_outstanding(liability)
    paid_minor = max(0, orig_minor - out_minor)

    pct = round((paid_minor / orig_minor) * 100.0, 2) if orig_minor > 0 else 100.0
    progress_percent = min(100.0, max(0.0, pct))

    orig_str = Money(orig_minor, liability.currency_code, 2).serialize()
    out_str = Money(out_minor, liability.currency_code, 2).serialize()
    paid_str = Money(paid_minor, liability.currency_code, 2).serialize()

    return LiabilityProgress(
        original_principal_minor=orig_minor,
        outstanding_principal_minor=out_minor,
        paid_principal_minor=paid_minor,
        progress_percent=progress_percent,
        original_principal=orig_str,
        outstanding_principal=out_str,
        paid_principal=paid_str,
    )


def get_debt_payoff_projection(
    liability: Liability,
    monthly_payment: str | Decimal | int | None = None,
) -> DebtProjection:
    """Calculate estimated months to payoff and projected payoff date."""
    outstanding_minor = get_liability_outstanding(liability)
    currency_code = liability.currency_code

    if outstanding_minor == 0:
        return DebtProjection(
            liability_id=str(liability.id),
            currency=currency_code,
            outstanding_principal_minor=0,
            interest_rate=float(liability.interest_rate) if liability.interest_rate else None,
            monthly_payment_minor=0,
            estimated_months_to_payoff=0.0,
            total_interest_minor=0,
            projected_payoff_date=date.today().isoformat(),
        )

    rate_float = float(liability.interest_rate) if liability.interest_rate else 0.0

    payment_minor = None
    if monthly_payment is not None:
        if isinstance(monthly_payment, (int, Decimal)):
            payment_minor = (
                int(monthly_payment)
                if isinstance(monthly_payment, int)
                else int(Decimal(monthly_payment) * 100)
            )
        else:
            payment_minor = Money.parse(str(monthly_payment), currency_code, 2).amount_minor

    # If no monthly payment provided, default to standard amortization pace or 5% of principal
    if payment_minor is None or payment_minor <= 0:
        # minimum 3% of outstanding or $50
        payment_minor = max(int(outstanding_minor * 0.05), 5000)

    # Monthly interest rate
    monthly_rate = (rate_float / 100.0) / 12.0

    months = 0
    balance = float(outstanding_minor)
    total_interest = 0.0

    # Simulate month-by-month payoff up to 360 months (30 years)
    max_months = 360
    while balance > 0 and months < max_months:
        interest_charge = balance * monthly_rate
        total_interest += interest_charge
        principal_payment = float(payment_minor) - interest_charge

        if principal_payment <= 0:
            # Payment does not even cover interest
            months = 999
            break

        balance -= principal_payment
        months += 1

    months_float = round(float(months), 1) if months < 999 else None
    payoff_date_str = None
    if months_float is not None:
        days = int(months_float * 30.4375)
        from datetime import timedelta

        payoff_date = date.today() + timedelta(days=days)
        payoff_date_str = payoff_date.isoformat()

    return DebtProjection(
        liability_id=str(liability.id),
        currency=currency_code,
        outstanding_principal_minor=outstanding_minor,
        interest_rate=rate_float if rate_float > 0 else None,
        monthly_payment_minor=payment_minor,
        estimated_months_to_payoff=months_float,
        total_interest_minor=int(round(total_interest)),
        projected_payoff_date=payoff_date_str,
    )
