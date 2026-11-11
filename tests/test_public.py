"""Tests for public API endpoints."""
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app

BASE = "http://test"


@pytest.mark.asyncio
async def test_public_settings(init_test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get("/api/public/settings")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_public_home(init_test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get("/api/public/home")
    assert resp.status_code == 200
    body = resp.json()
    assert "hero_slides" in body
    assert "stats" in body
    assert "features" in body


@pytest.mark.asyncio
async def test_public_home_sw(init_test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get("/api/public/home?lang=sw")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_public_pages_404(init_test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get("/api/public/pages/nonexistent-page")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_public_team(init_test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get("/api/public/team")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_public_services(init_test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get("/api/public/services")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_public_projects_pagination(init_test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get("/api/public/projects?page=1&limit=5")
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert "page" in body
    assert "pages" in body


@pytest.mark.asyncio
async def test_public_faqs(init_test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get("/api/public/faqs")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_public_sitemap(init_test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get("/api/public/sitemap")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
