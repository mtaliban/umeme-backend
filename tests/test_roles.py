"""Tests for role-based access control."""
import pytest
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.user import User
from app.security.passwords import hash_password

BASE = "http://test"


async def _login(ac: AsyncClient, email: str, password: str) -> None:
    resp = await ac.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200


async def _make_user(email: str, password: str, role: str) -> User:
    existing = await User.find_one(User.email == email)
    if existing:
        await existing.delete()
    user = User(
        name=f"{role} user",
        email=email,
        password_hash=hash_password(password),
        role=role,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await user.insert()
    return user


@pytest.mark.asyncio
async def test_inbox_officer_cannot_access_settings(init_test_db):
    """inbox_officer should get 403 on /api/admin/settings."""
    email = "officer@example.com"
    pw = "Password1234"
    await _make_user(email, pw, "inbox_officer")

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        await _login(ac, email, pw)
        resp = await ac.get("/api/admin/settings")

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_writer_cannot_delete(init_test_db):
    """writer role should get 403 when trying to delete a collection item."""
    email = "writertest@example.com"
    pw = "Password1234"
    await _make_user(email, pw, "writer")

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        await _login(ac, email, pw)
        # Fake ID — should get 403 before the 404
        resp = await ac.delete(
            "/api/admin/posts/000000000000000000000001",
            headers={"origin": "http://localhost"},
        )

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_editor_can_access_activity(init_test_db):
    email = "editortest@example.com"
    pw = "Password1234"
    await _make_user(email, pw, "editor")

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        await _login(ac, email, pw)
        resp = await ac.get("/api/admin/activity")

    assert resp.status_code == 200
    assert "items" in resp.json()


@pytest.mark.asyncio
async def test_unauthenticated_cannot_access_admin(init_test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get("/api/admin/dashboard")
    assert resp.status_code == 401
