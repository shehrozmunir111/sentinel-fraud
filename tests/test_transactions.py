import pytest

@pytest.mark.asyncio
async def test_assess_transaction(client, sample_transaction):
    user_resp = await client.post("/api/v1/auth/register", json={
        "email": "tx@test.com",
        "password": "testpass123",
        "country": "US"
    })
    user_id = user_resp.json()["id"]
    
    login_resp = await client.post("/api/v1/auth/login", data={
        "username": "tx@test.com",
        "password": "testpass123"
    })
    token = login_resp.json()["access_token"]
    
    sample_transaction["user_id"] = user_id
    response = await client.post(
        "/api/v1/transactions/assess",
        json=sample_transaction,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "risk_score" in data
    assert "decision" in data
    assert data["processing_time_ms"] < 100