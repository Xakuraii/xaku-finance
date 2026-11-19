"""Integration tests for account deletion requests, grace period, and cancellation."""


import pytest

from apps.identity.models import User, UserSession
from apps.identity.services import two_factor
from apps.identity.services.sessions import RequestMeta, issue_tokens
from apps.privacy.models import AccountDeletionRequest, DeletionRequestStatus
from apps.privacy.services.deletion import execute_deletion, request_account_deletion
from apps.workspaces.models import Workspace

PASSWORD = "correct horse battery staple"


@pytest.fixture
def enrolled_user(user):
    two_factor.begin_enrollment(user)
    import hashlib

    import pyotp

    secret = two_factor._decrypt_secret(user.two_factor)
    totp = pyotp.TOTP(secret, digits=6, interval=30, digest=hashlib.sha1)
    code = totp.now()
    two_factor.confirm_enrollment(user, code)
    return user


@pytest.mark.django_db
def test_deletion_request_requires_delete_confirmation(api_client, user) -> None:
    tokens = issue_tokens(user, request_meta=RequestMeta())
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens.access}")

    res = api_client.post(
        "/api/v1/privacy/deletion-requests/",
        {"password": PASSWORD, "confirm": "NOPE"},
        format="json",
    )
    assert res.status_code == 400
    assert "DELETE" in str(res.json())


@pytest.mark.django_db
def test_deletion_request_requires_valid_password(api_client, user) -> None:
    tokens = issue_tokens(user, request_meta=RequestMeta())
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens.access}")

    res = api_client.post(
        "/api/v1/privacy/deletion-requests/",
        {"password": "wrong-password", "confirm": "DELETE"},
        format="json",
    )
    assert res.status_code == 401


@pytest.mark.django_db
def test_deletion_request_workflow_and_cancellation(api_client, user) -> None:
    # Open 2 sessions
    meta1 = RequestMeta(user_agent="Browser 1")
    tokens1 = issue_tokens(user, request_meta=meta1)
    meta2 = RequestMeta(user_agent="Browser 2")
    tokens2 = issue_tokens(user, request_meta=meta2)

    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens1.access}")

    res = api_client.post(
        "/api/v1/privacy/deletion-requests/",
        {"password": PASSWORD, "confirm": "DELETE"},
        format="json",
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "requested"
    assert "consequences" in data
    assert len(data["consequences"]) >= 1

    # Check status endpoint
    current_res = api_client.get("/api/v1/privacy/deletion-requests/current/")
    assert current_res.status_code == 200
    assert current_res.json()["status"] == "requested"

    # Other session was revoked
    session2 = UserSession.objects.get(id=tokens2.session_id)
    assert session2.revoked_at is not None
    assert session2.revoked_reason == "account_deletion_requested"

    # Current session remains active
    session1 = UserSession.objects.get(id=tokens1.session_id)
    assert session1.revoked_at is None

    # Cancel during grace period
    cancel_res = api_client.delete("/api/v1/privacy/deletion-requests/current/")
    assert cancel_res.status_code == 204

    # Current request is now none (or cancelled)
    check_cancelled = api_client.get("/api/v1/privacy/deletion-requests/current/")
    assert check_cancelled.status_code == 404

    req = AccountDeletionRequest.objects.filter(user=user).first()
    assert req.status == DeletionRequestStatus.CANCELLED
    assert req.cancelled_at is not None


@pytest.mark.django_db
def test_execute_deletion_removes_data(user) -> None:
    ws = user.workspace
    user_id = user.id
    ws_id = ws.id

    req = request_account_deletion(
        user=user,
        password=PASSWORD,
        confirm_text="DELETE",
    )

    execute_deletion(req)

    req.refresh_from_db()
    assert req.status == DeletionRequestStatus.EXECUTED
    assert req.executed_at is not None

    # User is deactivated and anonymized
    u = User.objects.get(id=user_id)
    assert u.is_active is False
    assert "@deleted.local" in u.email
    assert not Workspace.objects.filter(id=ws_id).exists()
