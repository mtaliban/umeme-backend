import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_health_returns_200():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/health")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_health_schema():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/health")
    body = resp.json()
    assert body["status"] == "ok"
    assert "db" in body


@pytest.mark.asyncio
async def test_health_db_ok(init_test_db):
    """When MongoDB is reachable the db field must be 'ok'."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/health")
    assert resp.json()["db"] == "ok"
