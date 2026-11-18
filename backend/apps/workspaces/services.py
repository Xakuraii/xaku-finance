"""Transactional workspace provisioning."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import transaction

from apps.common.models import Currency
from apps.workspaces.models import Workspace

if TYPE_CHECKING:
    from apps.identity.models import User


@transaction.atomic
def ensure_workspace(user: User) -> Workspace:
    """Return the user's single workspace, creating it from their profile if missing.

    Registration creates the workspace in the same transaction as the user. This helper exists for
    repair and for tests; it never creates a second workspace because ``owner`` is unique.
    """
    profile = getattr(user, "profile", None)
    currency = (
        profile.reporting_currency if profile is not None else Currency.objects.get(code="USD")
    )
    workspace, _created = Workspace.objects.get_or_create(
        owner=user,
        defaults={
            "name": "Personal",
            "reporting_currency": currency,
            "timezone": profile.timezone if profile is not None else "UTC",
            "week_start": profile.week_start if profile is not None else 1,
        },
    )
    return workspace
