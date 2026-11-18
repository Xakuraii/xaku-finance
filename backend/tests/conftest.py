"""Shared test fixtures."""

import pytest


@pytest.fixture(autouse=True)
def _clear_throttle_cache():
    """Throttle counters live in the process-wide cache; every test starts clean."""
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def _ensure_currencies(db):
    """Ensure seed currencies exist even when transaction=True truncates tables."""
    from apps.common.models import Currency

    Currency.objects.get_or_create(
        code="USD",
        defaults={
            "name": "United States Dollar",
            "symbol": "$",
            "minor_unit": 2,
            "is_active": True,
        },
    )
    Currency.objects.get_or_create(
        code="KHR",
        defaults={
            "name": "Cambodian Riel",
            "symbol": "៛",
            "minor_unit": 2,
            "is_active": True,
        },
    )


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def user(db):
    from tests.factories.users import UserFactory

    return UserFactory()
