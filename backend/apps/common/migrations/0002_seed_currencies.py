"""Seed the currencies V1 supports. USD and KHR both use 2 decimal places for uniformity."""

from __future__ import annotations

from django.db import migrations


def seed_currencies(apps, schema_editor):  # type: ignore[no-untyped-def]
    currency = apps.get_model("common", "Currency")
    rows = [
        {"code": "USD", "name": "US Dollar", "symbol": "$", "minor_unit": 2, "is_active": True},
        {"code": "KHR", "name": "Cambodian Riel", "symbol": "៛", "minor_unit": 2, "is_active": True},
    ]
    for row in rows:
        currency.objects.update_or_create(code=row["code"], defaults=row)


def unseed_currencies(apps, schema_editor):  # type: ignore[no-untyped-def]
    currency = apps.get_model("common", "Currency")
    currency.objects.filter(code__in=["USD", "KHR"]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("common", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_currencies, unseed_currencies),
    ]
