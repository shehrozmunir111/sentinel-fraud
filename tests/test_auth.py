import pytest

@pytest.mark.asyncio
async def test_register_user(client):
    response = await client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "testpass123",
        "phone": "+1234567890",
        "country": "US"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["role"] == "analyst"

@pytest.mark.asyncio
async def test_login(client):
    await client.post("/api/v1/auth/register", json={
        "email": "login@test.com",
        "password": "testpass123",
        "country": "US"
    })
    
    response = await client.post("/api/v1/auth/login", data={
        "username": "login@test.com",
        "password": "testpass123"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()