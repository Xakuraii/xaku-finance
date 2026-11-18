"""Workspace factory for tests."""

from __future__ import annotations

import factory

from apps.workspaces.models import Workspace
from tests.factories.users import UserFactory


class WorkspaceFactory(factory.Factory):
    class Meta:
        model = Workspace

    @classmethod
    def _create(cls, model_class: type[Workspace], **kwargs: object) -> Workspace:
        user = UserFactory()
        return user.workspace
