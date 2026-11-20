"""Majaribio ya STOCK (K0–K4) — UMMU-STOCK, sehemu A5."""

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
from app.tz import now  # noqa: E402


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


async def add_abaya(client, headers):
    res = await client.post(
        "/stock/products", json={"name": "Abaya", "has_variants": True}, headers=headers
    )
    assert res.status_code == 200, res.text
    return res.json()


async def add_variant(client, headers, pid, name, qty, buying, selling):
    res = await client.post(
        f"/stock/products/{pid}/variants",
        json={"name": name, "qty": qty, "buying": buying, "selling": selling},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    return res.json()


async def test_empty_stock(client, headers):
    res = await client.get("/stock", headers=headers)
    assert res.status_code == 200, res.text
    assert res.json() == {
        "summary": {"products": 0, "variants": 0, "qty": 0, "capital": 0},
        "products": [],
    }


async def test_new_product_with_variants_is_empty(client, headers):
    product = await add_abaya(client, headers)
    assert product == {
        "id": product["id"],
        "name": "Abaya",
        "has_variants": True,
        "summary": {"qty": 0, "capital": 0, "profit_if_sold": 0},
        "variants": [],
    }


async def test_four_variants_summary_and_order(client, headers):
    product = await add_abaya(client, headers)
    pid = product["id"]
    await add_variant(client, headers, pid, "Abaya ya Kituruki", 16, 5000, 8000)
    await add_variant(client, headers, pid, "Abaya ya Dubai", 8, 25000, 35000)
    await add_variant(client, headers, pid, "Abaya nyeusi", 5, 7000, 11000)
    detail = await add_variant(client, headers, pid, "Abaya ya harusi", 3, 40000, 60000)

    assert set(detail) == {"id", "name", "has_variants", "summary", "variants"}
    assert detail["summary"] == {"qty": 32, "capital": 435000, "profit_if_sold": 208000}
    assert detail["variants"][0]["name"] == "Abaya ya Kituruki"
    assert [v["qty"] for v in detail["variants"]] == [16, 8, 5, 3]
    for variant in detail["variants"]:
        assert set(variant) == {"id", "name", "qty", "buying", "selling"}


async def test_duplicate_variant_name(client, headers):
    product = await add_abaya(client, headers)
    await add_variant(client, headers, product["id"], "Abaya nyeusi", 5, 7000, 11000)
    res = await client.post(
        f"/stock/products/{product['id']}/variants",
        json={"name": "abaya nyeusi", "qty": 1, "buying": 7000, "selling": 11000},
        headers=headers,
    )
    assert res.status_code == 409
    assert res.json()["detail"] == "Aina hii ipo tayari"


async def test_duplicate_product_name(client, headers):
    await add_abaya(client, headers)
    res = await client.post(
        "/stock/products", json={"name": "abaya", "has_variants": True}, headers=headers
    )
    assert res.status_code == 409
    assert res.json()["detail"] == "Bidhaa hii ipo tayari"


async def test_product_without_variants(client, headers):
    res = await client.post(
        "/stock/products",
        json={
            "name": "Mafuta ya nywele",
            "has_variants": False,
            "qty": 12,
            "buying": 3000,
            "selling": 5000,
        },
        headers=headers,
    )
    assert res.status_code == 200, res.text
    product = res.json()
    assert product["has_variants"] is False
    assert len(product["variants"]) == 1
    assert product["variants"][0]["name"] == "Mafuta ya nywele"
    assert product["summary"] == {"qty": 12, "capital": 36000, "profit_if_sold": 24000}


async def test_new_product_without_selling_is_422(client, headers):
    res = await client.post(
        "/stock/products",
        json={"name": "Mafuta ya nywele", "has_variants": False, "qty": 12, "buying": 3000},
        headers=headers,
    )
    assert res.status_code == 422
    assert res.json()["detail"] == "Jaza selling"


async def test_variant_on_single_product_is_400(client, headers):
    res = await client.post(
        "/stock/products",
        json={
            "name": "Mafuta ya nywele",
            "has_variants": False,
            "qty": 12,
            "buying": 3000,
            "selling": 5000,
        },
        headers=headers,
    )
    pid = res.json()["id"]
    res = await client.post(
        f"/stock/products/{pid}/variants",
        json={"name": "Mafuta ya nazi", "qty": 1, "buying": 3000, "selling": 5000},
        headers=headers,
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "Bidhaa hii haina aina"


async def test_restock_records_movement(client, headers):
    product = await add_abaya(client, headers)
    detail = await add_variant(client, headers, product["id"], "Abaya nyeusi", 5, 7000, 11000)
    vid = detail["variants"][0]["id"]

    res = await client.patch(f"/stock/variants/{vid}", json={"add_qty": 10}, headers=headers)
    assert res.status_code == 200, res.text
    detail = res.json()
    assert detail["variants"][0]["qty"] == 15

    movement = await db.stock_movements.find_one(
        {"variant_id": ObjectId(vid), "reason": "restock"}
    )
    assert movement is not None
    assert movement["delta"] == 10


async def test_price_change_keeps_qty(client, headers):
    product = await add_abaya(client, headers)
    detail = await add_variant(client, headers, product["id"], "Abaya nyeusi", 5, 7000, 11000)
    vid = detail["variants"][0]["id"]

    res = await client.patch(f"/stock/variants/{vid}", json={"selling": 12000}, headers=headers)
    assert res.status_code == 200, res.text
    variant = res.json()["variants"][0]
    assert variant["selling"] == 12000
    assert variant["qty"] == 5


async def test_stock_list_sorted_with_totals(client, headers):
    product = await add_abaya(client, headers)
    pid = product["id"]
    await add_variant(client, headers, pid, "Abaya ya Kituruki", 16, 5000, 8000)
    await add_variant(client, headers, pid, "Abaya ya Dubai", 8, 25000, 35000)
    await add_variant(client, headers, pid, "Abaya nyeusi", 5, 7000, 11000)
    await add_variant(client, headers, pid, "Abaya ya harusi", 3, 40000, 60000)
    await client.post(
        "/stock/products",
        json={
            "name": "Mafuta ya nywele",
            "has_variants": False,
            "qty": 12,
            "buying": 3000,
            "selling": 5000,
        },
        headers=headers,
    )

    data = (await client.get("/stock", headers=headers)).json()
    assert data["summary"] == {"products": 2, "variants": 5, "qty": 44, "capital": 471000}
    assert [p["name"] for p in data["products"]] == ["Abaya", "Mafuta ya nywele"]
    abaya = data["products"][0]
    assert set(abaya) == {"id", "name", "has_variants", "variants", "qty", "capital"}
    assert abaya["variants"] == 4
    assert abaya["qty"] == 32
    assert abaya["capital"] == 435000


async def test_search_list_reads_stock_variants(client, headers):
    product = await add_abaya(client, headers)
    pid = product["id"]
    await add_variant(client, headers, pid, "Abaya ya Kituruki", 16, 5000, 8000)
    await add_variant(client, headers, pid, "Abaya ya Dubai", 8, 25000, 35000)
    await add_variant(client, headers, pid, "Abaya nyeusi", 5, 7000, 11000)
    await add_variant(client, headers, pid, "Abaya ya harusi", 3, 40000, 60000)
    await client.post(
        "/stock/products",
        json={
            "name": "Mafuta ya nywele",
            "has_variants": False,
            "qty": 12,
            "buying": 3000,
            "selling": 5000,
        },
        headers=headers,
    )

    listed = (await client.get("/products/search-list", headers=headers)).json()
    names = [item["name"] for item in listed]
    assert "Mafuta ya nywele" in names
    assert sorted((n for n in names if n.startswith("Abaya")), key=str.lower) == [
        "Abaya nyeusi",
        "Abaya ya Dubai",
        "Abaya ya harusi",
        "Abaya ya Kituruki",
    ]
