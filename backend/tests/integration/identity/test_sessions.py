import uuid
from datetime import timedelta

import pytest
from django.utils import timezone
from freezegun import freeze_time

from apps.identity.api.cookies import REFRESH_COOKIE
from apps.identity.models import UserSession
from tests.factories.users import UserFactory

PASSWORD = "correct horse battery staple"


def login(api, email: str, password: str = PASSWORD):
    return api.post(
        "/api/v1/auth/login/",
        {"email": email, "password": password},
        format="json",
    )


def authenticate(api, access: str) -> None:
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")


@pytest.fixture
def logged_in(api_client):
    user = UserFactory()
    response = login(api_client, user.email)
    assert response.status_code == 200
    return user, response.json()


@pytest.mark.django_db
def test_login_sets_secure_refresh_cookie(api_client, user) -> None:
    response = login(api_client, user.email)
    assert response.status_code == 200
    body = response.json()
    assert body["access"]
    assert body["access_expires_in"] == 900
    assert body["refresh_expires_in"] == 604800
    assert REFRESH_COOKIE in response.cookies

    cookie = response.cookies[REFRESH_COOKIE]
    assert cookie["httponly"] is True
    assert cookie["secure"] is True
    assert cookie["samesite"] == "Lax"
    assert cookie["path"] == "/api/v1/auth/"
    assert api_client.cookies[REFRESH_COOKIE].value


@pytest.mark.django_db
def test_login_failure_is_generic_for_unknown_and_wrong_password(api_client, user) -> None:
    wrong = login(api_client, user.email, "not the right password")
    unknown = login(api_client, "nobody@example.com", "not the right password")
    assert wrong.status_code == 401
    assert unknown.status_code == 401
    assert wrong.json()["error"]["code"] == "invalid_credentials"
    assert wrong.json()["error"]["message"] == unknown.json()["error"]["message"]


@pytest.mark.django_db
def test_refresh_rotates_and_issues_new_jti(api_client, user) -> None:
    assert login(api_client, user.email).status_code == 200
    old = api_client.cookies[REFRESH_COOKIE].value
    session = UserSession.objects.get(user=user)
    old_jti = session.refresh_jti

    response = api_client.post("/api/v1/auth/refresh/")
    assert response.status_code == 200
    assert response.json()["access"]
    new = response.cookies[REFRESH_COOKIE].value
    assert new != old

    session.refresh_from_db()
    assert session.refresh_jti != old_jti


@pytest.mark.django_db
def test_refresh_without_cookie_is_401(api_client) -> None:
    response = api_client.post("/api/v1/auth/refresh/")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"


@pytest.mark.django_db
def test_refresh_reuse_revokes_family(api_client, user) -> None:
    assert login(api_client, user.email).status_code == 200
    old = api_client.cookies[REFRESH_COOKIE].value

    first = api_client.post("/api/v1/auth/refresh/")
    assert first.status_code == 200

    api_client.cookies[REFRESH_COOKIE] = old
    second = api_client.post("/api/v1/auth/refresh/")
    assert second.status_code == 401
    assert not UserSession.objects.filter(user=user, revoked_at__isnull=True).exists()
    assert UserSession.objects.filter(user=user, revoked_reason="refresh_reuse").exists()


@pytest.mark.django_db
def test_logout_revokes_session_and_clears_cookie(api_client, logged_in) -> None:
    user, body = logged_in
    authenticate(api_client, body["access"])

    response = api_client.post("/api/v1/auth/logout/")
    assert response.status_code == 204
    assert response.cookies[REFRESH_COOKIE].value == ""
    assert not UserSession.objects.filter(user=user, revoked_at__isnull=True).exists()

    api_client.credentials()
    assert api_client.post("/api/v1/auth/refresh/").status_code == 401


@pytest.mark.django_db
def test_sessions_list_marks_current_and_hides_revoked(api_client, user) -> None:
    first = login(api_client, user.email).json()
    authenticate(api_client, first["access"])
    second = login(api_client, user.email).json()
    authenticate(api_client, second["access"])

    response = api_client.get("/api/v1/auth/sessions/")
    assert response.status_code == 200
    sessions = response.json()
    assert len(sessions) == 2
    assert sum(1 for session in sessions if session["current"]) == 1
    assert all(session["device"] for session in sessions)
    assert all("ip_hash" not in session for session in sessions)

    current = next(session for session in sessions if session["current"])
    revoked = api_client.delete(f"/api/v1/auth/sessions/{current['id']}/")
    assert revoked.status_code == 204
    remaining = api_client.get("/api/v1/auth/sessions/").json()
    assert len(remaining) == 1


@pytest.mark.django_db
def test_cannot_revoke_another_users_session(api_client, user) -> None:
    body = login(api_client, user.email).json()

    other = UserFactory()
    login(api_client, other.email)
    other_session = UserSession.objects.get(user=other)

    authenticate(api_client, body["access"])
    response = api_client.delete(f"/api/v1/auth/sessions/{other_session.id}/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_logout_all_revokes_every_session(api_client, user) -> None:
    login(api_client, user.email)
    second = login(api_client, user.email).json()
    authenticate(api_client, second["access"])

    response = api_client.post("/api/v1/auth/logout-all/")
    assert response.status_code == 200
    assert response.json() == {"revoked": 2}
    assert not UserSession.objects.filter(user=user, revoked_at__isnull=True).exists()


@pytest.mark.django_db
def test_unknown_session_id_is_404(api_client, logged_in) -> None:
    _user, body = logged_in
    authenticate(api_client, body["access"])
    response = api_client.delete(f"/api/v1/auth/sessions/{uuid.uuid4()}/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_progressive_lockout_blocks_and_then_expires(api_client, user) -> None:
    for _ in range(5):
        assert login(api_client, user.email, "wrong password").status_code == 401

    user.refresh_from_db()
    assert user.failed_login_count == 5
    assert user.locked_until is not None

    assert login(api_client, user.email).status_code == 401

    with freeze_time(timezone.now() + timedelta(minutes=2)):
        response = login(api_client, user.email)
        assert response.status_code == 200

    user.refresh_from_db()
    assert user.failed_login_count == 0
    assert user.locked_until is None
