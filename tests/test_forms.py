"""Tests for visitor form endpoints."""
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app

BASE = "http://test"


@pytest.mark.asyncio
async def test_contact_form_honeypot(init_test_db):
    """Requests with the honeypot field filled should silently succeed (but not save)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            "/api/forms/contact",
            json={
                "name": "Bot User",
                "phone": "0754000000",
                "subject": "test",
                "message": "hello",
                "consent": True,
                "website": "http://spam.com",  # honeypot filled
            },
        )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


@pytest.mark.asyncio
async def test_contact_form_no_consent(init_test_db):
    """Contact form without consent should return 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            "/api/forms/contact",
            json={
                "name": "Test User",
                "phone": "0754000000",
                "subject": "test",
                "message": "hello",
                "consent": False,
            },
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_contact_form_success(init_test_db):
    """Valid contact form should return ok."""
    from app.models.inbox import ContactMessage
    before = await ContactMessage.count()

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            "/api/forms/contact",
            json={
                "name": "Test User",
                "phone": "0754123456",
                "email": "test@example.com",
                "subject": "Test subject",
                "message": "This is a test message",
                "consent": True,
            },
        )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    after = await ContactMessage.count()
    assert after == before + 1


@pytest.mark.asyncio
async def test_contact_form_invalid_phone(init_test_db):
    """Invalid Tanzanian phone number should return 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        resp = await ac.post(
            "/api/forms/contact",
            json={
                "name": "Test User",
                "phone": "1234567890",  # not a valid TZ number
                "subject": "test",
                "message": "hello",
                "consent": True,
            },
        )
    assert resp.status_code == 422
