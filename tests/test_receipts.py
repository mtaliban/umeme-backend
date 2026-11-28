"""Majaribio ya RISITI (C0–C3) — UMMU-RISITI, sehemu A5."""

import os
import re
from datetime import timedelta

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ["DB_NAME"] = "ummu_ayman_test"
os.environ["JWT_SECRET"] = "test-secret-ndefu-sana-kwa-majaribio"

import pytest  # noqa: E402
from bson import ObjectId  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app import auth as auth_mod  # noqa: E402
from app.auth import hash_pin  # noqa: E402
from app.db import create_indexes, db  # noqa: E402
from app.main import app  # noqa: E402
from app.tz import now, today  # noqa: E402

DAY = "2026-11-20"


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


async def sid():
    return (await db.shops.find_one({}))["_id"]


async def add_stock(name, qty, buying, selling):
    pid, vid = ObjectId(), ObjectId()
    await db.products.insert_one(
        {
            "shop_id": await sid(),
            "name": name,
            "name_lc": name.lower(),
            "has_types": False,
            "variants": [
                {
                    "_id": vid,
                    "name": name,
                    "name_lc": name.lower(),
                    "qty": qty,
                    "buying": buying,
                    "selling": selling,
                    "created_at": now(),
                }
            ],
            "created_at": now(),
            "updated_at": now(),
        }
    )
    return str(vid)


async def qty_of(variant_id):
    pid = (await db.products.find_one({"variants._id": ObjectId(variant_id)}))["_id"]
    product = await db.products.find_one({"_id": pid})
    return next(v["qty"] for v in product["variants"] if v["_id"] == ObjectId(variant_id))


async def received(client, headers, date, items, name="Said Hamad", phone="0712445900"):
    return await client.post(
        "/receipts",
        json={
            "date": date,
            "customer": {"name": name, "phone": phone},
            "items": items,
        },
        headers=headers,
    )


async def test_today_list_empty(client, headers):
    data = (await client.get("/receipts", params={"date": DAY}, headers=headers)).json()
    assert data == {
        "date": DAY,
        "receipts": [],
        "count": 0,
        "total": 0,
        "next_number": "0001",
    }


async def test_create_receipt_contract(client, headers):
    abaya = await add_stock("Abaya nyeusi", 5, 7000, 11000)
    kofia = await add_stock("Kofia nyeusi", 3, 15000, 22000)

    res = await received(
        client,
        headers,
        DAY,
        [
            {"variant_id": abaya, "qty": 2, "price": 11000, "discount": 1000},
            {"variant_id": kofia, "qty": 1, "price": 22000, "discount": 0},
        ],
    )
    assert res.status_code == 201, res.text
    receipt = res.json()

    assert set(receipt) == {
        "id",
        "number",
        "date",
        "time",
        "customer",
        "items",
        "total_qty",
        "gross",
        "discount",
        "paid",
        "shop",
    }
    assert receipt["total_qty"] == 3
    assert receipt["number"] == "0001"
    assert receipt["date"] == DAY
    assert re.match(r"^\d{2}:\d{2}$", receipt["time"])
    assert receipt["gross"] == 44000
    assert receipt["discount"] == 2000
    assert receipt["paid"] == 42000
    assert receipt["items"][0] == {
        "name": "Abaya nyeusi",
        "category": "Abaya nyeusi",
        "qty": 2,
        "price": 11000,
        "discount": 1000,
        "amount": 20000,
    }
    assert receipt["customer"] == {
        "name": "Said Hamad",
        "phone": "0712445900",
        "location": "",
        "address": "",
    }
    assert receipt["shop"] == {
        "name": "UMMU AYMAN OUTFITS",
        "phone": "0621 340 044",
        "email": "kambilatifah@gmail.com",
        "signature_name": "Ummu Ayman",
    }

    assert await qty_of(abaya) == 3
    assert await qty_of(kofia) == 2

    today_list = (await client.get("/receipts", params={"date": DAY}, headers=headers)).json()
    assert today_list["count"] == 1
    assert today_list["total"] == 42000
    assert today_list["next_number"] == "0002"
    assert today_list["receipts"][0] == {
        "id": receipt["id"],
        "number": "0001",
        "date": DAY,
        "customer": "Said Hamad",
        "location": "",
        "time": receipt["time"],
        "total_qty": 3,
        "gross": 44000,
        "discount": 2000,
        "paid": 42000,
        "shop": receipt["shop"],
    }


async def test_qty_beyond_stock_is_clamped(client, headers):
    abaya = await add_stock("Abaya nyeusi", 5, 7000, 11000)

    res = await received(
        client, headers, DAY, [{"variant_id": abaya, "qty": 7, "price": 11000, "discount": 0}]
    )
    assert res.status_code == 201, res.text
    assert res.json()["paid"] == 77000
    assert await qty_of(abaya) == 0

    saved = await db.receipts.find_one({"_id": ObjectId(res.json()["id"])})
    assert saved["items"][0]["stock_taken"] == 5


async def test_empty_items_422(client, headers):
    res = await client.post(
        "/receipts", json={"date": DAY, "customer": {"name": "Said"}, "items": []}, headers=headers
    )
    assert res.status_code == 422
    assert res.json()["detail"] == "Weka bidhaa angalau moja"


async def test_discount_above_price_422(client, headers):
    kofia = await add_stock("Kofia nyeusi", 3, 15000, 22000)
    res = await received(
        client, headers, DAY, [{"variant_id": kofia, "qty": 1, "price": 11000, "discount": 12000}]
    )
    assert res.status_code == 422
    assert res.json()["detail"] == "Punguzo ni kubwa kuliko bei"


async def test_off_stock_item_requires_buying(client, headers):
    res = await received(
        client,
        headers,
        DAY,
        [{"variant_id": None, "name": "Mafuta ya nazi", "qty": 1, "price": 5000, "discount": 0}],
    )
    assert res.status_code == 422
    assert res.json()["detail"] == "Jaza buying"

    ok = await received(
        client,
        headers,
        DAY,
        [
            {
                "variant_id": None,
                "name": "Mafuta ya nazi",
                "qty": 1,
                "price": 5000,
                "discount": 0,
                "buying": 3000,
            }
        ],
    )
    assert ok.status_code == 201, ok.text
    assert ok.json()["items"][0]["amount"] == 5000
    assert await db.products.count_documents({}) == 0


async def test_numbers_increment_and_order(client, headers):
    abaya = await add_stock("Abaya nyeusi", 20, 7000, 11000)
    for _ in range(3):
        res = await received(
            client, headers, DAY, [{"variant_id": abaya, "qty": 1, "price": 11000, "discount": 0}]
        )
        assert res.status_code == 201, res.text

    data = (await client.get("/receipts", params={"date": DAY}, headers=headers)).json()
    assert [r["number"] for r in data["receipts"]] == ["0003", "0002", "0001"]
    assert data["count"] == 3
    assert data["total"] == 33000
    assert data["next_number"] == "0004"


async def test_get_receipt_matches_post(client, headers):
    abaya = await add_stock("Abaya nyeusi", 5, 7000, 11000)
    created = (
        await received(
            client, headers, DAY, [{"variant_id": abaya, "qty": 2, "price": 11000, "discount": 1000}]
        )
    ).json()

    fetched = (await client.get(f"/receipts/{created['id']}", headers=headers)).json()
    assert fetched == created
    missing = await client.get("/receipts/665f1c1c1c1c1c1c1c1c1c1c", headers=headers)
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Haipo"


async def test_empty_customer_shows_mteja(client, headers):
    abaya = await add_stock("Abaya nyeusi", 5, 7000, 11000)
    res = await client.post(
        "/receipts",
        json={
            "date": DAY,
            "customer": {"name": "", "phone": ""},
            "items": [{"variant_id": abaya, "qty": 1, "price": 11000, "discount": 0}],
        },
        headers=headers,
    )
    assert res.status_code == 201, res.text
    assert res.json()["customer"] == {
        "name": "",
        "phone": "",
        "location": "",
        "address": "",
    }
    data = (await client.get("/receipts", params={"date": DAY}, headers=headers)).json()
    assert data["receipts"][0]["customer"] == "Mteja"


async def test_history_search_and_labels(client, headers):
    abaya = await add_stock("Abaya nyeusi", 20, 7000, 11000)
    t = today()
    for day, name in (
        (t.isoformat(), "Said Hamad"),
        ((t - timedelta(days=1)).isoformat(), "Neema Ally"),
        ("2026-11-18", "Hassan Omar"),
    ):
        res = await received(
            client,
            headers,
            day,
            [{"variant_id": abaya, "qty": 1, "price": 11000, "discount": 0}],
            name=name,
        )
        assert res.status_code == 201, res.text

    data = (await client.get("/receipts/history", headers=headers)).json()
    assert [d["date"] for d in data["days"]] == [t.isoformat(), (t - timedelta(days=1)).isoformat(), "2026-11-18"]
    assert data["days"][0]["label"].startswith("LEO · ")
    assert data["days"][1]["label"].startswith("JANA · ")
    assert data["days"][2]["label"].startswith("JUMATANO 18 NOV")
    assert data["next_before"] is None
    assert all(
        {"id", "number", "date", "customer", "time", "paid"} <= set(r)
        for d in data["days"]
        for r in d["receipts"]
    )

    by_name = (await client.get("/receipts/history", params={"q": "hamad"}, headers=headers)).json()
    nums = [r["number"] for d in by_name["days"] for r in d["receipts"]]
    assert nums == ["0001"]

    by_number = (await client.get("/receipts/history", params={"q": "0001"}, headers=headers)).json()
    assert [r["number"] for d in by_number["days"] for r in d["receipts"]] == ["0001"]
    short = (await client.get("/receipts/history", params={"q": "1"}, headers=headers)).json()
    assert [r["number"] for d in short["days"] for r in d["receipts"]] == ["0001"]


async def test_receipt_lines_in_daily(client, headers):
    abaya = await add_stock("Abaya nyeusi", 5, 7000, 11000)
    await received(
        client, headers, DAY, [{"variant_id": abaya, "qty": 2, "price": 11000, "discount": 1000}]
    )

    daily = (await client.get(f"/daily/{DAY}", headers=headers)).json()
    assert len(daily["receipt_lines"]) == 1
    line = daily["receipt_lines"][0]
    assert line["receipt_no"] == "0001"
    assert line["selling"] == 10000
    assert daily["summary"]["sales"] == 20000


async def test_future_date_400(client, headers):
    abaya = await add_stock("Abaya nyeusi", 5, 7000, 11000)
    tomorrow = (today() + timedelta(days=1)).isoformat()
    res = await received(
        client, headers, tomorrow, [{"variant_id": abaya, "qty": 1, "price": 11000, "discount": 0}]
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "Huwezi kuandika siku ijayo"
