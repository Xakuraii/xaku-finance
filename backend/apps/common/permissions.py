"""Workspace permissions for API endpoints."""

from __future__ import annotations

from typing import Any

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView


class IsWorkspaceMember(BasePermission):
    """Verifies that the requested object belongs to the authenticated user's workspace."""

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False

        user_workspace = getattr(user, "workspace", None)
        if user_workspace is None:
            return False

        user_workspace_id = user_workspace.id
        obj_workspace_id = getattr(obj, "workspace_id", None)
        if obj_workspace_id is None and hasattr(obj, "workspace"):
            obj_workspace_id = getattr(obj.workspace, "id", None)

        return obj_workspace_id is not None and obj_workspace_id == user_workspace_id
