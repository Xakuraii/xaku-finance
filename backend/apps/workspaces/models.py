"""Workspaces: one financial boundary per user in V1."""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.common.validators import validate_iana_timezone


class Workspace(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="workspace",
    )
    name = models.CharField(max_length=80)
    reporting_currency = models.ForeignKey(
        "common.Currency",
        on_delete=models.PROTECT,
        related_name="+",
        db_column="reporting_currency_code",
    )
    timezone = models.CharField(
        max_length=64,
        default="UTC",
        validators=[validate_iana_timezone],
    )
    week_start = models.SmallIntegerField(default=1)
    #: Monotonic sequence bumped by the ledger on every posted entry. Snapshots pin it.
    ledger_seq = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "workspace"
        constraints = [
            models.CheckConstraint(
                condition=Q(week_start__gte=1) & Q(week_start__lte=7),
                name="workspace_week_start_ck",
            ),
            models.CheckConstraint(
                condition=~Q(name=""),
                name="workspace_name_not_blank_ck",
            ),
        ]

    def __str__(self) -> str:
        return self.name
