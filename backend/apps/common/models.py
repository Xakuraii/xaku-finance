"""Reference data shared by every domain.

Currencies are a database table, not a Python enum: enabling a new currency is data, not code.
"""

from __future__ import annotations

import uuid

from django.db import models
from django.db.models import Q

from apps.common.managers import WorkspaceScopedManager


class UuidModel(models.Model):
    """Abstract model providing a UUID primary key."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TimestampedModel(models.Model):
    """Abstract model providing creation and update timestamps in UTC."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ArchivedModel(models.Model):
    """Abstract model providing soft-archive capabilities."""

    is_archived = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True


class WorkspaceScopedModel(UuidModel, TimestampedModel):
    """Abstract base model for all workspace-owned entities."""

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)ss",
    )

    objects = WorkspaceScopedManager()

    class Meta:
        abstract = True


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
