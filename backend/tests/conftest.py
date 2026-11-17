"""Shared test fixtures."""

import pytest


@pytest.fixture(autouse=True)
def _clear_throttle_cache():
    """Throttle counters live in the process-wide cache; every test starts clean."""
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def user(db):
    from tests.factories.users import UserFactory

    return UserFactory()
