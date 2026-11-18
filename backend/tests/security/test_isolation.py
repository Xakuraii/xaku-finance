"""Security and isolation tests: verify workspace-level isolation."""

from __future__ import annotations

import pytest
from rest_framework.test import APIRequestFactory

from apps.common.permissions import IsWorkspaceMember
from tests.factories.users import UserFactory


@pytest.fixture
def other_user(db):
    return UserFactory(email="other_tenant@example.com")


def assert_isolated(client, user, other_user, url: str) -> None:
    """Helper to verify that user cannot access resources belonging to other_user."""
    client.force_authenticate(user=user)
    response = client.get(url)
    assert response.status_code in (404, 403), f"Expected 404 or 403, got {response.status_code}"


@pytest.mark.django_db
def test_is_workspace_member_permission_allows_own_workspace(user):
    factory = APIRequestFactory()
    request = factory.get("/")
    request.user = user

    permission = IsWorkspaceMember()

    class FakeResource:
        workspace_id = user.workspace.id

    assert permission.has_object_permission(request, None, FakeResource()) is True


@pytest.mark.django_db
def test_is_workspace_member_permission_denies_other_workspace(user, other_user):
    factory = APIRequestFactory()
    request = factory.get("/")
    request.user = user

    permission = IsWorkspaceMember()

    class FakeResource:
        workspace_id = other_user.workspace.id

    assert permission.has_object_permission(request, None, FakeResource()) is False


@pytest.mark.django_db
def test_is_workspace_member_denies_unauthenticated(user):
    factory = APIRequestFactory()
    request = factory.get("/")
    request.user = None

    permission = IsWorkspaceMember()

    class FakeResource:
        workspace_id = user.workspace.id

    assert permission.has_object_permission(request, None, FakeResource()) is False
