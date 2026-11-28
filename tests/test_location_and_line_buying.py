"""Majaribio 17 na 18 — `customer.location` na `buying` ya mstari wa daftari."""

import os

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


async def shop_id():
    return (await db.shops.find_one({}))["_id"]


async def add_stock(name, qty, buying, selling):
    """Bidhaa bila aina (variant moja) — hurudisha (product_id, variant_id)."""
    pid, vid = ObjectId(), ObjectId()
    await db.products.insert_one(
        {
            "_id": pid,
            "shop_id": await shop_id(),
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
    return str(pid), str(vid)


def receipt_body(variant_id, qty=1, price=22000, discount=0, customer=None):
    body = {"items": [{"variant_id": variant_id, "qty": qty, "price": price, "discount": discount}]}
    if customer is not None:
        body["customer"] = customer
    return body


# ── 17 — customer.location kwenye risiti ─────────────────────────────────────

async def test_17_receipt_customer_location(client, headers):
    _, vid = await add_stock("Kofia nyeusi", 20, 15000, 22000)
    day = today().isoformat()

    # 1. Bila location → 201, huhifadhiwa "" (sio None, sio 422)
    res = await client.post("/receipts", json=receipt_body(vid), headers=headers)
    assert res.status_code == 201, res.text
    first = res.json()
    assert first["customer"] == {
        "name": "",
        "phone": "",
        "location": "",
        "address": "",
    }
    one = (await client.get(f"/receipts/{first['id']}", headers=headers)).json()
    assert one["customer"]["location"] == ""
    assert one["customer"]["location"] is not None
    saved = await db.receipts.find_one({"_id": ObjectId(first["id"])})
    assert saved["customer"]["location"] == ""

    # 2. location inatrimwa (na kukatwa kwa herufi 120)
    res = await client.post(
        "/receipts",
        json=receipt_body(vid, customer={"name": "Said Hamad", "location": "  Kariakoo, Dar  "}),
        headers=headers,
    )
    assert res.status_code == 201, res.text
    second = res.json()
    assert second["customer"]["location"] == "Kariakoo, Dar"

    long_location = "M" * 130
    res = await client.post(
        "/receipts",
        json=receipt_body(vid, customer={"name": "Neema Ally", "location": long_location}),
        headers=headers,
    )
    assert res.status_code == 201, res.text
    assert res.json()["customer"]["location"] == "M" * 120

    # 3. GET /receipts?date= inarudisha location ile ile
    today_list = (await client.get("/receipts", params={"date": day}, headers=headers)).json()
    by_id = {row["id"]: row for row in today_list["receipts"]}
    assert by_id[second["id"]]["location"] == "Kariakoo, Dar"
    assert by_id[first["id"]]["location"] == ""
    assert by_id[second["id"]]["customer"] == "Said Hamad"

    # Location haigusi totals
    assert second["paid"] == 22000
    assert today_list["total"] == 3 * 22000

    # 8. Risiti ya zamani isiyo na location → ""
    legacy_id = ObjectId()
    await db.receipts.insert_one(
        {
            "_id": legacy_id,
            "shop_id": await shop_id(),
            "number": "0900",
            "date": day,
            "time": "10:00",
            "created_at": now(),
            "status": "paid",
            "customer": {"name": "Mzee Juma", "phone": "0700"},
            "items": [{"name": "Kofia nyeusi", "qty": 1, "price": 22000, "discount": 0, "buying": 15000}],
            "totals": {"qty": 1, "gross": 22000, "discount": 0, "paid": 22000, "capital": 15000},
        }
    )
    legacy = (await client.get(f"/receipts/{legacy_id}", headers=headers)).json()
    assert legacy["customer"]["location"] == ""


# ── 18 — buying ya mstari wa daftari (snapshot) ─────────────────────────────

async def test_18_daily_line_buying_snapshot(client, headers):
    pid, vid = await add_stock("Kofia nyeusi", 10, 15000, 22000)
    day = today().isoformat()

    # 4. buying ya mstari = 18000; stock buying bado 15000
    res = await client.post(
        f"/daily/{day}/lines",
        json={"variant_id": vid, "qty": 2, "selling": 22000, "buying": 18000},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    data = res.json()
    line = data["lines"][0]
    assert line["buying"] == 18000
    assert data["summary"]["sales"] == 44000
    assert data["summary"]["capital"] == 36000
    assert data["summary"]["product_profit"] == 2 * (22000 - 18000)
    assert data["summary"]["net"] == 8000

    detail = (await client.get(f"/stock/products/{pid}", headers=headers)).json()
    row = next(v for v in detail["variants"] if v["id"] == vid)
    assert row["buying"] == 15000
    assert row["qty"] == 8
    assert row["selling"] == 22000

    # 5. PATCH buying → mstari pekee; hesabu zote zinasasishwa
    res = await client.patch(
        f"/daily/{day}/lines/{line['id']}", json={"buying": 16000}, headers=headers
    )
    assert res.status_code == 200, res.text
    patched = res.json()
    assert patched["lines"][0]["buying"] == 16000
    assert patched["summary"]["capital"] == 32000
    assert patched["summary"]["net"] == 12000

    detail = (await client.get(f"/stock/products/{pid}", headers=headers)).json()
    assert next(v for v in detail["variants"] if v["id"] == vid)["buying"] == 15000

    home = (await client.get("/home", headers=headers)).json()
    assert home["summary"]["net"] == 12000
    assert home["top"][0]["profit"] == 12000
    assert home["top"][0]["capital"] == 32000

    report = (await client.get(f"/reports/day/{day}", headers=headers)).json()
    assert report["summary"]["net"] == 12000
    assert report["products"][0]["profit"] == 12000
    assert report["products"][0]["capital"] == 32000

    # Bila buying → variants.buying ya sasa
    res = await client.post(
        f"/daily/{day}/lines",
        json={"variant_id": vid, "qty": 1, "selling": 22000},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["lines"][1]["buying"] == 15000
    assert data["summary"]["capital"] == 32000 + 15000

    # 6. lines[].buying na receipt_lines[].buying zipo kwa mistari yote
    res = await client.post(
        "/receipts",
        json={
            "customer": {"name": "Said Hamad", "location": "Kariakoo, Dar"},
            "items": [{"variant_id": vid, "qty": 1, "price": 22000, "discount": 0}],
        },
        headers=headers,
    )
    assert res.status_code == 201, res.text
    data = (await client.get(f"/daily/{day}", headers=headers)).json()
    assert all("buying" in line for line in data["lines"])
    assert all("buying" in line for line in data["receipt_lines"])
    assert data["receipt_lines"][0]["buying"] == 15000

    # Bidhaa isiyo stock: buying > 0 ni lazima
    res = await client.post(
        f"/daily/{day}/lines",
        json={"variant_id": None, "name": "Mafuta ya nazi", "qty": 1, "selling": 5000},
        headers=headers,
    )
    assert res.status_code == 422
    assert res.json()["detail"] == "Jaza buying"

    res = await client.post(
        f"/daily/{day}/lines",
        json={"variant_id": None, "name": "Mafuta ya nazi", "qty": 1, "selling": 5000, "buying": 0},
        headers=headers,
    )
    assert res.status_code == 422
    assert res.json()["detail"] == "Jaza buying"


async def test_18_legacy_line_reads_variant_buying(client, headers):
    """8. Mstari wa zamani usio na `buying` unasomwa kama variants.buying."""
    pid, vid = await add_stock("Kofia nyeusi", 5, 15000, 22000)
    day = today().isoformat()
    await db.daily_sheets.insert_one(
        {
            "shop_id": await shop_id(),
            "date": day,
            "saved_at": None,
            "updated_at": now(),
            "lines": [
                {
                    "id": "legacy",
                    "variant_id": ObjectId(vid),
                    "product_id": ObjectId(pid),
                    "name": "Kofia nyeusi",
                    "qty": 2,
                    "selling": 22000,
                    "stock_selling": 22000,
                    "stock_taken": 2,
                    "out_of_stock": False,
                }
            ],
            "expenses": [],
        }
    )

    data = (await client.get(f"/daily/{day}", headers=headers)).json()
    assert data["lines"][0]["buying"] == 15000
    assert data["summary"]["capital"] == 30000
