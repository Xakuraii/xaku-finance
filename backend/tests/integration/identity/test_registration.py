import pytest

from apps.identity.models import DashboardLayout, User, UserProfile
from apps.identity.services.registration import EmailTaken, register_user
from apps.workspaces.models import Workspace

PASSWORD = "correct horse battery staple"


@pytest.mark.django_db
def test_registration_creates_user_profile_and_workspace() -> None:
    user = register_user(
        email="mara@example.com",
        password=PASSWORD,
        display_name="Mara",
        timezone="Asia/Phnom_Penh",
    )
    assert user.workspace.owner_id == user.id
    assert user.profile.reporting_currency.code == "USD"
    assert user.workspace.reporting_currency.code == "USD"
    assert user.workspace.timezone == "Asia/Phnom_Penh"
    assert user.profile.timezone == "Asia/Phnom_Penh"
    assert DashboardLayout.objects.filter(user=user).exists()


@pytest.mark.django_db
def test_registration_normalizes_email_and_hashes_password() -> None:
    user = register_user(
        email="  Mara@Example.COM ", password=PASSWORD, display_name="  Mara  "
    )
    assert user.email == "mara@example.com"
    assert user.profile.display_name == "Mara"
    assert user.password != PASSWORD
    assert user.check_password(PASSWORD)
    assert user.password_changed_at is not None


@pytest.mark.django_db
def test_duplicate_email_rejected_case_insensitively() -> None:
    register_user(email="mara@example.com", password=PASSWORD, display_name="Mara")
    with pytest.raises(EmailTaken):
        register_user(
            email="MARA@example.com", password=PASSWORD, display_name="Mara 2"
        )


@pytest.mark.django_db
def test_failed_registration_leaves_no_partial_rows() -> None:
    register_user(email="mara@example.com", password=PASSWORD, display_name="Mara")
    with pytest.raises(EmailTaken):
        register_user(
            email="mara@example.com", password=PASSWORD, display_name="Duplicate"
        )
    assert User.objects.count() == 1
    assert UserProfile.objects.count() == 1
    assert Workspace.objects.count() == 1


@pytest.mark.django_db
def test_weak_password_rejected() -> None:
    from apps.identity.services.registration import WeakPassword

    with pytest.raises(WeakPassword):
        register_user(email="mara@example.com", password="short", display_name="Mara")
    assert not User.objects.exists()


@pytest.mark.django_db
def test_unknown_timezone_rejected() -> None:
    from apps.identity.services.registration import InvalidTimezone

    with pytest.raises(InvalidTimezone):
        register_user(
            email="mara@example.com",
            password=PASSWORD,
            display_name="Mara",
            timezone="Mars/Olympus_Mons",
        )
    assert not User.objects.exists()


@pytest.mark.django_db
def test_unsupported_currency_rejected() -> None:
    from apps.identity.services.registration import UnsupportedCurrency

    with pytest.raises(UnsupportedCurrency):
        register_user(
            email="mara@example.com",
            password=PASSWORD,
            display_name="Mara",
            reporting_currency="XYZ",
        )
    assert not User.objects.exists()


@pytest.mark.django_db
def test_registration_api_returns_user_and_workspace(api_client) -> None:
    response = api_client.post(
        "/api/v1/auth/register/",
        {
            "email": "mara@example.com",
            "password": PASSWORD,
            "display_name": "Mara",
            "timezone": "Asia/Phnom_Penh",
        },
        format="json",
    )
    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == "mara@example.com"
    assert body["user"]["is_email_verified"] is False
    assert body["workspace"]["reporting_currency"] == "USD"
    assert body["workspace"]["timezone"] == "Asia/Phnom_Penh"
    assert body["access"]
    assert "refresh" in response.cookies
    assert "password" not in body["user"]


@pytest.mark.django_db
def test_registration_api_duplicate_email_is_a_field_error(api_client) -> None:
    payload = {
        "email": "mara@example.com",
        "password": PASSWORD,
        "display_name": "Mara",
    }
    assert api_client.post("/api/v1/auth/register/", payload, format="json").status_code == 201
    response = api_client.post(
        "/api/v1/auth/register/",
        {**payload, "email": "MARA@example.com"},
        format="json",
    )
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "email_taken"
    assert error["field"] == "email"
    assert response["X-Request-ID"].startswith("req_")


@pytest.mark.django_db
def test_registration_api_rejects_unknown_timezone(api_client) -> None:
    response = api_client.post(
        "/api/v1/auth/register/",
        {
            "email": "mara@example.com",
            "password": PASSWORD,
            "display_name": "Mara",
            "timezone": "Nowhere/Land",
        },
        format="json",
    )
    assert response.status_code == 400
    assert response.json()["error"]["field"] == "timezone"
    assert not User.objects.exists()
