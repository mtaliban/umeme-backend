"""Majaribio ya mtiririko kamili wa API."""

import os

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ["DB_NAME"] = "ummu_ayman_test"
os.environ["JWT_SECRET"] = "test-secret-ndefu-sana-kwa-majaribio"

import asyncio  # noqa: E402
from datetime import date  # noqa: E402

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app import auth as auth_mod  # noqa: E402
from app.auth import hash_pin  # noqa: E402
from app.db import create_indexes, db  # noqa: E402
from app.main import app  # noqa: E402
from app.tz import DAY_NAMES, now, today  # noqa: E402


@pytest.fixture(scope="session")
def event_loop():
    """Motor client ni ya module moja — majaribio yote yatumie loop moja."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


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
async def token(client):
    res = await client.post("/auth/pin", json={"pin": "1234"})
    assert res.status_code == 200, res.text
    return res.json()["token"]


@pytest.fixture
def headers(token):
    return {"Authorization": f"Bearer {token}"}


async def make_kanzu(client, headers):
    res = await client.post("/products", json={"name": "Kanzu", "has_types": True}, headers=headers)
    assert res.status_code == 200, res.text
    product = res.json()
    alfurqan = (
        await client.post(
            f"/products/{product['id']}/variants",
            json={"name": "Alfurqan Kanzu", "qty": 6, "buying": 50000, "selling": 65000},
            headers=headers,
        )
    ).json()
    oman = (
        await client.post(
            f"/products/{product['id']}/variants",
            json={"name": "Kanzu ya Oman", "qty": 6, "buying": 30000, "selling": 40000},
            headers=headers,
        )
    ).json()
    return product, alfurqan, oman


async def stock_qty(client, headers, product_id, variant_id):
    products = (await client.get("/products", headers=headers)).json()
    for product in products:
        if product["id"] != product_id:
            continue
        for variant in product["variants"]:
            if variant["id"] == variant_id:
                return variant["qty"]
    return None


async def test_health(client):
    res = await client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"ok": True}


async def test_pin_login_and_rate_limit(client):
    ok = await client.post("/auth/pin", json={"pin": "1234"})
    assert ok.status_code == 200
    assert ok.json()["token"]
    assert ok.json()["shop"]["name"] == "UMMU AYMAN OUTFITS"

    no_token = await client.get("/me")
    assert no_token.status_code == 401
    assert no_token.json()["detail"] == "Ingia tena"

    bad = await client.post("/auth/pin", json={"pin": "9999"})
    assert bad.status_code == 401
    assert bad.json()["detail"] == "PIN si sahihi"

    for _ in range(4):
        assert (await client.post("/auth/pin", json={"pin": "9999"})).status_code == 401

    blocked = await client.post("/auth/pin", json={"pin": "1234"})
    assert blocked.status_code == 429
    assert blocked.json()["detail"] == "Subiri dakika 10"


async def test_udi_single_variant_and_duplicate_name(client, headers):
    res = await client.post(
        "/products",
        json={"name": "Udi", "has_types": False, "qty": 4, "buying": 10000, "selling": 15000},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    product = res.json()
    assert product["has_types"] is False
    assert len(product["variants"]) == 1
    assert product["variants"][0]["qty"] == 4

    duplicate = await client.post(
        "/products",
        json={"name": "udi", "has_types": False, "qty": 1, "buying": 1, "selling": 2},
        headers=headers,
    )
    assert duplicate.status_code == 409


async def test_kanzu_with_two_variants(client, headers):
    product, alfurqan, oman = await make_kanzu(client, headers)
    assert product["has_types"] is True
    assert alfurqan["qty"] == 6 and oman["qty"] == 6
    listed = (await client.get("/products", headers=headers)).json()
    kanzu = next(p for p in listed if p["id"] == product["id"])
    assert len(kanzu["variants"]) == 2


async def test_restock_variant(client, headers):
    product, alfurqan, _ = await make_kanzu(client, headers)
    res = await client.patch(
        f"/variants/{alfurqan['id']}", json={"add_qty": 10}, headers=headers
    )
    assert res.status_code == 200, res.text
    assert res.json()["qty"] == 16
    movement = await db.stock_movements.find_one(
        {"variant_id": __import__("bson").ObjectId(alfurqan["id"]), "reason": "restock"}
    )
    assert movement is not None and movement["change"] == 10


async def test_receipt_number_totals_and_stock(client, headers):
    product, alfurqan, oman = await make_kanzu(client, headers)
    res = await client.post(
        "/receipts",
        json={
            "customer": {"name": "Said Hamad", "phone": "0712 445 900"},
            "items": [
                {"variant_id": alfurqan["id"], "qty": 2, "price": 65000, "discount": 5000},
                {"variant_id": oman["id"], "qty": 1, "price": 22000, "discount": 0},
            ],
        },
        headers=headers,
    )
    assert res.status_code == 201, res.text
    receipt = res.json()
    assert receipt["number"] == "0001"
    assert receipt["totals"]["paid"] == 142000
    assert receipt["totals"]["qty"] == 3
    assert receipt["status"] == "paid"
    assert await stock_qty(client, headers, product["id"], alfurqan["id"]) == 4
    assert await stock_qty(client, headers, product["id"], oman["id"]) == 5


async def test_receipt_without_stock_changes_nothing(client, headers):
    product, alfurqan, _ = await make_kanzu(client, headers)
    shop_before = await db.shops.find_one({})
    res = await client.post(
        "/receipts",
        json={
            "customer": {"name": "Said Hamad", "phone": "0712 445 900"},
            "items": [{"variant_id": alfurqan["id"], "qty": 99, "price": 65000, "discount": 0}],
        },
        headers=headers,
    )
    assert res.status_code == 400
    assert "zipo 6 tu" in res.json()["detail"]
    assert await stock_qty(client, headers, product["id"], alfurqan["id"]) == 6
    shop_after = await db.shops.find_one({})
    assert shop_after["receipt_seq"] == shop_before["receipt_seq"]
    assert await db.receipts.count_documents({}) == 0


async def test_daily_shows_receipt_lines(client, headers):
    _, alfurqan, _ = await make_kanzu(client, headers)
    await client.post(
        "/receipts",
        json={
            "customer": {"name": "Said Hamad", "phone": "0712 445 900"},
            "items": [{"variant_id": alfurqan["id"], "qty": 1, "price": 65000, "discount": 5000}],
        },
        headers=headers,
    )
    res = await client.get(f"/daily/{today().isoformat()}", headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()
    assert len(data["receipt_lines"]) == 1
    assert data["receipt_lines"][0]["receipt_no"] == "0001"
    assert data["receipt_lines"][0]["selling"] == 60000
    assert data["saved_at"] is None


async def test_daily_delta_and_revert(client, headers):
    product, alfurqan, oman = await make_kanzu(client, headers)
    third = (
        await client.post(
            "/products",
            json={"name": "Udi", "has_types": False, "qty": 6, "buying": 10000, "selling": 15000},
            headers=headers,
        )
    ).json()
    day = today().isoformat()

    first = await client.put(
        f"/daily/{day}",
        json={
            "lines": [
                {"variant_id": alfurqan["id"], "qty": 2, "selling": 65000},
                {"variant_id": oman["id"], "qty": 3, "selling": 40000},
            ],
            "expenses": [],
        },
        headers=headers,
    )
    assert first.status_code == 200, first.text
    assert await stock_qty(client, headers, product["id"], alfurqan["id"]) == 4
    assert await stock_qty(client, headers, product["id"], oman["id"]) == 3
    assert await stock_qty(client, headers, third["id"], third["variants"][0]["id"]) == 6
    assert first.json()["saved_at"] is not None

    second = await client.put(
        f"/daily/{day}",
        json={"lines": [{"variant_id": alfurqan["id"], "qty": 2, "selling": 65000}], "expenses": []},
        headers=headers,
    )
    assert second.status_code == 200, second.text
    assert await stock_qty(client, headers, product["id"], alfurqan["id"]) == 4
    assert await stock_qty(client, headers, product["id"], oman["id"]) == 6


async def test_daily_expenses_and_net(client, headers):
    _, alfurqan, _ = await make_kanzu(client, headers)
    day = today().isoformat()
    res = await client.put(
        f"/daily/{day}",
        json={
            "lines": [{"variant_id": alfurqan["id"], "qty": 1, "selling": 65000}],
            "expenses": [
                {"name": "Usafirishaji", "amount": 2000},
                {"name": "Bando", "amount": 1000, "mtandao": "Vodacom"},
            ],
        },
        headers=headers,
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["expenses"][1]["mtandao"] == "Vodacom"
    summary = data["summary"]
    assert summary["sales"] == 65000
    assert summary["capital"] == 50000
    assert summary["expenses"] == 3000
    assert summary["net"] == summary["sales"] - summary["capital"] - summary["expenses"]


async def test_home_sold_today(client, headers):
    _, alfurqan, _ = await make_kanzu(client, headers)
    day = today().isoformat()
    await client.post(
        "/receipts",
        json={
            "customer": {"name": "Said Hamad"},
            "items": [{"variant_id": alfurqan["id"], "qty": 2, "price": 65000, "discount": 5000}],
        },
        headers=headers,
    )
    await client.put(
        f"/daily/{day}",
        json={"lines": [{"variant_id": alfurqan["id"], "qty": 1, "selling": 65000}], "expenses": []},
        headers=headers,
    )
    res = await client.get("/home", headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()
    sold = data["sold_today"]
    assert len(sold) == 1
    assert sold[0]["qty"] == 3
    assert data["summary"]["sales"] == 185000
    variant = next(v for p in data["products"] for v in p["variants"] if v["id"] == alfurqan["id"])
    assert variant["sold_today"] == 3
    assert variant["profit_today"] == 35000
    assert variant["qty"] == 3


async def test_cancel_receipt_returns_stock(client, headers):
    product, alfurqan, _ = await make_kanzu(client, headers)
    receipt = (
        await client.post(
            "/receipts",
            json={
                "customer": {"name": "Said Hamad"},
                "items": [{"variant_id": alfurqan["id"], "qty": 2, "price": 65000, "discount": 0}],
            },
            headers=headers,
        )
    ).json()
    assert await stock_qty(client, headers, product["id"], alfurqan["id"]) == 4

    res = await client.post(f"/receipts/{receipt['id']}/cancel", headers=headers)
    assert res.status_code == 200 and res.json()["ok"] is True
    assert await stock_qty(client, headers, product["id"], alfurqan["id"]) == 6
    assert (await client.get("/receipts", headers=headers)).json() == []
    assert (await client.get(f"/reports/day/{today().isoformat()}", headers=headers)).json()["summary"]["sales"] == 0


async def test_week_report(client, headers):
    _, alfurqan, _ = await make_kanzu(client, headers)
    await client.post(
        "/receipts",
        json={
            "customer": {"name": "Said Hamad"},
            "items": [{"variant_id": alfurqan["id"], "qty": 2, "price": 65000, "discount": 5000}],
        },
        headers=headers,
    )
    res = await client.get("/reports/week", headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()
    assert len(data["rows"]) == today().weekday() + 1
    assert all(row["key"] <= today().isoformat() for row in data["rows"])
    assert sum(row["sales"] for row in data["rows"]) == data["summary"]["sales"] == 120000
    assert sum(row["net"] for row in data["rows"]) == data["summary"]["net"]
    assert [row["short"] for row in data["rows"]][0] == "Jtt"


async def test_month_and_year_rows(client, headers):
    month = (await client.get("/reports/month", headers=headers)).json()
    expected = min((today().day - 1) // 7 + 1, 5)
    assert len(month["rows"]) == expected
    assert month["rows"][0]["label"] == "Wiki 1"

    year = (await client.get("/reports/year", headers=headers)).json()
    assert len(year["rows"]) == today().month
    assert year["rows"][-1]["current"] is True


async def test_day_report(client, headers):
    _, alfurqan, _ = await make_kanzu(client, headers)
    day = today().isoformat()
    await client.post(
        "/receipts",
        json={
            "customer": {"name": "Said Hamad"},
            "items": [{"variant_id": alfurqan["id"], "qty": 1, "price": 65000, "discount": 5000}],
        },
        headers=headers,
    )
    home = (await client.get("/home", headers=headers)).json()
    report = (await client.get(f"/reports/day/{day}", headers=headers)).json()
    assert report["summary"] == home["summary"]
    assert report["date"] == day
    assert report["label"].startswith(DAY_NAMES[today().weekday()])
    assert report["items"][0]["name"] == "Alfurqan Kanzu"
    assert report["items"][0]["profit"] == 10000


async def test_delete_last_variant_deletes_product(client, headers):
    product = (
        await client.post("/products", json={"name": "Kanzu", "has_types": True}, headers=headers)
    ).json()
    variant = (
        await client.post(
            f"/products/{product['id']}/variants",
            json={"name": "Alfurqan Kanzu", "qty": 1, "buying": 50000, "selling": 65000},
            headers=headers,
        )
    ).json()
    res = await client.delete(f"/variants/{variant['id']}", headers=headers)
    assert res.status_code == 204
    assert (await client.get("/products", headers=headers)).json() == []


async def test_add_variant_converts_single_variant_product(client, headers):
    product = (
        await client.post(
            "/products",
            json={"name": "Udi", "has_types": False, "qty": 2, "buying": 10000, "selling": 15000},
            headers=headers,
        )
    ).json()
    res = await client.post(
        f"/products/{product['id']}/variants",
        json={"name": "Udi nyeupe", "qty": 3, "buying": 12000, "selling": 18000},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    listed = (await client.get("/products", headers=headers)).json()
    udi = next(p for p in listed if p["id"] == product["id"])
    assert udi["has_types"] is True
    assert [v["name"] for v in udi["variants"]] == ["Udi", "Udi nyeupe"]


async def test_variant_search_matches_word_starts(client, headers):
    product = (
        await client.post("/products", json={"name": "Kanzu", "has_types": True}, headers=headers)
    ).json()
    await client.post(
        f"/products/{product['id']}/variants",
        json={"name": "Abaya nyeusi", "qty": 4, "buying": 20000, "selling": 30000},
        headers=headers,
    )
    found = (await client.get("/variants/search", params={"q": "aba ny"}, headers=headers)).json()
    assert len(found) == 1 and found[0]["name"] == "Abaya nyeusi"
    partial = (await client.get("/variants/search", params={"q": "nyeu"}, headers=headers)).json()
    assert partial[0]["name"] == "Abaya nyeusi"
    none = (await client.get("/variants/search", params={"q": "baya"}, headers=headers)).json()
    assert none == []


async def test_expense_names_returns_list(client, headers):
    await client.put(
        f"/daily/{today().isoformat()}",
        json={"lines": [], "expenses": [{"name": "Bando", "amount": 1000}]},
        headers=headers,
    )
    names = (await client.get("/expenses/names", headers=headers)).json()
    assert isinstance(names, list)
    assert names[0] == "Bando"
    assert "Usafirishaji" in names


async def test_extra_fields_are_preserved(client, headers):
    product = (
        await client.post(
            "/products",
            json={
                "name": "Kanzu",
                "has_types": False,
                "qty": 2,
                "buying": 1000,
                "selling": 2000,
                "supplier": "Dubai",
            },
            headers=headers,
        )
    ).json()
    assert product["supplier"] == "Dubai"
    variant = product["variants"][0]
    receipt = (
        await client.post(
            "/receipts",
            json={
                "customer": {"name": "Said", "note": "mteja wa kudumu"},
                "items": [{"variant_id": variant["id"], "qty": 1, "price": 2000, "discount": 0}],
            },
            headers=headers,
        )
    ).json()
    assert receipt["customer"]["note"] == "mteja wa kudumu"
    saved = (await client.get(f"/receipts/{receipt['id']}", headers=headers)).json()
    assert saved["customer"]["note"] == "mteja wa kudumu"


async def test_validation_error_detail_is_string(client, headers):
    res = await client.post("/products", json={"has_types": False}, headers=headers)
    assert res.status_code == 422
    assert isinstance(res.json()["detail"], str)
    assert res.json()["detail"].startswith("name:")


async def test_stock_never_negative(client, headers):
    product, alfurqan, _ = await make_kanzu(client, headers)
    day = today().isoformat()
    res = await client.put(
        f"/daily/{day}",
        json={"lines": [{"variant_id": alfurqan["id"], "qty": 9, "selling": 65000}], "expenses": []},
        headers=headers,
    )
    assert res.status_code == 400
    assert await stock_qty(client, headers, product["id"], alfurqan["id"]) == 6
    assert await db.daily_sheets.count_documents({}) == 0
