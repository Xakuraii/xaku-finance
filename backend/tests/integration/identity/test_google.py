"""Google sign-in: ID-token verification, explicit linking, and account creation."""

import pytest
from django.contrib.auth import get_user_model

from apps.identity.api.cookies import REFRESH_COOKIE
from apps.identity.models import SocialIdentity
from apps.identity.services.google import (
    GoogleEmailUnverified,
    GoogleInvalidToken,
    GoogleLinkRequired,
    GoogleNotConfigured,
    _verify_id_token,
    login_with_google,
)
from apps.workspaces.models import Workspace
from tests.factories.users import UserFactory

CLAIMS = {
    "sub": "google-subject-1",
    "email": "mara@example.com",
    "email_verified": True,
    "name": "Mara Sok",
    "iss": "https://accounts.google.com",
}


@pytest.fixture
def google_claims(monkeypatch):
    def _set(claims: dict[str, object]) -> None:
        monkeypatch.setattr(
            "apps.identity.services.google._verify_id_token", lambda _raw: claims
        )

    return _set


@pytest.mark.django_db
def test_google_creates_a_verified_account(google_claims) -> None:
    google_claims(CLAIMS)

    user = login_with_google("fake-id-token")

    assert user.email == "mara@example.com"
    assert user.is_email_verified is True
    assert user.has_usable_password() is False
    assert user.profile.display_name == "Mara Sok"
    assert Workspace.objects.filter(owner=user).exists()
    identity = SocialIdentity.objects.get(user=user)
    assert identity.provider == "google"
    assert identity.subject == "google-subject-1"


@pytest.mark.django_db
def test_google_login_is_idempotent(google_claims) -> None:
    google_claims(CLAIMS)
    first = login_with_google("fake-id-token")
    second = login_with_google("fake-id-token")

    assert first.id == second.id
    assert SocialIdentity.objects.filter(user=first).count() == 1
    assert get_user_model().objects.count() == 1


@pytest.mark.django_db
def test_google_does_not_link_an_existing_password_account(google_claims) -> None:
    existing = UserFactory(email="mara@example.com")
    google_claims(CLAIMS)

    with pytest.raises(GoogleLinkRequired):
        login_with_google("fake-id-token")

    assert not SocialIdentity.objects.filter(user=existing).exists()


@pytest.mark.django_db
def test_google_requires_a_verified_email(google_claims) -> None:
    google_claims({**CLAIMS, "email_verified": False})

    with pytest.raises(GoogleEmailUnverified):
        login_with_google("fake-id-token")


@pytest.mark.django_db
def test_google_rejects_an_invalid_token(monkeypatch) -> None:
    def _raise(_raw: str) -> dict[str, object]:
        raise GoogleInvalidToken("The Google token is not valid.")

    monkeypatch.setattr("apps.identity.services.google._verify_id_token", _raise)

    with pytest.raises(GoogleInvalidToken):
        login_with_google("not-a-token")


def test_google_requires_a_client_id(settings) -> None:
    settings.GOOGLE_CLIENT_ID = ""
    with pytest.raises(GoogleNotConfigured):
        _verify_id_token("anything")


@pytest.mark.django_db
def test_google_api_returns_tokens_and_cookie(api_client, google_claims) -> None:
    google_claims(CLAIMS)

    response = api_client.post(
        "/api/v1/auth/google/", {"id_token": "fake-id-token"}, format="json"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access"]
    assert body["access_expires_in"] == 900
    assert REFRESH_COOKIE in response.cookies


@pytest.mark.django_db
def test_google_api_reports_link_required(api_client, google_claims) -> None:
    UserFactory(email="mara@example.com")
    google_claims(CLAIMS)

    response = api_client.post(
        "/api/v1/auth/google/", {"id_token": "fake-id-token"}, format="json"
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "google_link_required"


@pytest.mark.django_db
def test_google_api_reports_unverified_email(api_client, google_claims) -> None:
    google_claims({**CLAIMS, "email_verified": False})

    response = api_client.post(
        "/api/v1/auth/google/", {"id_token": "fake-id-token"}, format="json"
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "google_email_unverified"
