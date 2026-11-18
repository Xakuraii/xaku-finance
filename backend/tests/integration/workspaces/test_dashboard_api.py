
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.common.models import Currency
from apps.identity.models import User
from apps.workspaces.dashboard_registry import DEFAULT_WIDGET_ORDER
from apps.workspaces.models import Workspace


@pytest.fixture
def auth_client(db):
    user = User.objects.create_user(email="dashapi@example.com", password="password123456")
    ws = Workspace.objects.create(
        owner=user,
        name="Personal",
        reporting_currency=Currency.objects.get(code="USD"),
        timezone="UTC",
    )
    user.workspace = ws

    client = APIClient()
    client.force_authenticate(user=user)
    return client, user, ws


def test_get_dashboard_unauthenticated():
    client = APIClient()
    response = client.get("/api/v1/dashboard/")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_dashboard_authenticated(auth_client):
    client, user, ws = auth_client
    response = client.get("/api/v1/dashboard/")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert "period" in data
    assert "widget_order" in data
    assert data["widget_order"] == DEFAULT_WIDGET_ORDER
    assert "balances" in data
    assert "converted_total" in data


def test_get_dashboard_custom_period(auth_client):
    client, user, ws = auth_client
    response = client.get(
        "/api/v1/dashboard/",
        {"period": "custom", "start": "2026-11-01", "end": "2026-11-15"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["period"]["start"] == "2026-11-01"
    assert data["period"]["end"] == "2026-11-15"


def test_get_and_put_dashboard_layout(auth_client):
    client, user, ws = auth_client
    # GET layout
    get_res = client.get("/api/v1/dashboard/layout/")
    assert get_res.status_code == status.HTTP_200_OK
    assert len(get_res.json()["widgets"]) == len(DEFAULT_WIDGET_ORDER)

    # PUT layout
    new_layout = [
        {"key": "net_worth", "enabled": True},
        {"key": "total_balance", "enabled": False},
    ]
    put_res = client.put("/api/v1/dashboard/layout/", {"widgets": new_layout}, format="json")
    assert put_res.status_code == status.HTTP_200_OK
    widgets = put_res.json()["widgets"]
    assert len(widgets) == 2
    assert widgets[0]["key"] == "net_worth"
    assert widgets[1]["enabled"] is False

    # Verify dashboard reflects new layout
    dash_res = client.get("/api/v1/dashboard/")
    assert dash_res.status_code == status.HTTP_200_OK
    assert dash_res.json()["widget_order"] == ["net_worth"]  # Only enabled widgets in order

    # RESET layout
    reset_res = client.post("/api/v1/dashboard/layout/reset/")
    assert reset_res.status_code == status.HTTP_200_OK
    assert len(reset_res.json()["widgets"]) == len(DEFAULT_WIDGET_ORDER)
