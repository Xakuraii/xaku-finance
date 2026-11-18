"""Workspace-scoped querysets and managers.

Enforces that every financial query is scoped to an explicit workspace.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from django.db import models

if TYPE_CHECKING:
    from apps.workspaces.models import Workspace


class WorkspaceScopedQuerySet(models.QuerySet[Any]):
    """QuerySet providing explicit workspace scoping."""

    def for_workspace(self, workspace: Workspace | uuid.UUID | str) -> WorkspaceScopedQuerySet:
        workspace_id = getattr(workspace, "id", workspace)
        return self.filter(workspace_id=workspace_id)


class WorkspaceScopedManager(models.Manager[Any]):
    """Manager enforcing that financial records are queried for a specific workspace."""

    def get_queryset(self) -> WorkspaceScopedQuerySet:
        return WorkspaceScopedQuerySet(self.model, using=self._db)

    def for_workspace(self, workspace: Workspace | uuid.UUID | str) -> WorkspaceScopedQuerySet:
        return self.get_queryset().for_workspace(workspace)
