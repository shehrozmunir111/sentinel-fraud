import pytest


# ──────────────────────────── GET /health ────────────────────────────

@pytest.mark.asyncio
async def test_health_check(client):
    """Health endpoint should return status healthy."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "environment" in data


# ──────────────────────────── GET / (root) ────────────────────────────

@pytest.mark.asyncio
async def test_root_endpoint(client):
    """Root endpoint should return project info and capabilities."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert data["status"] == "operational"
    assert "capabilities" in data
    assert isinstance(data["capabilities"], list)
    assert "real_time_scoring" in data["capabilities"]
    assert "ml_detection" in data["capabilities"]
    assert "velocity_checks" in data["capabilities"]
