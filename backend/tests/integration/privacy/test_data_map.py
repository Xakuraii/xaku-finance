"""Integration test for privacy data map transparency endpoint."""

import pytest

from apps.identity.services.sessions import RequestMeta, issue_tokens


@pytest.mark.django_db
def test_data_map_endpoint_returns_data_inventory(api_client, user) -> None:
    tokens = issue_tokens(user, request_meta=RequestMeta())
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens.access}")

    res = api_client.get("/api/v1/privacy/data-map/")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 5

    categories = [item["category"] for item in data]
    assert "Identity & Authentication" in categories
    assert "Financial Accounts & Balances" in categories
    assert "Encrypted Database Backups" in categories

    for item in data:
        assert item["purpose"]
        assert item["lawful_basis"]
        assert item["retention"]
        assert item["shared_with_third_parties"] is False
