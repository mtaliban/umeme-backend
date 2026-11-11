"""Tests for authentication endpoints."""
import pytest
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.user import User
from app.security.passwords import hash_password


BASE = "http://test"


async def _create_user(email: str, password: str, role: str = "writer") -> User:
    """Helper to create a user directly in the test DB."""
    existing = await User.find_one(User.email == email)
    if existing:
        await existing.delete()
    user = User(
        name="Test User",
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
async def test_login_success(init_test_db):
    email = "logintest@example.com"
    password = "TestPassword123"
    await _create_user(email, password)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post("/api/auth/login", json={"email": email, "password": password})

    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    # Cookie should be set
    assert "access_token" in resp.cookies


@pytest.mark.asyncio
async def test_login_wrong_password(init_test_db):
    email = "wrongpw@example.com"
    await _create_user(email, "CorrectPassword123")

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post("/api/auth/login", json={"email": email, "password": "WrongPassword!"})

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_account_lockout(init_test_db):
    """After 5 failed attempts the account should be locked."""
    email = "locktest@example.com"
    await _create_user(email, "CorrectPassword123")

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        for _ in range(5):
            await ac.post("/api/auth/login", json={"email": email, "password": "wrong"})
        # 6th attempt should be locked out
        resp = await ac.post("/api/auth/login", json={"email": email, "password": "wrong"})

    assert resp.status_code in (429, 401)


@pytest.mark.asyncio
async def test_me_requires_auth(init_test_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.get("/api/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_returns_user(init_test_db):
    email = "metest@example.com"
    password = "TestPassword123"
    await _create_user(email, password, role="editor")

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        # Login first
        login_resp = await ac.post("/api/auth/login", json={"email": email, "password": password})
        assert login_resp.status_code == 200
        # /me should return user info
        me_resp = await ac.get("/api/auth/me")

    assert me_resp.status_code == 200
    body = me_resp.json()
    assert body["email"] == email
    assert body["role"] == "editor"


@pytest.mark.asyncio
async def test_logout_clears_cookie(init_test_db):
    email = "logouttest@example.com"
    password = "TestPassword123"
    await _create_user(email, password)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        await ac.post("/api/auth/login", json={"email": email, "password": password})
        logout_resp = await ac.post("/api/auth/logout")

    assert logout_resp.status_code == 200


@pytest.mark.asyncio
async def test_change_password(init_test_db):
    email = "changepw@example.com"
    old_pw = "OldPassword123"
    new_pw = "NewPassword456"
    await _create_user(email, old_pw)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        await ac.post("/api/auth/login", json={"email": email, "password": old_pw})
        resp = await ac.post(
            "/api/auth/change-password",
            json={"current_password": old_pw, "new_password": new_pw},
        )

    assert resp.status_code == 200
    assert resp.json()["ok"] is True


@pytest.mark.asyncio
async def test_change_password_short(init_test_db):
    email = "shortpw@example.com"
    password = "LongEnoughPW"
    await _create_user(email, password)

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        await ac.post("/api/auth/login", json={"email": email, "password": password})
        resp = await ac.post(
            "/api/auth/change-password",
            json={"current_password": password, "new_password": "short"},
        )

    assert resp.status_code == 400
