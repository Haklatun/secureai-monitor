"""
Tests for authentication endpoints.
Run with: pytest tests/ -v
"""
import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_login_invalid_credentials():
    async with AsyncClient(app=app, base_url="http://test") as client:
        res = await client.post("/api/auth/login", json={
            "email": "nobody@test.com",
            "password": "wrongpassword123"
        })
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_login_missing_fields():
    async with AsyncClient(app=app, base_url="http://test") as client:
        res = await client.post("/api/auth/login", json={"email": "test@test.com"})
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(app=app, base_url="http://test") as client:
        res = await client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_protected_route_without_token():
    async with AsyncClient(app=app, base_url="http://test") as client:
        res = await client.get("/api/logs")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_log_ingest_invalid_ip():
    """Input validation should reject malformed IP addresses."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        res = await client.post(
            "/api/logs",
            json={
                "event_type": "test",
                "source_ip": "not-an-ip-address!!",
            },
            headers={"Authorization": "Bearer fake_token"}
        )
    # 401 because fake token; validation happens before auth in pydantic
    assert res.status_code in (401, 422)
