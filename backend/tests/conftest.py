"""Shared test fixtures."""

import pytest


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def user(db):
    from tests.factories.users import UserFactory

    return UserFactory()
