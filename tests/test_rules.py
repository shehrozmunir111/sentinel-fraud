import pytest
from tests.conftest import register_and_login, auth_headers


# ──────────────────────────── POST /api/v1/rules/ (create rule – admin only) ────────────────────────────

@pytest.mark.asyncio
async def test_create_rule_as_admin(client, sample_rule_data):
    """Admin should be able to create a fraud rule."""
    _, token = await register_and_login(client, email="admin_rule@test.com", role="admin")

    response = await client.post(
        "/api/v1/rules/",
        json=sample_rule_data,
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["rule_name"] == sample_rule_data["rule_name"]
    assert data["rule_type"] == sample_rule_data["rule_type"]
    assert data["risk_weight"] == sample_rule_data["risk_weight"]
    assert data["is_active"] is True
    assert "id" in data


@pytest.mark.asyncio
async def test_create_rule_as_analyst_forbidden(client, sample_rule_data):
    """Non-admin (analyst) should be forbidden from creating rules."""
    _, token = await register_and_login(client, email="analyst_rule@test.com")

    response = await client.post(
        "/api/v1/rules/",
        json=sample_rule_data,
        headers=auth_headers(token),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_rule_unauthenticated(client, sample_rule_data):
    """Creating a rule without auth should fail."""
    response = await client.post("/api/v1/rules/", json=sample_rule_data)
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_create_duplicate_rule_name(client, sample_rule_data):
    """Creating a rule with a duplicate name should return 400."""
    _, token = await register_and_login(client, email="dup_rule@test.com", role="admin")

    await client.post("/api/v1/rules/", json=sample_rule_data, headers=auth_headers(token))
    resp2 = await client.post("/api/v1/rules/", json=sample_rule_data, headers=auth_headers(token))
    assert resp2.status_code == 400
    assert "already exists" in resp2.json()["detail"].lower()


# ──────────────────────────── GET /api/v1/rules/ (list rules) ────────────────────────────

@pytest.mark.asyncio
async def test_list_rules(client, sample_rule_data):
    """Listing rules should return paginated response."""
    _, token = await register_and_login(client, email="list_rule@test.com", role="admin")

    # Create a rule first
    await client.post("/api/v1/rules/", json=sample_rule_data, headers=auth_headers(token))

    response = await client.get(
        "/api/v1/rules/?page=1&limit=20",
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_list_rules_unauthenticated(client):
    """Listing rules without auth should fail."""
    response = await client.get("/api/v1/rules/?page=1&limit=20")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_rules_filter_by_type(client, sample_rule_data):
    """Filtering rules by rule_type should work."""
    _, token = await register_and_login(client, email="filter_rule@test.com", role="admin")
    await client.post("/api/v1/rules/", json=sample_rule_data, headers=auth_headers(token))

    response = await client.get(
        "/api/v1/rules/?rule_type=amount",
        headers=auth_headers(token),
    )
    assert response.status_code == 200


# ──────────────────────────── GET /api/v1/rules/active ────────────────────────────

@pytest.mark.asyncio
async def test_get_active_rules(client, sample_rule_data):
    """GET /rules/active should return only active rules."""
    _, token = await register_and_login(client, email="active_rule@test.com", role="admin")
    await client.post("/api/v1/rules/", json=sample_rule_data, headers=auth_headers(token))

    response = await client.get("/api/v1/rules/active")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert data[0]["is_active"] is True


# ──────────────────────────── PUT /api/v1/rules/{rule_id} (update) ────────────────────────────

@pytest.mark.asyncio
async def test_update_rule(client, sample_rule_data):
    """Admin should be able to update an existing rule."""
    _, token = await register_and_login(client, email="update_rule@test.com", role="admin")

    create_resp = await client.post(
        "/api/v1/rules/", json=sample_rule_data, headers=auth_headers(token)
    )
    rule_id = create_resp.json()["id"]

    updated = sample_rule_data.copy()
    updated["rule_name"] = "Updated Rule Name"
    updated["risk_weight"] = 50

    response = await client.put(
        f"/api/v1/rules/{rule_id}",
        json=updated,
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["rule_name"] == "Updated Rule Name"
    assert data["risk_weight"] == 50


@pytest.mark.asyncio
async def test_update_rule_not_found(client, sample_rule_data):
    """Updating a non-existent rule should return 404."""
    _, token = await register_and_login(client, email="update404@test.com", role="admin")

    response = await client.put(
        "/api/v1/rules/00000000-0000-0000-0000-000000000001",
        json=sample_rule_data,
        headers=auth_headers(token),
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_rule_analyst_forbidden(client, sample_rule_data):
    """Analyst should not be able to update rules."""
    admin_id, admin_token = await register_and_login(client, email="admin_upd@test.com", role="admin")
    _, analyst_token = await register_and_login(client, email="analyst_upd@test.com")

    create_resp = await client.post(
        "/api/v1/rules/", json=sample_rule_data, headers=auth_headers(admin_token)
    )
    rule_id = create_resp.json()["id"]

    response = await client.put(
        f"/api/v1/rules/{rule_id}",
        json=sample_rule_data,
        headers=auth_headers(analyst_token),
    )
    assert response.status_code == 403


# ──────────────────────────── DELETE /api/v1/rules/{rule_id} ────────────────────────────

@pytest.mark.asyncio
async def test_delete_rule(client, sample_rule_data):
    """Admin should be able to delete a rule."""
    _, token = await register_and_login(client, email="del_rule@test.com", role="admin")

    create_resp = await client.post(
        "/api/v1/rules/", json=sample_rule_data, headers=auth_headers(token)
    )
    rule_id = create_resp.json()["id"]

    response = await client.delete(
        f"/api/v1/rules/{rule_id}",
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    assert "deleted" in response.json()["message"].lower()


@pytest.mark.asyncio
async def test_delete_rule_not_found(client):
    """Deleting a non-existent rule should return 404."""
    _, token = await register_and_login(client, email="del404@test.com", role="admin")

    response = await client.delete(
        "/api/v1/rules/00000000-0000-0000-0000-000000000001",
        headers=auth_headers(token),
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_rule_analyst_forbidden(client, sample_rule_data):
    """Analyst should not be able to delete rules."""
    _, admin_token = await register_and_login(client, email="admin_del@test.com", role="admin")
    _, analyst_token = await register_and_login(client, email="analyst_del@test.com")

    create_resp = await client.post(
        "/api/v1/rules/", json=sample_rule_data, headers=auth_headers(admin_token)
    )
    rule_id = create_resp.json()["id"]

    response = await client.delete(
        f"/api/v1/rules/{rule_id}",
        headers=auth_headers(analyst_token),
    )
    assert response.status_code == 403
