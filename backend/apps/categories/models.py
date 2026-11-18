"""Category model: income and expense categories."""

from __future__ import annotations

from django.db import models
from django.db.models import CheckConstraint, F, Q, UniqueConstraint
from django.db.models.functions import Lower

from apps.common.models import ArchivedModel, WorkspaceScopedModel


class CategoryKind(models.TextChoices):
    EXPENSE = "expense", "Expense"
    INCOME = "income", "Income"


class Category(WorkspaceScopedModel, ArchivedModel):
    name = models.CharField(max_length=80)
    kind = models.CharField(max_length=8, choices=CategoryKind.choices)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="children",
    )
    icon = models.CharField(max_length=40, null=True, blank=True)
    color = models.CharField(max_length=7, null=True, blank=True)
    is_system = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = "category"
        ordering = ["sort_order", "name"]
        constraints = [
            UniqueConstraint(
                "workspace",
                "kind",
                Lower("name"),
                "parent",
                name="category_ws_kind_name_parent_uq",
            ),
            CheckConstraint(
                condition=Q(kind__in=CategoryKind.values),
                name="category_kind_ck",
            ),
            CheckConstraint(
                condition=Q(parent__isnull=True) | ~Q(parent=F("id")),
                name="category_parent_not_self_ck",
            ),
        ]
        indexes = [
            models.Index(
                fields=["workspace", "kind", "is_archived", "sort_order"],
                name="category_ws_kind_arch_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.kind})"
