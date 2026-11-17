"""Factories for identity tests.

Creating a user through the service keeps profile, workspace, and layout consistent with what
registration produces. A factory that inserts rows directly would hide missing side effects.
"""

from __future__ import annotations

import factory

from apps.identity.models import User
from apps.identity.services.registration import register_user


class UserFactory(factory.Factory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    password = "correct horse battery staple"
    display_name = "Test User"
    timezone = "UTC"
    reporting_currency = "USD"

    @classmethod
    def _create(cls, model_class: type[User], **kwargs: object) -> User:
        return register_user(**kwargs)  # type: ignore[arg-type]
