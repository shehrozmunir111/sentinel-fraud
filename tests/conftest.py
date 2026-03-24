import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import asyncio
import os
import sys

# Windows asyncio loop fix
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.main import app
from app.db.base import Base, engine, get_db
from app.core.config import settings
from app.core.security import create_access_token

# ─── Database ───
@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    """Wipe and recreate database tables once per session."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()

TestingSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

from sqlalchemy import text

@pytest_asyncio.fixture
async def db_session():
    """Yield a database session for a test. Clear tables after each test."""
    async with TestingSessionLocal() as session:
        yield session
        # No rollback needed after truncate, but good practice
        await session.rollback()
    
    # Wipe tables for next test
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE transactions, alerts, users, fraud_rules CASCADE;"))

@pytest_asyncio.fixture
async def client(db_session):
    """API client with DB override."""
    def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as ac:
        yield ac
    app.dependency_overrides.clear()

# ─── Redis Mock ───
from unittest.mock import AsyncMock, MagicMock
@pytest.fixture(autouse=True)
def mock_redis(monkeypatch):
    mock_redis_client = MagicMock()
    mock_pipeline = MagicMock()
    mock_pipeline.incr.return_value = mock_pipeline
    mock_pipeline.expire.return_value = mock_pipeline
    mock_pipeline.execute = AsyncMock(return_value=[1, True])
    mock_redis_client.pipeline.return_value = mock_pipeline
    mock_redis_client.get = AsyncMock(return_value=None)
    mock_redis_client.setex = AsyncMock(return_value=True)
    monkeypatch.setattr("redis.asyncio.Redis", lambda **kwargs: mock_redis_client)
    return mock_redis_client

# ─── Fixtures ───
@pytest.fixture
def sample_transaction():
    return {
        "transaction_id": "TXN_PG_TEST",
        "card_id": "CARD_PG_TEST",
        "amount": 25000.00,
        "currency": "USD",
        "merchant_id": "MERCH_1",
        "merchant_category": "retail",
        "country_code": "US",
        "city": "NY",
        "ip_address": "127.0.0.1",
        "device_fingerprint": "dev_1",
        "timestamp": "2024-01-01T10:00:00Z"
    }

@pytest.fixture
def sample_user_data():
    return {"email": "pg_test@example.com", "password": "password123", "country": "US"}

@pytest.fixture
def sample_rule_data():
    return {
        "rule_name": "High Amount Rule",
        "rule_type": "amount",
        "conditions": {"max_amount": 50000, "currency": "USD"},
        "risk_weight": 30,
        "is_active": True,
        "description": "Flag transactions above 50k USD"
    }

# ─── Helpers ───
async def register_and_login(client, email="pg_test@example.com", password="password123", role=None):
    # Registration
    reg_resp = await client.post("/api/v1/auth/register", json={
        "email": email, 
        "password": password, 
        "country": "US"
    })
    # If 400 (Already exists), it's fine.
    assert reg_resp.status_code in (200, 400), f"Registration failed: {reg_resp.text}"
    
    # Login to get token
    login_resp = await client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert login_resp.status_code == 200, f"Login failed for {email}: {login_resp.text}"
    
    data = login_resp.json()
    token = data.get("access_token")
    assert token, "No access_token returned from login"
    
    # Extract user_id from token sub (JWT payload)
    from jose import jwt
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    user_id = payload.get("sub")
    
    if role == "admin":
        token = create_access_token(data={"sub": str(user_id), "role": "admin", "email": email})
    
    return user_id, token

def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}