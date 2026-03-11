"""
SentinelFraud Integration Tests
Tests for API endpoints with mocked dependencies
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


class TestHealthEndpoints:
    @pytest.mark.asyncio
    async def test_health_check(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        assert resp.json()["service"] == "sentinel-fraud"

    @pytest.mark.asyncio
    async def test_metrics_endpoint(self, client):
        with patch("app.main.websocket_manager") as mock_ws:
            mock_ws.connection_count.return_value = 0
            resp = await client.get("/metrics")
            assert resp.status_code == 200


class TestTransactionValidation:
    """Test Pydantic validation on transaction endpoint."""

    @pytest.mark.asyncio
    async def test_invalid_amount_rejected(self, client):
        """Amount must be > 0."""
        resp = await client.post(
            "/api/v1/transactions/",
            json={
                "transaction_id": "TX001",
                "card_id": "CARD001",
                "amount": -10.0,  # Invalid
                "currency": "USD",
            },
            headers={"Authorization": "Bearer fake_token"},
        )
        # 401 (no real token) or 422 (validation fails first)
        assert resp.status_code in (401, 422)

    @pytest.mark.asyncio
    async def test_missing_required_fields(self, client):
        resp = await client.post(
            "/api/v1/transactions/",
            json={"amount": 100.0},
            headers={"Authorization": "Bearer fake_token"},
        )
        assert resp.status_code in (401, 422)


class TestAuthEndpoints:
    @pytest.mark.asyncio
    async def test_login_with_invalid_creds(self, client):
        with patch("app.api.v1.auth.UserRepository") as MockRepo:
            mock_repo = MagicMock()
            mock_repo.get_by_email = AsyncMock(return_value=None)
            MockRepo.return_value = mock_repo

            resp = await client.post(
                "/api/v1/auth/login",
                json={"email": "bad@example.com", "password": "wrongpass"},
            )
            assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_protected_endpoint_requires_auth(self, client):
        resp = await client.get("/api/v1/transactions/")
        assert resp.status_code == 403  # No auth header


class TestPagination:
    @pytest.mark.asyncio
    async def test_page_size_validation(self, client):
        resp = await client.get(
            "/api/v1/transactions/?page_size=999",
            headers={"Authorization": "Bearer fake_token"},
        )
        # 422 (validation) or 401/403 (auth) - page_size=999 > 100 should fail
        assert resp.status_code in (401, 403, 422)
