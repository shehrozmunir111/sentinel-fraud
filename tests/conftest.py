import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.base import Base, get_db

TEST_DATABASE_URL = "postgresql+asyncpg://sentinel:sentinel123@localhost:5432/sentinelfraud_test"

engine = create_async_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

@pytest_asyncio.fixture
async def db_session():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()

@pytest.fixture
def sample_transaction():
    return {
        "transaction_id": "TXN123456",
        "card_id": "CARD987654",
        "amount": 15000.00,
        "currency": "USD",
        "merchant_id": "MERCHANT001",
        "merchant_category": "electronics",
        "country_code": "US",
        "city": "New York",
        "ip_address": "192.168.1.1",
        "device_fingerprint": "fp_abc123",
        "timestamp": "2024-01-01T12:00:00Z"
    }