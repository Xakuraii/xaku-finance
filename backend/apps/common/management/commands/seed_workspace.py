"""Management command to seed a workspace with realistic accounts and transactions."""

from __future__ import annotations

import random
from datetime import date, timedelta
from typing import Any

from django.core.management.base import BaseCommand

from apps.accounts.models import AccountType
from apps.accounts.services import create_account
from apps.categories.models import Category, CategoryKind
from apps.identity.models import User
from apps.ledger.services.reconciliation import reconcile_workspace
from apps.transactions.services.create import create_transaction
from apps.workspaces.services import ensure_workspace


class Command(BaseCommand):
    help = (
        "Seed a test or demo workspace with accounts, categories, and service-layer transactions."
    )

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--email", type=str, default="demo@xakufinance.local")
        parser.add_argument("--password", type=str, default="DemoPass123456!")
        parser.add_argument("--count", type=int, default=30)

    def handle(self, *args: Any, **options: Any) -> None:
        email = options["email"]
        password = options["password"]
        count = options["count"]

        from apps.common.models import Currency

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
            self.stdout.write(self.style.SUCCESS(f"Created user {email}"))

        ws = ensure_workspace(user=user)

        # Create demo accounts if none exist
        checking = create_account(
            workspace=ws,
            actor=user,
            name="Primary Checking",
            account_type=str(AccountType.CHECKING[0]),
            currency="USD",
            opening_balance="3500.00",
            opening_balance_date=date(2026, 11, 1),
            is_spendable=True,
            description="Main day-to-day spending and salary deposit account",
        )
        create_account(
            workspace=ws,
            actor=user,
            name="Emergency Fund",
            account_type=str(AccountType.SAVINGS[0]),
            currency="USD",
            opening_balance="10000.00",
            opening_balance_date=date(2026, 11, 1),
            is_spendable=False,
            description="High-yield savings buffer",
        )
        cash = create_account(
            workspace=ws,
            actor=user,
            name="Physical Wallet",
            account_type=str(AccountType.CASH[0]),
            currency="USD",
            opening_balance="200.00",
            opening_balance_date=date(2026, 11, 1),
            is_spendable=True,
        )

        categories_data = [
            ("Groceries", CategoryKind.EXPENSE),
            ("Dining & Cafes", CategoryKind.EXPENSE),
            ("Housing & Rent", CategoryKind.EXPENSE),
            ("Utilities", CategoryKind.EXPENSE),
            ("Transportation", CategoryKind.EXPENSE),
            ("Salary", CategoryKind.INCOME),
            ("Freelance", CategoryKind.INCOME),
        ]
        categories = {}
        for name, kind in categories_data:
            cat, _ = Category.objects.get_or_create(
                workspace=ws, name=name, defaults={"kind": kind}
            )
            categories[name] = cat

        merchants = ["Whole Foods", "Local Cafe", "Shell Oil", "Electric Utility", "Corner Market"]
        today = date.today()

        self.stdout.write(f"Generating {count} transactions through service layer...")
        for i in range(count):
            days_ago = random.randint(0, 30)
            tx_date = today - timedelta(days=days_ago)
            amount_dollars = random.randint(5, 120)
            amount_str = f"{amount_dollars}.50"

            cat_name = random.choice(["Groceries", "Dining & Cafes", "Utilities", "Transportation"])
            acc = random.choice([checking, cash])

            create_transaction(
                workspace=ws,
                actor=user,
                kind="expense",
                account_id=acc.id,
                amount=amount_str,
                currency="USD",
                occurred_on=tx_date,
                title=f"{cat_name} payment #{i + 1}",
                category_id=categories[cat_name].id,
                merchant=random.choice(merchants),
            )

        # Run reconciliation
        reconciled = reconcile_workspace(workspace=ws)
        if reconciled:
            self.stdout.write(
                self.style.SUCCESS("All ledger entries balance! Drift: 0 minor units.")
            )
        else:
            self.stdout.write(self.style.ERROR("Reconciliation detected drift in ledger!"))

        self.stdout.write(self.style.SUCCESS(f"Seeding completed successfully for {email}."))
