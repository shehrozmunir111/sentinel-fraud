import pytest
from tests.conftest import register_and_login, auth_headers


# ──────────────────────────── POST /api/v1/auth/register ────────────────────────────

@pytest.mark.asyncio
async def test_register_user(client):
    """Successful registration should return 200 with user details."""
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
    assert "id" in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    """Registering the same email twice should return 400."""
    payload = {
        "email": "dup@example.com",
        "password": "testpass123",
        "country": "US"
    }
    resp1 = await client.post("/api/v1/auth/register", json=payload)
    assert resp1.status_code == 200

    resp2 = await client.post("/api/v1/auth/register", json=payload)
    assert resp2.status_code == 400
    assert "already registered" in resp2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_invalid_payload(client):
    """Missing required fields should return 422."""
    response = await client.post("/api/v1/auth/register", json={
        "email": "bad@example.com"
        # missing password
    })
    assert response.status_code == 422


# ──────────────────────────── POST /api/v1/auth/login ────────────────────────────

@pytest.mark.asyncio
async def test_login_success(client):
    """Login with valid credentials should return access_token."""
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
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    """Login with wrong password should return 401."""
    await client.post("/api/v1/auth/register", json={
        "email": "wrongpw@test.com",
        "password": "testpass123",
        "country": "US"
    })

    response = await client.post("/api/v1/auth/login", data={
        "username": "wrongpw@test.com",
        "password": "wrongpassword"
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client):
    """Login with email that doesn't exist should return 401."""
    response = await client.post("/api/v1/auth/login", data={
        "username": "ghost@test.com",
        "password": "testpass123"
    })
    assert response.status_code == 401


# ──────────────────────────── GET /api/v1/auth/me ────────────────────────────

@pytest.mark.asyncio
async def test_get_me_authenticated(client):
    """GET /me with valid token should return user profile."""
    user_id, token = await register_and_login(client, email="me@test.com")
    response = await client.get("/api/v1/auth/me", headers=auth_headers(token))
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@test.com"
    assert data["id"] == str(user_id) if isinstance(user_id, str) else user_id


@pytest.mark.asyncio
async def test_get_me_unauthenticated(client):
    """GET /me without token should return 401/403."""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code in (401, 403)