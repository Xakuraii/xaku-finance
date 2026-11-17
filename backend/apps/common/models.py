"""Reference data shared by every domain.

Currencies are a database table, not a Python enum: enabling a new currency is data, not code.
"""

from __future__ import annotations

from django.db import models
from django.db.models import Q


class Currency(models.Model):
    """ISO-4217 currency metadata, including the minor unit used by the Money object."""

    code = models.CharField(max_length=3, primary_key=True)
    name = models.CharField(max_length=64)
    symbol = models.CharField(max_length=8)
    minor_unit = models.SmallIntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "ref_currency"
        ordering = ["code"]
        verbose_name_plural = "currencies"
        constraints = [
            models.CheckConstraint(
                condition=Q(minor_unit__gte=0) & Q(minor_unit__lte=4),
                name="ref_currency_minor_unit_ck",
            ),
            models.CheckConstraint(
                condition=Q(code__regex=r"^[A-Z]{3}$"),
                name="ref_currency_code_ck",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.code} ({self.minor_unit} dp)"
