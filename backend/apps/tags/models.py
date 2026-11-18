"""Tag model: labels for cross-cutting financial analysis."""

from __future__ import annotations

from django.db import models
from django.db.models import CheckConstraint, Q, UniqueConstraint
from django.db.models.functions import Lower

from apps.common.models import WorkspaceScopedModel


class Tag(WorkspaceScopedModel):
    name = models.CharField(max_length=40)
    color = models.CharField(max_length=7, null=True, blank=True)
    is_system = models.BooleanField(default=False)

    class Meta:
        db_table = "tag"
        ordering = ["name"]
        constraints = [
            UniqueConstraint(
                "workspace",
                Lower("name"),
                name="tag_workspace_lower_name_uq",
            ),
            CheckConstraint(
                condition=Q(name__regex=r"\S"),
                name="tag_name_not_blank_ck",
            ),
        ]

    def __str__(self) -> str:
        return self.name
