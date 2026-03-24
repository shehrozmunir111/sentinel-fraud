import pytest
from tests.conftest import register_and_login, auth_headers


# ──────────────────────────── POST /api/v1/transactions/assess ────────────────────────────

@pytest.mark.asyncio
async def test_assess_transaction_success(client, sample_transaction):
    """Assess a valid transaction – should return risk_score and decision."""
    user_id, token = await register_and_login(client, email="tx@test.com")
    sample_transaction["user_id"] = user_id

    response = await client.post(
        "/api/v1/transactions/assess",
        json=sample_transaction,
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    data = response.json()
    assert "risk_score" in data
    assert "decision" in data
    assert "ml_score" in data
    assert "rule_contributions" in data
    assert "processing_time_ms" in data


@pytest.mark.asyncio
async def test_assess_transaction_unauthenticated(client, sample_transaction):
    """Assess without token should fail with 401/403."""
    sample_transaction["user_id"] = "00000000-0000-0000-0000-000000000001"
    response = await client.post(
        "/api/v1/transactions/assess",
        json=sample_transaction,
    )
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_assess_transaction_invalid_amount(client):
    """Transaction with negative/zero amount should return 422."""
    user_id, token = await register_and_login(client, email="txbad@test.com")
    payload = {
        "transaction_id": "TXN_INVALID",
        "card_id": "CARD_001",
        "amount": -100,
        "currency": "USD",
        "merchant_id": "MERCH_001",
        "country_code": "US",
        "timestamp": "2024-01-01T12:00:00Z",
        "user_id": str(user_id),
    }
    response = await client.post(
        "/api/v1/transactions/assess",
        json=payload,
        headers=auth_headers(token),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_assess_transaction_exceeds_max_amount(client):
    """Amount exceeding 999999999.99 should be rejected."""
    user_id, token = await register_and_login(client, email="txmax@test.com")
    payload = {
        "transaction_id": "TXN_MAXAMT",
        "card_id": "CARD_002",
        "amount": 9999999999.99,
        "currency": "USD",
        "merchant_id": "MERCH_002",
        "country_code": "US",
        "timestamp": "2024-06-01T08:00:00Z",
        "user_id": str(user_id),
    }
    response = await client.post(
        "/api/v1/transactions/assess",
        json=payload,
        headers=auth_headers(token),
    )
    assert response.status_code == 422


# ──────────────────────────── GET /api/v1/transactions/ ────────────────────────────

@pytest.mark.asyncio
async def test_list_transactions_empty(client):
    """List transactions when none exist should return empty list."""
    _, token = await register_and_login(client, email="txlist@test.com")
    response = await client.get(
        "/api/v1/transactions/?page=1&limit=20",
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "pages" in data
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_list_transactions_after_assess(client, sample_transaction):
    """After assessing a transaction, it should appear in the listing."""
    user_id, token = await register_and_login(client, email="txlist2@test.com")
    sample_transaction["user_id"] = user_id

    # Create a transaction first
    await client.post(
        "/api/v1/transactions/assess",
        json=sample_transaction,
        headers=auth_headers(token),
    )

    response = await client.get(
        "/api/v1/transactions/?page=1&limit=20",
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_list_transactions_unauthenticated(client):
    """Listing transactions without auth should fail."""
    response = await client.get("/api/v1/transactions/?page=1&limit=20")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_transactions_pagination(client):
    """Pagination parameters should be respected."""
    _, token = await register_and_login(client, email="txpage@test.com")
    response = await client.get(
        "/api/v1/transactions/?page=1&limit=5",
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["limit"] == 5


@pytest.mark.asyncio
async def test_list_transactions_filter_decision(client, sample_transaction):
    """Filtering by decision query param should work."""
    user_id, token = await register_and_login(client, email="txfilter@test.com")
    sample_transaction["user_id"] = user_id

    await client.post(
        "/api/v1/transactions/assess",
        json=sample_transaction,
        headers=auth_headers(token),
    )

    response = await client.get(
        "/api/v1/transactions/?decision=approve",
        headers=auth_headers(token),
    )
    assert response.status_code == 200