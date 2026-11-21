"""Management command to seed a rich dual-currency (USD & KHR) demo workspace."""

from __future__ import annotations

import calendar
import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Account
from apps.accounts.services import create_account
from apps.analytics.emergency_fund import update_emergency_fund_config
from apps.analytics.models import ObligationCadence, ObligationKind, RecurringObligation
from apps.analytics.net_worth import get_or_create_snapshot
from apps.budgets.services.create import create_budget
from apps.categories.models import Category, CategoryKind
from apps.categories.services import create_category
from apps.common.models import Currency
from apps.common.money import Money
from apps.debts.services import create_liability, record_debt_repayment
from apps.identity.models import User
from apps.ledger.models import ExchangeRate, ExchangeRateSource
from apps.ledger.services.reconciliation import reconcile_workspace
from apps.savings.services import create_savings_goal, record_savings_contribution
from apps.transactions.services.create import SplitInput, create_transaction
from apps.transactions.services.transfer import create_transfer
from apps.workspaces.models import Workspace
from apps.workspaces.services import ensure_workspace


def _add_months_end(base: date, offset_months: int) -> date:
    """Return the month-end date offset_months relative to base."""
    total_months = base.year * 12 + (base.month - 1) + offset_months
    year = total_months // 12
    month = (total_months % 12) + 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, last_day)


class Command(BaseCommand):
    help = "Seed a workspace with realistic USD & Khmer Riel data across all modules."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--email", type=str, default="demo@xakufinance.local")
        parser.add_argument("--password", type=str, default="DemoPass123456")
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Detach any existing workspace onto an inactive archive user and seed fresh data.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        email: str = options["email"]
        password: str = options["password"]
        reset: bool = bool(options["reset"])

        Currency.objects.get_or_create(
            code="USD", defaults={"name": "US Dollar", "symbol": "$", "minor_unit": 2}
        )
        Currency.objects.get_or_create(
            code="KHR", defaults={"name": "Cambodian Riel", "symbol": "៛", "minor_unit": 2}
        )

        user = User.objects.filter(email=email).first()
        if not user:
            user = User.objects.create_user(email=email, password=password)
            user.is_email_verified = True
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Created demo user {email}"))
        else:
            user.set_password(password)
            user.is_email_verified = True
            user.failed_login_count = 0
            user.locked_until = None
            user.is_active = True
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Reset credentials for {email}"))

        today = timezone.localdate()

        with transaction.atomic():
            if reset:
                old_ws = Workspace.objects.filter(owner=user).first()
                if old_ws is not None:
                    # Preserve immutable ledger entries by reassigning the old workspace owner
                    # to an inactive archive account instead of deleting posted journal entries.
                    archive_email = f"archived-seed-{uuid.uuid4().hex[:10]}@xakufinance.local"
                    archive_user = User.objects.create_user(email=archive_email, password=None)
                    archive_user.is_active = False
                    archive_user.save(update_fields=["is_active"])
                    old_ws.owner = archive_user
                    old_ws.archived_at = timezone.now()
                    old_ws.name = f"Archived Demo ({today.isoformat()})"[:80]
                    old_ws.save(update_fields=["owner", "archived_at", "name"])
                    self.stdout.write(
                        self.style.WARNING("Detached previous workspace for clean reset.")
                    )

            ws = ensure_workspace(user=user)
            if ws.name != "Personal & Studio":
                ws.name = "Personal & Studio"
                ws.timezone = "Asia/Phnom_Penh"
                ws.save(update_fields=["name", "timezone", "updated_at"])

            if Account.objects.filter(workspace=ws, is_archived=False).exists():
                self.stdout.write(
                    self.style.WARNING(
                        "Workspace already contains active accounts. Re-run with --reset to rebuild."
                    )
                )
                return

            self._seed_workspace_contents(ws=ws, user=user, today=today)

    def _seed_workspace_contents(self, *, ws: Workspace, user: User, today: date) -> None:

        opened_on = today - timedelta(days=190)

        # 1. Exchange Rates (USD <-> KHR)
        for fx_date, usd_to_khr in [
            (opened_on, Decimal("4085.0000000000")),
            (today - timedelta(days=75), Decimal("4095.0000000000")),
            (today - timedelta(days=20), Decimal("4100.0000000000")),
            (today, Decimal("4100.0000000000")),
        ]:
            khr_to_usd = (Decimal("1") / usd_to_khr).quantize(Decimal("0.0000000001"))
            ExchangeRate.objects.update_or_create(
                workspace=ws,
                base_currency_id="USD",
                quote_currency_id="KHR",
                effective_date=fx_date,
                source=ExchangeRateSource.MANUAL,
                defaults={"rate": usd_to_khr, "set_by": user},
            )
            ExchangeRate.objects.update_or_create(
                workspace=ws,
                base_currency_id="KHR",
                quote_currency_id="USD",
                effective_date=fx_date,
                source=ExchangeRateSource.MANUAL,
                defaults={"rate": khr_to_usd, "set_by": user},
            )

        # 2. Realistic Multi-Currency Accounts
        aba_checking = create_account(
            workspace=ws,
            actor=user,
            name="ABA USD Payroll & Checking",
            account_type="checking",
            currency="USD",
            opening_balance="4820.45",
            opening_balance_date=opened_on,
            is_spendable=True,
            description="Primary USD payroll deposit, rent, and international billing",
        )
        wing_khr = create_account(
            workspace=ws,
            actor=user,
            name="Wing Bank KHR Wallet",
            account_type="ewallet",
            currency="KHR",
            opening_balance="6250000.00",
            opening_balance_date=opened_on,
            is_spendable=True,
            description="KHQR everyday spending, utilities, and local retainers",
        )
        reserve_vault = create_account(
            workspace=ws,
            actor=user,
            name="High-Yield Reserve Vault",
            account_type="savings",
            currency="USD",
            opening_balance="9650.00",
            opening_balance_date=opened_on,
            is_spendable=False,
            description="Locked emergency buffer & dedicated long-term reserve",
        )
        cash_khr = create_account(
            workspace=ws,
            actor=user,
            name="Phnom Penh Cash Pouch",
            account_type="cash",
            currency="KHR",
            opening_balance="840000.00",
            opening_balance_date=opened_on,
            is_spendable=True,
            description="Physical Riel cash for local markets, tuk-tuks, and cafes",
        )
        etf_portfolio = create_account(
            workspace=ws,
            actor=user,
            name="Brokerage Index ETFs",
            account_type="investment",
            currency="USD",
            opening_balance="5480.75",
            opening_balance_date=opened_on,
            is_spendable=False,
            description="Long-horizon equity index holdings",
        )

        # 3. Categories
        def get_cat(name: str, kind: str, icon: str, color: str, order: int) -> Category:
            existing = Category.objects.filter(workspace=ws, name=name).first()
            if existing:
                return existing
            return create_category(
                workspace=ws,
                name=name,
                kind=kind,
                icon=icon,
                color=color,
                sort_order=order,
            )

        cat_salary = get_cat("Monthly Salary", CategoryKind.INCOME, "briefcase", "#10B981", 1)
        cat_consulting = get_cat("Product Consulting", CategoryKind.INCOME, "laptop", "#38BDF8", 2)
        cat_retainer_khr = get_cat("Local Studio Retainer", CategoryKind.INCOME, "sparkles", "#F0B90B", 3)
        cat_dividends = get_cat("Dividends & Yield", CategoryKind.INCOME, "trending-up", "#A78BFA", 4)

        cat_housing = get_cat("Housing & Rent", CategoryKind.EXPENSE, "home", "#F0B90B", 10)
        cat_groceries = get_cat("Groceries & Market", CategoryKind.EXPENSE, "shopping-cart", "#10B981", 11)
        cat_dining = get_cat("Coffee & Dining", CategoryKind.EXPENSE, "coffee", "#FB923C", 12)
        cat_transport = get_cat("Transport & Grab", CategoryKind.EXPENSE, "car", "#38BDF8", 13)
        cat_utilities = get_cat("Utilities & Fiber", CategoryKind.EXPENSE, "zap", "#A78BFA", 14)
        cat_software = get_cat("Cloud & SaaS Tools", CategoryKind.EXPENSE, "cpu", "#60A5FA", 15)
        cat_health = get_cat("Healthcare & Pharmacy", CategoryKind.EXPENSE, "heart-pulse", "#F43F5E", 16)
        cat_travel = get_cat("Travel & Getaways", CategoryKind.EXPENSE, "plane", "#14B8A6", 17)

        # 4. Varied 6-month Income & Expense Activity (USD + KHR)
        def clamp_date(days_ago: int) -> date:
            return today - timedelta(days=max(0, days_ago))

        income_schedule = [
            (168, aba_checking, "USD", "3420.18", "Engineering Payroll - Month 1", cat_salary, "Vannak Tech Co", ["salary", "payroll"]),
            (152, aba_checking, "USD", "685.40", "UX Design Sprint Advisory", cat_consulting, "Studio K", ["consulting", "work"]),
            (138, aba_checking, "USD", "3485.62", "Engineering Payroll - Month 2", cat_salary, "Vannak Tech Co", ["salary", "payroll"]),
            (126, wing_khr, "KHR", "1850000.00", "Phnom Penh Boutique Retainer", cat_retainer_khr, "Mekong Retail", ["retainer", "khmer"]),
            (108, aba_checking, "USD", "3610.40", "Engineering Payroll & Bonus", cat_salary, "Vannak Tech Co", ["salary", "payroll"]),
            (96, etf_portfolio, "USD", "164.35", "Quarterly Index ETF Dividend", cat_dividends, "Vanguard VOO", ["dividend", "passive"]),
            (78, aba_checking, "USD", "3420.18", "Engineering Payroll - Month 4", cat_salary, "Vannak Tech Co", ["salary", "payroll"]),
            (64, aba_checking, "USD", "1120.25", "API Architecture Audit", cat_consulting, "FinCore Asia", ["consulting", "work"]),
            (48, aba_checking, "USD", "3795.90", "Engineering Payroll & On-Call", cat_salary, "Vannak Tech Co", ["salary", "payroll"]),
            (32, wing_khr, "KHR", "2140000.00", "Cambodia Storefront Consultation", cat_retainer_khr, "Sovann Group", ["retainer", "khmer"]),
            (18, aba_checking, "USD", "3540.75", "Engineering Payroll - Current", cat_salary, "Vannak Tech Co", ["salary", "payroll"]),
            (9, aba_checking, "USD", "845.60", "Mobile Checkout Audit Milestone", cat_consulting, "Kiri Pay", ["consulting", "work"]),
            (4, etf_portfolio, "USD", "178.92", "Monthly Yield Reinvestment", cat_dividends, "Vanguard VOO", ["dividend", "passive"]),
        ]

        for days_ago, acct, curr, amt, title, cat, merchant, tags in income_schedule:
            create_transaction(
                workspace=ws,
                actor=user,
                kind="income",
                account_id=acct.id,
                amount=amt,
                currency=curr,
                occurred_on=clamp_date(days_ago),
                title=title,
                category_id=cat.id,
                merchant=merchant,
                tags=tags,
                status="completed",
            )

        # Realistic, non-repetitive USD and KHR expenses spread across 175 days + current month
        expense_schedule = [
            # Month -5 to -3 historical baseline
            (164, aba_checking, "USD", "725.00", "Apartment Lease - BKK1", cat_housing, "BKK1 Residences", "essential", ["recurring", "housing"]),
            (160, wing_khr, "KHR", "236000.00", "Lucky Market Weekly Produce", cat_groceries, "Lucky Supermarket", "essential", ["grocery", "phnom-penh"]),
            (155, cash_khr, "KHR", "18500.00", "Brown Iced Latte & Croissant", cat_dining, "Brown Coffee", "lifestyle", ["coffee"]),
            (149, aba_checking, "USD", "68.42", "Ezecom Fiber & EDC Electric", cat_utilities, "Ezecom", "essential", ["recurring", "utilities"]),
            (134, aba_checking, "USD", "725.00", "Apartment Lease - BKK1", cat_housing, "BKK1 Residences", "essential", ["recurring", "housing"]),
            (131, wing_khr, "KHR", "194500.00", "Aeon Supermarket Fresh Haul", cat_groceries, "Aeon Mall 1", "essential", ["grocery", "phnom-penh"]),
            (122, aba_checking, "USD", "41.80", "AWS + Cloud Backups", cat_software, "Amazon Web Services", "important", ["saas", "work"]),
            (114, cash_khr, "KHR", "24500.00", "Grab Rides & Tuk-Tuk", cat_transport, "Grab Cambodia", "important", ["transport"]),
            (104, aba_checking, "USD", "740.00", "Apartment Lease + Parking", cat_housing, "BKK1 Residences", "essential", ["recurring", "housing"]),
            (99, wing_khr, "KHR", "218000.00", "Thai Huot Organic Groceries", cat_groceries, "Thai Huot", "essential", ["grocery"]),
            (91, aba_checking, "USD", "186.35", "Kampot Weekend Riverside Stay", cat_travel, "Amber Kampot", "lifestyle", ["weekend", "travel"]),
            (86, wing_khr, "KHR", "142000.00", "Royal Phnom Penh Checkup", cat_health, "Royal PP Hospital", "essential", ["health"]),
            # Month -2 to -1
            (74, aba_checking, "USD", "740.00", "Apartment Lease + Parking", cat_housing, "BKK1 Residences", "essential", ["recurring", "housing"]),
            (70, aba_checking, "USD", "74.15", "EDC Electric & Water Utility", cat_utilities, "EDC Phnom Penh", "essential", ["recurring", "utilities"]),
            (66, aba_checking, "USD", "91.74", "Super Duper Pantry Restock", cat_groceries, "Super Duper", "essential", ["grocery"]),
            (61, cash_khr, "KHR", "16500.00", "Tube Coffee Morning", cat_dining, "Tube Coffee", "lifestyle", ["coffee"]),
            (55, aba_checking, "USD", "218.40", "Siem Reap Flight & Boutique", cat_travel, "Cambodia Angkor Air", "lifestyle", ["travel", "weekend"]),
            (45, aba_checking, "USD", "740.00", "Apartment Lease + Parking", cat_housing, "BKK1 Residences", "essential", ["recurring", "housing"]),
            (41, wing_khr, "KHR", "274000.00", "Malis Khmer Fine Dining", cat_dining, "Malis Restaurant", "lifestyle", ["dining", "family"]),
            (37, aba_checking, "USD", "38.99", "Figma + GitHub Copilot Pro", cat_software, "Figma Inc", "important", ["saas", "work"]),
            (33, wing_khr, "KHR", "164500.00", "Makro Household & Produce", cat_groceries, "Makro Cambodia", "essential", ["grocery"]),
            # Current month dense varied activity (< 28 days ago)
            (22, aba_checking, "USD", "740.00", "Apartment Lease + Parking", cat_housing, "BKK1 Residences", "essential", ["recurring", "housing"]),
            (19, aba_checking, "USD", "71.20", "Ezecom Fiber & Mobile Data", cat_utilities, "Ezecom", "essential", ["recurring", "utilities"]),
            (16, wing_khr, "KHR", "188500.00", "Orussey & Lucky Fresh Market", cat_groceries, "Lucky Supermarket", "essential", ["grocery", "phnom-penh"]),
            (14, cash_khr, "KHR", "22000.00", "Grab Car Airport Pickup", cat_transport, "Grab Cambodia", "important", ["transport"]),
            (11, aba_checking, "USD", "87.50", "Dental Hygiene & Scaling", cat_health, "Roomchang Clinic", "important", ["health"]),
            (9, aba_checking, "USD", "64.38", "Super Duper Cold Cuts & Olive Oil", cat_groceries, "Super Duper", "essential", ["grocery"]),
            (7, wing_khr, "KHR", "96000.00", "KOI & Khmer Lunch with Team", cat_dining, "Eleven One Kitchen", "lifestyle", ["dining"]),
            (5, aba_checking, "USD", "46.85", "Cloudflare + Linear + Hosting", cat_software, "Cloudflare", "important", ["saas", "work"]),
            (3, cash_khr, "KHR", "19500.00", "Espresso & Pastries", cat_dining, "Brown Coffee", "lifestyle", ["coffee"]),
            (2, aba_checking, "USD", "53.19", "Pharmacare Vitamins & First Aid", cat_health, "Ucare Pharmacy", "unplanned", ["health"]),
            (1, wing_khr, "KHR", "48500.00", "PassApp & Petrol Refill", cat_transport, "Tela Station", "important", ["transport"]),
        ]

        for days_ago, acct, curr, amt, title, cat, merchant, necessity, tags in expense_schedule:
            create_transaction(
                workspace=ws,
                actor=user,
                kind="expense",
                account_id=acct.id,
                amount=amt,
                currency=curr,
                occurred_on=clamp_date(days_ago),
                title=title,
                category_id=cat.id,
                merchant=merchant,
                necessity=necessity,
                tags=tags,
                status="completed",
            )

        # Multi-category split transactions (USD and KHR)
        create_transaction(
            workspace=ws,
            actor=user,
            kind="expense",
            account_id=aba_checking.id,
            amount="148.65",
            currency="USD",
            occurred_on=clamp_date(6),
            title="Super Duper & Clinic Pantry Split",
            merchant="Super Duper",
            necessity="essential",
            tags=["grocery", "health"],
            splits=[
                SplitInput(category_id=cat_groceries.id, amount="104.25", memo="Fresh produce & pantry"),
                SplitInput(category_id=cat_health.id, amount="44.40", memo="Multivitamins & bandages"),
            ],
        )
        create_transaction(
            workspace=ws,
            actor=user,
            kind="expense",
            account_id=wing_khr.id,
            amount="312000.00",
            currency="KHR",
            occurred_on=clamp_date(13),
            title="Aeon Mall Groceries & Cafe Split",
            merchant="Aeon Mall",
            necessity="important",
            tags=["grocery", "dining", "phnom-penh"],
            splits=[
                SplitInput(category_id=cat_groceries.id, amount="228000.00", memo="Weekly groceries"),
                SplitInput(category_id=cat_dining.id, amount="84000.00", memo="Dinner court"),
            ],
        )

        # Pending outflows (visible in Safe-to-Spend pending calculation)
        create_transaction(
            workspace=ws,
            actor=user,
            kind="expense",
            account_id=aba_checking.id,
            amount="58.90",
            currency="USD",
            occurred_on=today,
            title="Pending EDC Utility Invoice",
            category_id=cat_utilities.id,
            merchant="EDC Phnom Penh",
            necessity="essential",
            tags=["utilities", "pending"],
            status="pending",
        )
        create_transaction(
            workspace=ws,
            actor=user,
            kind="expense",
            account_id=wing_khr.id,
            amount="124000.00",
            currency="KHR",
            occurred_on=today,
            title="Pending Lab Bloodwork Copay",
            category_id=cat_health.id,
            merchant="Pasteur Clinic",
            necessity="important",
            tags=["health", "pending"],
            status="pending",
        )

        # 5. Cross-Currency FX Transfer + Savings Vault Transfer
        create_transfer(
            workspace=ws,
            actor=user,
            source_account_id=aba_checking.id,
            destination_account_id=wing_khr.id,
            amount="450.00",
            destination_amount="1845000.00",
            rate=Decimal("4100.00"),
            reference_rate=Decimal("4100.00"),
            occurred_on=clamp_date(24),
            notes="Top-up Wing KHR Wallet from USD Payroll",
        )
        create_transfer(
            workspace=ws,
            actor=user,
            source_account_id=aba_checking.id,
            destination_account_id=reserve_vault.id,
            amount="600.00",
            occurred_on=clamp_date(11),
            notes="Monthly automated transfer to Reserve Vault",
        )

        # 6. Current Month Active Budgets (USD & KHR)
        month_start = date(today.year, today.month, 1)
        create_budget(
            workspace=ws,
            name="Groceries & Fresh Market",
            category_id=cat_groceries.id,
            amount="420.00",
            currency="USD",
            period_type="monthly",
            rollover_enabled=True,
            is_flexible=True,
            starts_on=month_start,
        )
        create_budget(
            workspace=ws,
            name="Coffee & Dining",
            category_id=cat_dining.id,
            amount="260.00",
            currency="USD",
            period_type="monthly",
            rollover_enabled=False,
            is_flexible=True,
            starts_on=month_start,
        )
        create_budget(
            workspace=ws,
            name="Housing & Rent",
            category_id=cat_housing.id,
            amount="850.00",
            currency="USD",
            period_type="monthly",
            rollover_enabled=False,
            is_flexible=False,
            starts_on=month_start,
        )
        create_budget(
            workspace=ws,
            name="Cloud & SaaS Tools",
            category_id=cat_software.id,
            amount="140.00",
            currency="USD",
            period_type="monthly",
            rollover_enabled=True,
            is_flexible=True,
            starts_on=month_start,
        )
        create_budget(
            workspace=ws,
            name="Daily Grab & Transport (KHR)",
            category_id=cat_transport.id,
            amount="1450000.00",
            currency="KHR",
            period_type="monthly",
            rollover_enabled=False,
            is_flexible=True,
            starts_on=month_start,
        )

        # 7. Savings Goals & Earmark Contributions
        goal_emergency = create_savings_goal(
            workspace=ws,
            actor=user,
            name="6-Month Emergency Runway",
            target_amount="12500.00",
            currency="USD",
            target_date=today + timedelta(days=210),
            linked_account_id=str(reserve_vault.id),
            strategy="linked_account",
            notes="Dedicated USD safety reserve",
        )
        record_savings_contribution(
            workspace=ws,
            actor=user,
            goal=goal_emergency,
            kind="earmark",
            amount="2850.00",
            account_id=str(reserve_vault.id),
            occurred_on=clamp_date(60),
            note="Initial emergency tranche",
        )
        record_savings_contribution(
            workspace=ws,
            actor=user,
            goal=goal_emergency,
            kind="earmark",
            amount="1420.00",
            account_id=str(reserve_vault.id),
            occurred_on=clamp_date(15),
            note="Bonus allocation",
        )

        goal_japan = create_savings_goal(
            workspace=ws,
            actor=user,
            name="Japan Autumn Trip",
            target_amount="3850.00",
            currency="USD",
            target_date=today + timedelta(days=150),
            linked_account_id=str(aba_checking.id),
            strategy="earmark",
            notes="Flights, JR Pass, and Kyoto ryokan",
        )
        for d_ago, amt, note in [
            (72, "415.00", "Month 1 travel set-aside"),
            (40, "380.00", "Month 2 travel set-aside"),
            (10, "525.00", "Consulting split allocation"),
        ]:
            record_savings_contribution(
                workspace=ws,
                actor=user,
                goal=goal_japan,
                kind="earmark",
                amount=amt,
                account_id=str(aba_checking.id),
                occurred_on=clamp_date(d_ago),
                note=note,
            )

        goal_kny = create_savings_goal(
            workspace=ws,
            actor=user,
            name="Khmer New Year Family Fund",
            target_amount="6000000.00",
            currency="KHR",
            target_date=today + timedelta(days=140),
            linked_account_id=str(wing_khr.id),
            strategy="earmark",
            notes="Family celebration & travel fund in Riel",
        )
        record_savings_contribution(
            workspace=ws,
            actor=user,
            goal=goal_kny,
            kind="earmark",
            amount="1250000.00",
            account_id=str(wing_khr.id),
            occurred_on=clamp_date(50),
            note="Retainer earmark #1",
        )
        record_savings_contribution(
            workspace=ws,
            actor=user,
            goal=goal_kny,
            kind="earmark",
            amount="980000.00",
            account_id=str(wing_khr.id),
            occurred_on=clamp_date(18),
            note="Retainer earmark #2",
        )

        # 8. Debts / Liabilities & Repayments (USD & KHR)
        laptop_loan = create_liability(
            workspace=ws,
            actor=user,
            name="Workstation Hardware Loan",
            original_principal="2400.00",
            currency="USD",
            liability_type="personal_loan",
            interest_rate="6.50",
            interest_type="simple",
            lender="ABA Device Plan",
            due_day=15,
            next_due_date=today + timedelta(days=12),
            linked_account_id=str(aba_checking.id),
            disbursement_date=opened_on + timedelta(days=5),
            notes="12-month studio MacBook Pro hardware plan",
        )
        for d_ago, p_amt, i_amt, note in [
            (120, "245.00", "13.00", "Installment #1"),
            (90, "265.00", "11.65", "Installment #2"),
            (60, "280.00", "10.20", "Installment #3"),
            (28, "295.00", "8.70", "Installment #4"),
        ]:
            record_debt_repayment(
                workspace=ws,
                actor=user,
                liability=laptop_loan,
                paying_account_id=str(aba_checking.id),
                principal_amount=p_amt,
                interest_amount=i_amt,
                paid_on=clamp_date(d_ago),
                note=note,
            )

        moto_loan = create_liability(
            workspace=ws,
            actor=user,
            name="Honda Scoopy Commuter Financing",
            original_principal="4800000.00",
            currency="KHR",
            liability_type="personal_loan",
            interest_rate="8.00",
            interest_type="simple",
            lender="AEON Specialized Bank",
            due_day=20,
            next_due_date=today + timedelta(days=17),
            linked_account_id=str(wing_khr.id),
            disbursement_date=opened_on + timedelta(days=10),
            notes="Local KHR commuter motorcycle installment",
        )
        for d_ago, p_amt, i_amt, note in [
            (100, "480000.00", "32000.00", "KHR payment #1"),
            (68, "520000.00", "28800.00", "KHR payment #2"),
            (34, "540000.00", "25300.00", "KHR payment #3"),
        ]:
            record_debt_repayment(
                workspace=ws,
                actor=user,
                liability=moto_loan,
                paying_account_id=str(wing_khr.id),
                principal_amount=p_amt,
                interest_amount=i_amt,
                paid_on=clamp_date(d_ago),
                note=note,
            )

        # 9. Emergency Fund Configuration & Upcoming Reserved Obligations
        update_emergency_fund_config(
            workspace=ws,
            target_months=6,
            designated_account_id=str(reserve_vault.id),
        )

        RecurringObligation.objects.create(
            workspace=ws,
            name="BKK1 Apartment Rent",
            kind=ObligationKind.BILL,
            amount_minor=Money.parse("740.00", "USD", 2).amount_minor,
            currency_code="USD",
            account=aba_checking,
            category=cat_housing,
            cadence=ObligationCadence.MONTHLY,
            next_due_date=today + timedelta(days=8),
            is_reserved=True,
        )
        RecurringObligation.objects.create(
            workspace=ws,
            name="Ezecom Fiber & EDC Utility",
            kind=ObligationKind.BILL,
            amount_minor=Money.parse("72.50", "USD", 2).amount_minor,
            currency_code="USD",
            account=aba_checking,
            category=cat_utilities,
            cadence=ObligationCadence.MONTHLY,
            next_due_date=today + timedelta(days=15),
            is_reserved=True,
        )
        RecurringObligation.objects.create(
            workspace=ws,
            name="AEON Scoopy Monthly Payment",
            kind=ObligationKind.RESERVED,
            amount_minor=Money.parse("565000.00", "KHR", 2).amount_minor,
            currency_code="KHR",
            account=wing_khr,
            cadence=ObligationCadence.MONTHLY,
            next_due_date=today + timedelta(days=17),
            is_reserved=True,
        )

        # 10. Precompute Historical Net Worth Snapshots (USD + KHR)
        ws.refresh_from_db()
        snapshot_dates = sorted(
            {_add_months_end(today, -m) for m in range(1, 6)} | {today}
        )
        for snap_date in snapshot_dates:
            get_or_create_snapshot(ws, as_of=snap_date, currency_code="USD")
            get_or_create_snapshot(ws, as_of=snap_date, currency_code="KHR")

        # 11. Strict Double-Entry Reconciliation Check
        recon = reconcile_workspace(workspace=ws)
        if not recon.is_valid:
            self.stderr.write(
                self.style.ERROR(f"Reconciliation failure: {'; '.join(recon.errors)}")
            )
            raise SystemExit(1)

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded rich USD + KHR demo workspace for {user.email} "
                f"(ledger_seq={ws.ledger_seq}, 0 drift)."
            )
        )
