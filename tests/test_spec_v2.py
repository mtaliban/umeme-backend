"""Majaribio ya sehemu 8 — mahitaji mapya ya backend.

8.1 qty kamili / add_qty · 8.2 kufuta aina · 8.3 historia ya mauzo ·
8.4 aina iliyofutwa · 8.5 kalenda · 8.6 risiti · 8.7 PIN/logout ·
8.8 picha ya daftari · 8.9 client_id · 8.10 hesabu za ripoti.
"""

import io
import os
from datetime import date, timedelta

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ["DB_NAME"] = "ummu_ayman_test"
os.environ["JWT_SECRET"] = "test-secret-ndefu-sana-kwa-majaribio"
os.environ["AI_PROVIDER"] = "gemini"
os.environ["AI_FALLBACK"] = "groq,claude"

import pytest  # noqa: E402
from bson import ObjectId  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from PIL import Image  # noqa: E402

from app import auth as auth_mod  # noqa: E402
from app.auth import hash_pin  # noqa: E402
from app.db import create_indexes, db  # noqa: E402
from app.main import app  # noqa: E402
from app.services import notebook  # noqa: E402
from app.tz import now, today  # noqa: E402


@pytest.fixture(autouse=True)
async def fresh():
    await db.client.drop_database(db.name)
    await create_indexes()
    auth_mod.reset_attempts()
    await db.shops.insert_one(
        {
            "name": "UMMU AYMAN OUTFITS",
            "phone": "0621 340 044",
            "email": "kambilatifah@gmail.com",
            "pin_hash": hash_pin("1234"),
            "receipt_seq": 0,
            "settings": {"low_stock_threshold": 2, "close_day_reminder": "21:00"},
            "created_at": now(),
        }
    )
    yield


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
async def headers(client):
    res = await client.post("/auth/pin", json={"pin": "1234"})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['token']}"}


# ── Helpers ───────────────────────────────────────────────────────────────────

async def add_product(client, headers, name, has_variants=True):
    res = await client.post(
        "/stock/products", json={"name": name, "has_variants": has_variants}, headers=headers
    )
    assert res.status_code == 200, res.text
    return res.json()


async def add_variant(client, headers, product_id, name, qty, buying, selling):
    res = await client.post(
        f"/stock/products/{product_id}/variants",
        json={"name": name, "qty": qty, "buying": buying, "selling": selling},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    return res.json()


async def stock_qty(client, headers, product_id, variant_id):
    detail = (await client.get(f"/stock/products/{product_id}", headers=headers)).json()
    return next(v["qty"] for v in detail["variants"] if v["id"] == variant_id)


def png_bytes(size=(2200, 1600)):
    image = Image.new("RGB", size, (245, 245, 240))
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


# ── 8.1 ──────────────────────────────────────────────────────────────────────

async def test_81_qty_is_new_total_and_add_qty_is_422(client, headers):
    product = await add_product(client, headers, "Abaya")
    detail = await add_variant(client, headers, product["id"], "Abaya nyeusi", 5, 7000, 11000)
    vid = detail["variants"][0]["id"]

    res = await client.patch(f"/stock/variants/{vid}", json={"qty": 1}, headers=headers)
    assert res.status_code == 200, res.text
    assert res.json()["variants"][0]["qty"] == 1  # si 6

    res = await client.patch(f"/stock/variants/{vid}", json={"qty": 3}, headers=headers)
    assert res.status_code == 200, res.text
    assert res.json()["variants"][0]["qty"] == 3

    res = await client.patch(f"/stock/variants/{vid}", json={"add_qty": 10}, headers=headers)
    assert res.status_code == 422
    assert res.json()["detail"] == "Tumia qty"

    movement = await db.stock_movements.find_one(
        {"variant_id": ObjectId(vid), "delta": -4}
    )
    assert movement is not None
    assert movement["qty_after"] == 1


# ── 8.2 ──────────────────────────────────────────────────────────────────────

async def test_82_delete_only_variant_is_400(client, headers):
    res = await client.post(
        "/stock/products",
        json={"name": "Mafuta ya nywele", "has_variants": False, "qty": 5, "buying": 3000, "selling": 5000},
        headers=headers,
    )
    product = res.json()
    vid = product["variants"][0]["id"]

    res = await client.delete(f"/stock/variants/{vid}", headers=headers)
    assert res.status_code == 400
    assert res.json()["detail"] == "Futa bidhaa nzima"


async def test_82b_delete_variant_returns_product_and_movements_go(client, headers):
    product = await add_product(client, headers, "Abaya")
    first = await add_variant(client, headers, product["id"], "Abaya nyeusi", 5, 7000, 11000)
    await add_variant(client, headers, product["id"], "Abaya ya Dubai", 2, 25000, 35000)
    vid = first["variants"][0]["id"]

    res = await client.delete(f"/stock/variants/{vid}", headers=headers)
    assert res.status_code == 200, res.text
    detail = res.json()
    assert [v["name"] for v in detail["variants"]] == ["Abaya ya Dubai"]
    assert detail["summary"] == {"qty": 2, "capital": 50000, "profit_if_sold": 20000}
    assert await db.stock_movements.count_documents({"variant_id": ObjectId(vid)}) == 0


# ── 8.3 ──────────────────────────────────────────────────────────────────────

async def test_83_delete_product_keeps_sales_history(client, headers):
    day = today().isoformat()
    product = await add_product(client, headers, "Abaya")
    detail = await add_variant(client, headers, product["id"], "Abaya nyeusi", 5, 7000, 11000)
    vid = detail["variants"][0]["id"]

    await client.post(
        f"/daily/{day}/lines",
        json={"variant_id": vid, "qty": 1, "selling": 11000},
        headers=headers,
    )
    receipt = (
        await client.post(
            "/receipts",
            json={
                "date": day,
                "customer": {"name": "Said Hamad"},
                "items": [{"variant_id": vid, "qty": 2, "price": 11000, "discount": 0}],
            },
            headers=headers,
        )
    ).json()

    res = await client.delete(f"/stock/products/{product['id']}", headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()
    assert set(data) == {"summary", "products"}
    assert data["products"] == []
    assert await db.products.count_documents({}) == 0

    one = await client.get(f"/receipts/{receipt['id']}", headers=headers)
    assert one.status_code == 200
    assert one.json()["items"][0]["name"] == "Abaya nyeusi"
    assert one.json()["paid"] == 22000

    sheet = (await client.get(f"/daily/{day}", headers=headers)).json()
    assert [line["name"] for line in sheet["receipt_lines"]] == ["Abaya nyeusi"]
    assert sheet["lines"][0]["name"] == "Abaya nyeusi"
    assert sheet["summary"]["sales"] == 33000


# ── 8.4 ──────────────────────────────────────────────────────────────────────

async def test_84_deleted_variant_line_can_be_edited_and_cancelled(client, headers):
    day = today().isoformat()
    product = await add_product(client, headers, "Abaya")
    detail = await add_variant(client, headers, product["id"], "Abaya nyeusi", 5, 7000, 11000)
    other = await add_variant(client, headers, product["id"], "Abaya ya Dubai", 5, 25000, 35000)
    vid = detail["variants"][0]["id"]
    other_vid = next(v["id"] for v in other["variants"] if v["name"] == "Abaya ya Dubai")

    res = await client.post(
        f"/daily/{day}/lines",
        json={"variant_id": vid, "qty": 2, "selling": 11000},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    line_id = res.json()["lines"][0]["id"]

    receipt = (
        await client.post(
            "/receipts",
            json={
                "date": day,
                "items": [{"variant_id": other_vid, "qty": 2, "price": 35000, "discount": 0}],
            },
            headers=headers,
        )
    ).json()

    # Aina zote zinafutwa (bidhaa inabaki bila aina — has_types True).
    for variant_id in (vid, other_vid):
        res = await client.delete(f"/stock/variants/{variant_id}", headers=headers)
        assert res.status_code == 200, res.text

    # Kurekebisha mstari wa aina iliyofutwa hakuleti kosa.
    res = await client.patch(
        f"/daily/{day}/lines/{line_id}", json={"qty": 3}, headers=headers
    )
    assert res.status_code == 200, res.text
    assert res.json()["lines"][0]["qty"] == 3

    res = await client.patch(
        f"/daily/{day}/lines/{line_id}", json={"qty": 1}, headers=headers
    )
    assert res.status_code == 200, res.text
    assert res.json()["lines"][0]["qty"] == 1

    res = await client.delete(f"/daily/{day}/lines/{line_id}", headers=headers)
    assert res.status_code == 200, res.text

    # Kughairi risiti ya aina iliyofutwa hakuleti kosa.
    res = await client.post(f"/receipts/{receipt['id']}/cancel", headers=headers)
    assert res.status_code == 200, res.text
    assert res.json()["ok"] is True


# ── 8.5 ──────────────────────────────────────────────────────────────────────

async def test_85_calendar_days_and_bounds(client, headers):
    current = today()
    previous = current.replace(day=1) - timedelta(days=1)
    next_month = (
        date(current.year + 1, 1, 1)
        if current.month == 12
        else date(current.year, current.month + 1, 1)
    )

    product = await add_product(client, headers, "Abaya")
    detail = await add_variant(client, headers, product["id"], "Abaya nyeusi", 20, 7000, 11000)
    vid = detail["variants"][0]["id"]

    for day in (previous.isoformat(), current.isoformat()):
        res = await client.post(
            f"/daily/{day}/lines",
            json={"variant_id": vid, "qty": 1, "selling": 11000},
            headers=headers,
        )
        assert res.status_code == 200, res.text

    data = (await client.get("/daily/calendar", headers=headers)).json()
    assert set(data) == {"month", "label", "today", "days", "has_prev", "has_next"}
    assert data["month"] == f"{current.year}-{current.month:02d}"
    assert data["label"].startswith("Novemba") or data["label"]  # "Novemba 2026"
    assert data["today"] == current.isoformat()
    assert current.isoformat() in data["days"]
    assert data["has_prev"] is True
    assert data["has_next"] is False

    past = (
        await client.get(
            "/daily/calendar", params={"month": previous.strftime("%Y-%m")}, headers=headers
        )
    ).json()
    assert previous.isoformat() in past["days"]
    assert past["has_next"] is True

    res = await client.get(
        "/daily/calendar", params={"month": next_month.strftime("%Y-%m")}, headers=headers
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "Huwezi kuchagua mwezi ujao"

    res = await client.get("/daily/calendar", params={"month": "2026-13"}, headers=headers)
    assert res.status_code == 422
    assert res.json()["detail"] == "Tarehe si sahihi"

    # "calendar" haichukui tarehe; GET /daily/{date} bado inafanya kazi.
    res = await client.get(f"/daily/{current.isoformat()}", headers=headers)
    assert res.status_code == 200


async def test_85b_calendar_counts_receipts_not_cancelled(client, headers):
    day = today().isoformat()
    res = await client.post(
        "/receipts",
        json={
            "date": day,
            "items": [
                {"variant_id": None, "name": "Kanga", "qty": 1, "price": 5000, "discount": 0, "buying": 3000}
            ],
        },
        headers=headers,
    )
    receipt = res.json()
    data = (await client.get("/daily/calendar", headers=headers)).json()
    assert day in data["days"]

    await client.post(f"/receipts/{receipt['id']}/cancel", headers=headers)
    data = (await client.get("/daily/calendar", headers=headers)).json()
    assert day not in data["days"]


# ── 8.6 ──────────────────────────────────────────────────────────────────────

async def test_86_receipt_address_category_and_money(client, headers):
    day = today().isoformat()
    product = await add_product(client, headers, "Abaya")
    detail = await add_variant(client, headers, product["id"], "Abaya nyeusi", 5, 7000, 11000)
    vid = detail["variants"][0]["id"]

    res = await client.post(
        "/receipts",
        json={
            "date": day,
            "customer": {"name": "Said Hamad", "phone": "0712445900", "address": "  Kariakoo, Dar  "},
            "items": [
                {"variant_id": vid, "qty": 2, "price": 11000, "discount": 1000},
                {"variant_id": None, "name": "Kanga", "qty": 1, "price": 9000, "discount": 0, "buying": 5000},
            ],
        },
        headers=headers,
    )
    assert res.status_code == 201, res.text
    receipt = res.json()

    assert receipt["customer"]["address"] == "Kariakoo, Dar"
    assert receipt["customer"]["location"] == "Kariakoo, Dar"
    assert [item["category"] for item in receipt["items"]] == ["Abaya", "Kanga"]
    assert receipt["items"][0]["amount"] == 2 * (11000 - 1000)
    assert receipt["total_qty"] == 3
    assert receipt["paid"] == sum(item["amount"] for item in receipt["items"]) == 29000
    assert receipt["gross"] == 31000
    assert receipt["discount"] == 2000
    assert receipt["shop"]["signature_name"] == "Ummu Ayman"

    # Ombi la zamani lenye `location` linapokewa pia.
    legacy = (
        await client.post(
            "/receipts",
            json={
                "date": day,
                "customer": {"name": "Neema", "location": "Mbagala"},
                "items": [
                    {"variant_id": None, "name": "Kanga", "qty": 1, "price": 5000, "discount": 0, "buying": 3000}
                ],
            },
            headers=headers,
        )
    ).json()
    assert legacy["customer"]["address"] == "Mbagala"

    me = (await client.get("/me", headers=headers)).json()
    assert me["signature_name"] == "Ummu Ayman"


# ── 8.7 ──────────────────────────────────────────────────────────────────────

async def test_87_pin_change_errors_and_success(client, headers):
    res = await client.put(
        "/auth/pin", json={"old_pin": "9999", "new_pin": "5678"}, headers=headers
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "PIN ya sasa si sahihi"

    res = await client.put(
        "/auth/pin", json={"old_pin": "1234", "new_pin": "12"}, headers=headers
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "PIN mpya iwe namba 4"

    res = await client.put(
        "/auth/pin", json={"old_pin": "1234", "new_pin": "1234"}, headers=headers
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "PIN mpya isiwe sawa na ya sasa"

    res = await client.put(
        "/auth/pin", json={"old_pin": "1234", "new_pin": "5678"}, headers=headers
    )
    assert res.status_code == 200
    assert res.json() == {"ok": True}

    # Token iliyopo inaendelea kufanya kazi; PIN mpya inaingia.
    assert (await client.get("/me", headers=headers)).status_code == 200
    assert (await client.post("/auth/pin", json={"pin": "5678"})).status_code == 200


async def test_87b_pin_change_rate_limit(client, headers):
    for _ in range(5):
        res = await client.put(
            "/auth/pin", json={"old_pin": "0000", "new_pin": "5678"}, headers=headers
        )
        assert res.status_code == 400

    res = await client.put(
        "/auth/pin", json={"old_pin": "1234", "new_pin": "5678"}, headers=headers
    )
    assert res.status_code == 429
    assert res.json()["detail"] == "Subiri dakika 10"


async def test_87c_logout_is_204_and_drops_device(client, headers):
    await client.post("/devices", json={"fcm_token": "tok-1"}, headers=headers)
    assert await db.devices.count_documents({"fcm_token": "tok-1"}) == 1

    res = await client.post(
        "/auth/logout", headers={**headers, "X-Device-Token": "tok-1"}
    )
    assert res.status_code == 204
    assert res.content == b""
    assert await db.devices.count_documents({"fcm_token": "tok-1"}) == 0

    # Bila kifaa — bado 204.
    res = await client.post("/auth/logout", headers=headers)
    assert res.status_code == 204


# ── 8.8 ──────────────────────────────────────────────────────────────────────

async def test_88_scan_returns_day_sheet(client, headers, monkeypatch):
    day = today().isoformat()
    product = await add_product(client, headers, "Kanga")
    detail = await add_variant(client, headers, product["id"], "Kanga za pwani", 10, 6000, 9000)
    vid = detail["variants"][0]["id"]

    calls = {}

    async def fake_read(image, names):
        calls["bytes"] = len(image)
        calls["names"] = names
        return {
            "lines": [
                {"name": "Jumla", "qty": 0, "price": 0, "total": 0},
                {"name": "kanga za pwani", "qty": 2, "price": 9000, "total": 18000, "buying": 0},
                {"name": "Bidhaa mpya", "qty": 1, "price": 5000, "total": 5000, "buying": 3000},
                {"name": "kanga za pwani", "qty": 2, "price": 9000, "total": 18000},
            ],
            "expenses": [
                {"name": "Usafiri", "amount": 2000},
                {"name": "Chai", "amount": 20},
            ],
        }

    monkeypatch.setattr(notebook, "read_notebook", fake_read)

    res = await client.post(
        f"/daily/{day}/scan",
        files={"image": ("ukurasa.png", png_bytes(), "image/png")},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    sheet = res.json()
    assert set(sheet) == {"date", "saved_at", "receipt_lines", "lines", "expenses", "summary"}
    assert sheet["date"] == day
    assert calls["bytes"] > 0
    assert "Kanga za pwani" in calls["names"]

    assert [line["name"] for line in sheet["lines"]] == ["Kanga za pwani", "Bidhaa mpya"]
    matched, off_stock = sheet["lines"]
    assert matched["variant_id"] == vid
    assert matched["buying"] == 6000  # buying inatoka Stock
    assert off_stock["variant_id"] is None
    assert off_stock["buying"] == 3000

    # Gharama: ndogo (20) imeachwa; client_id/scan_id haionyeshwi.
    assert sheet["expenses"] == [
        {"id": sheet["expenses"][0]["id"], "name": "Usafiri", "amount": 2000}
    ]
    assert sheet["summary"]["sales"] == 2 * 9000 + 5000
    assert sheet["summary"]["capital"] == 2 * 6000 + 3000
    assert await stock_qty(client, headers, product["id"], vid) == 8


async def test_88b_scan_fixes_price_from_total(client, headers, monkeypatch):
    async def fake_read(image, names):
        return {
            "lines": [{"name": "Kitu", "qty": 3, "price": 1000, "total": 5000, "buying": 0}],
            "expenses": [],
        }

    monkeypatch.setattr(notebook, "read_notebook", fake_read)
    res = await client.post(
        f"/daily/{today().isoformat()}/scan",
        files={"image": ("p.png", png_bytes((400, 300)), "image/png")},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    line = res.json()["lines"][0]
    assert line["selling"] == round(5000 / 3)
    # Haipo kwenye stock: buying = bei ya kuuza (faida 0).
    assert line["buying"] == line["selling"]


async def test_88c_scan_bad_image_and_empty_read(client, headers, monkeypatch):
    day = today().isoformat()

    res = await client.post(f"/daily/{day}/scan", headers=headers)
    assert res.status_code == 422
    assert res.json()["detail"] == "Picha si sahihi"

    res = await client.post(
        f"/daily/{day}/scan",
        files={"image": ("x.png", b"hii si picha", "image/png")},
        headers=headers,
    )
    assert res.status_code == 422
    assert res.json()["detail"] == "Picha si sahihi"

    res = await client.post(
        f"/daily/{day}/scan",
        files={"image": ("x.txt", b"hujambo", "text/plain")},
        headers=headers,
    )
    assert res.status_code == 422
    assert res.json()["detail"] == "Picha si sahihi"

    big = b"0" * (6 * 1024 * 1024 + 16)
    res = await client.post(
        f"/daily/{day}/scan",
        files={"image": ("big.jpg", big, "image/jpeg")},
        headers=headers,
    )
    assert res.status_code == 422
    assert res.json()["detail"] == "Picha si sahihi"

    tomorrow = (today() + timedelta(days=1)).isoformat()
    res = await client.post(
        f"/daily/{tomorrow}/scan",
        files={"image": ("p.png", png_bytes((200, 200)), "image/png")},
        headers=headers,
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "Huwezi kuandika siku ijayo"

    async def empty_read(image, names):
        return {"lines": [], "expenses": []}

    monkeypatch.setattr(notebook, "read_notebook", empty_read)
    res = await client.post(
        f"/daily/{day}/scan",
        files={"image": ("p.png", png_bytes((200, 200)), "image/png")},
        headers=headers,
    )
    assert res.status_code == 422
    assert res.json()["detail"] == "Haikusomeka — piga picha tena"
    assert await db.daily_sheets.count_documents({}) == 0


async def test_88d_scan_saved_day_is_409_and_ai_down_is_503(client, headers, monkeypatch):
    day = today().isoformat()

    async def fake_read(image, names):
        return {
            "lines": [{"name": "Kitu", "qty": 1, "price": 5000, "total": 5000, "buying": 0}],
            "expenses": [],
        }

    monkeypatch.setattr(notebook, "read_notebook", fake_read)
    assert (await client.post(f"/daily/{day}/close", headers=headers)).status_code == 200

    res = await client.post(
        f"/daily/{day}/scan",
        files={"image": ("p.png", png_bytes((200, 200)), "image/png")},
        headers=headers,
    )
    assert res.status_code == 409

    # AI zote hazipatikani (hakuna funguo) → 503.
    monkeypatch.undo()
    monkeypatch.setattr(notebook.settings, "gemini_api_key", "")
    monkeypatch.setattr(notebook.settings, "groq_api_key", "")
    monkeypatch.setattr(notebook.settings, "claude_api_key", "")
    other = (today() - timedelta(days=1)).isoformat()
    res = await client.post(
        f"/daily/{other}/scan",
        files={"image": ("p.png", png_bytes((200, 200)), "image/png")},
        headers=headers,
    )
    assert res.status_code == 503
    assert res.json()["detail"] == "Jaribu tena baadaye"


# ── 8.9 ──────────────────────────────────────────────────────────────────────

async def test_89_client_id_makes_writes_idempotent(client, headers):
    day = today().isoformat()
    product = await add_product(client, headers, "Abaya")
    detail = await add_variant(client, headers, product["id"], "Abaya nyeusi", 5, 7000, 11000)
    vid = detail["variants"][0]["id"]

    line = {"variant_id": vid, "qty": 2, "selling": 11000, "client_id": "line-1"}
    first = await client.post(f"/daily/{day}/lines", json=line, headers=headers)
    second = await client.post(f"/daily/{day}/lines", json=line, headers=headers)
    assert first.status_code == second.status_code == 200
    assert len(second.json()["lines"]) == 1
    assert await stock_qty(client, headers, product["id"], vid) == 3  # mara moja tu

    expense = {"name": "Usafiri", "amount": 2000, "client_id": "exp-1"}
    await client.post(f"/daily/{day}/expenses", json=expense, headers=headers)
    twice = await client.post(f"/daily/{day}/expenses", json=expense, headers=headers)
    assert twice.status_code == 200
    assert [e["name"] for e in twice.json()["expenses"]] == ["Usafiri"]
    assert set(twice.json()["expenses"][0]) == {"id", "name", "amount"}

    body = {
        "date": day,
        "customer": {"name": "Said Hamad"},
        "items": [{"variant_id": vid, "qty": 1, "price": 11000, "discount": 0}],
        "client_id": "rec-1",
    }
    first_receipt = await client.post("/receipts", json=body, headers=headers)
    second_receipt = await client.post("/receipts", json=body, headers=headers)
    assert first_receipt.status_code == second_receipt.status_code == 201
    assert first_receipt.json()["id"] == second_receipt.json()["id"]
    assert await db.receipts.count_documents({"shop_id": (await db.shops.find_one({}))["_id"]}) == 1
    assert await stock_qty(client, headers, product["id"], vid) == 2  # 5 - 2 (mstari) - 1 (risiti)


# ── 8.10 ─────────────────────────────────────────────────────────────────────

async def test_810_report_totals_match(client, headers):
    product = await add_product(client, headers, "Abaya")
    detail = await add_variant(client, headers, product["id"], "Abaya nyeusi", 40, 7000, 11000)
    vid = detail["variants"][0]["id"]
    current = today()

    for offset in (1, 0):
        day = (current - timedelta(days=offset)).isoformat()
        res = await client.post(
            f"/daily/{day}/lines",
            json={"variant_id": vid, "qty": 2, "selling": 11000},
            headers=headers,
        )
        assert res.status_code == 200, res.text
        for name, amount in (("Usafiri", 2000), (" usafiri ", 1000), ("Bando", 500)):
            res = await client.post(
                f"/daily/{day}/expenses",
                json={"name": name, "amount": amount},
                headers=headers,
            )
            assert res.status_code == 200, res.text

    week = (await client.get("/reports/week", headers=headers)).json()
    assert set(week["bars"][0]) == {
        "key", "label", "name", "sales", "capital", "expenses", "net"
    }
    assert sum(e["amount"] for e in week["expense_list"]) == week["summary"]["expenses"]
    assert (
        sum(b["net"] for b in week["bars"] if b["net"] is not None)
        == week["summary"]["net"]
    )
    assert (
        sum(b["sales"] for b in week["bars"] if b["sales"] is not None)
        == week["summary"]["sales"]
    )
    assert week["summary"]["expenses"] == 2 * (2000 + 1000 + 500)

    month = (await client.get("/reports/month", headers=headers)).json()
    assert sum(g["amount"] for g in month["expense_groups"]) == month["summary"]["expenses"]
    # "Usafiri" na " usafiri " zinaunganishwa (herufi/nafasi hazizingatiwi).
    assert month["expense_groups"][0] == {"name": "Usafiri", "count": 4, "amount": 6000}
    assert (
        sum(b["net"] for b in month["bars"] if b["net"] is not None)
        == month["summary"]["net"]
    )

    year = (await client.get("/reports/year", headers=headers)).json()
    assert sum(g["amount"] for g in year["expense_groups"]) == year["summary"]["expenses"]
    assert (
        sum(b["sales"] for b in year["bars"] if b["sales"] is not None)
        == year["summary"]["sales"]
    )

    day_report = (await client.get(f"/reports/day/{current.isoformat()}", headers=headers)).json()
    assert [e["name"] for e in day_report["expenses"]] == ["Usafiri", "usafiri", "Bando"]
    assert sum(e["amount"] for e in day_report["expenses"]) == day_report["summary"]["expenses"]


async def test_811_bars_name_shape(client, headers):
    week = (await client.get("/reports/week", headers=headers)).json()
    for bar in week["bars"]:
        assert bar["name"].split()[0] in {
            "Jumatatu", "Jumanne", "Jumatano", "Alhamisi", "Ijumaa", "Jumamosi", "Jumapili"
        }

    month = (await client.get("/reports/month", headers=headers)).json()
    for bar in month["bars"]:
        assert "–" in bar["name"] or bar["name"].endswith(
            ("Jan", "Feb", "Mac", "Apr", "Mei", "Jun", "Jul", "Ago", "Sep", "Okt", "Nov", "Des")
        )

    year = (await client.get("/reports/year", headers=headers)).json()
    assert [bar["name"] for bar in year["bars"]][:3] == ["Januari", "Februari", "Machi"]


# ── 7.1 / 7.2 ────────────────────────────────────────────────────────────────

async def test_712_gzip_and_time_header(client, headers):
    res = await client.get(
        "/reports/year", headers={**headers, "Accept-Encoding": "gzip"}
    )
    assert res.status_code == 200
    assert res.headers.get("content-encoding") == "gzip"
    assert int(res.headers["X-Time-Ms"]) >= 0

    unauthorised = await client.get("/me", headers={"Accept-Encoding": "gzip"})
    assert unauthorised.status_code == 401
    assert "X-Time-Ms" in unauthorised.headers
