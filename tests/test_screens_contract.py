"""Mkataba wa screen tano — JSON kamili ya PDF za UMMU.

Huu ni jaribio la mwisho: linatumia products.json halisi (seed ya duka) na
linakagua kila API inayotumiwa na screen, pamoja na fields na thamani zake.
"""

import json
import os
import re
from datetime import date, timedelta
from pathlib import Path

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ["DB_NAME"] = "ummu_ayman_test"
os.environ["JWT_SECRET"] = "test-secret-ndefu-sana-kwa-majaribio"
os.environ["ALLOW_TEST_RESET"] = "true"

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app import auth as auth_mod  # noqa: E402
from app.auth import hash_pin  # noqa: E402
from app.db import create_indexes, db  # noqa: E402
from app.main import app  # noqa: E402
from app.services import stock as stock_service  # noqa: E402
from app.tz import now, today  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DAY1 = "2026-11-17"
DAY2 = "2026-11-20"

SUMMARY_20 = {
    "sales": 794000,
    "capital": 561000,
    "expenses": 5000,
    "product_profit": 233000,
    "net": 228000,
}


@pytest.fixture(autouse=True)
async def shop():
    await db.client.drop_database(db.name)
    await create_indexes()
    auth_mod.reset_attempts()
    result = await db.shops.insert_one(
        {
            "name": "UMMU AYMAN OUTFITS",
            "phone": "0621 340 044",
            "email": "kambilatifah@gmail.com",
            "pin_hash": hash_pin("1234"),
            "receipt_seq": 0,
            "settings": {"low_stock_threshold": 2},
            "created_at": now(),
        }
    )
    yield result.inserted_id


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
async def headers(client):
    res = await client.post("/auth/pin", json={"pin": "1234"})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['token']}"}


async def seed_products(sid) -> dict[str, str]:
    """Ingiza bidhaa zote za products.json (kama scripts/seed_products.py)."""
    items = json.loads((ROOT / "products.json").read_text(encoding="utf-8"))
    ts = now()
    variants: dict[str, str] = {}
    for item in items:
        docs = [
            stock_service.new_variant(v["name"], v["qty"], v["buying"], v["selling"], ts)
            for v in item["variants"]
        ]
        await db.products.insert_one(
            {
                "shop_id": sid,
                "name": item["name"],
                "name_lc": item["name"].lower(),
                "has_types": item["has_types"],
                "variants": docs,
                "created_at": ts,
                "updated_at": ts,
            }
        )
        for variant in docs:
            variants[variant["name"]] = str(variant["_id"])
    return variants


async def seed_sales(client, headers, variants) -> dict:
    """Data ya PDF: 17 Nov, 20 Nov, gharama ya Usafiri na risiti 0001."""
    lines_17 = [
        ("Viatu vya kufunga", 3, 33000),
        ("Abaya nyeusi", 3, 11000),
        ("Alfurqan Kanzu", 2, 65000),
        ("Kofia nyeusi", 2, 22000),
        ("Tasbihi za mbao", 1, 4000),
    ]
    for name, qty, selling in lines_17:
        res = await client.post(
            f"/daily/{DAY1}/lines",
            json={"variant_id": variants[name], "qty": qty, "selling": selling},
            headers=headers,
        )
        assert res.status_code == 200, res.text

    lines_20 = [
        ("Abaya ya Kituruki", 2, 8000),
        ("Kanzu ya Oman", 3, 40000),
        ("Kanzu ya Saudia", 10, 15000),
        ("Mkoba wa ngozi", 3, 45000),
        ("Viatu vya kufunga", 6, 35000),
    ]
    for name, qty, selling in lines_20:
        res = await client.post(
            f"/daily/{DAY2}/lines",
            json={"variant_id": variants[name], "qty": qty, "selling": selling},
            headers=headers,
        )
        assert res.status_code == 200, res.text
    # Bidhaa isiyo kwenye orodha (variant_id null)
    res = await client.post(
        f"/daily/{DAY2}/lines",
        json={"variant_id": None, "name": "Mafuta ya nazi", "qty": 3, "selling": 5000, "buying": 3000},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    res = await client.post(
        f"/daily/{DAY2}/expenses", json={"name": "Usafiri", "amount": 5000}, headers=headers
    )
    assert res.status_code == 200, res.text

    res = await client.post(
        "/receipts",
        json={
            "date": DAY2,
            "customer": {"name": "Said Hamad", "phone": "0712445900"},
            "items": [
                {"variant_id": variants["Alfurqan Kanzu"], "qty": 2, "price": 65000, "discount": 0},
                {"variant_id": variants["Kanga za pwani"], "qty": 2, "price": 9000, "discount": 0},
            ],
        },
        headers=headers,
    )
    assert res.status_code == 201, res.text
    return res.json()


# ── STOCK (K0–K4) ─────────────────────────────────────────────────────────────

async def test_stock_screen_json(client, headers, shop):
    await seed_products(shop)

    res = await client.get("/stock", headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()
    assert set(data) == {"summary", "products"}
    assert data["summary"] == {"products": 16, "variants": 37, "qty": 264, "capital": 3383500}
    names = [p["name"] for p in data["products"]]
    assert names == sorted(names, key=str.lower)
    for product in data["products"]:
        assert set(product) == {"id", "name", "has_variants", "variants", "qty", "capital"}
        assert isinstance(product["variants"], int)  # K0: idadi, si orodha

    abaya = next(p for p in data["products"] if p["name"] == "Abaya")
    assert abaya["has_variants"] is True
    assert (abaya["variants"], abaya["qty"], abaya["capital"]) == (4, 32, 435000)
    mafuta = next(p for p in data["products"] if p["name"] == "Mafuta ya nywele")
    assert (mafuta["has_variants"], mafuta["variants"], mafuta["qty"], mafuta["capital"]) == (
        False,
        1,
        12,
        36000,
    )

    res = await client.get(f"/stock/products/{abaya['id']}", headers=headers)
    assert res.status_code == 200, res.text
    detail = res.json()
    assert set(detail) == {"id", "name", "has_variants", "summary", "variants"}
    assert detail["summary"] == {"qty": 32, "capital": 435000, "profit_if_sold": 208000}
    assert [v["name"] for v in detail["variants"]] == [
        "Abaya ya Kituruki",
        "Abaya ya Dubai",
        "Abaya nyeusi",
        "Abaya ya harusi",
    ]
    assert [v["qty"] for v in detail["variants"]] == [16, 8, 5, 3]
    for variant in detail["variants"]:
        assert set(variant) == {"id", "name", "qty", "buying", "selling"}
    dubai = next(v for v in detail["variants"] if v["name"] == "Abaya ya Dubai")
    assert (dubai["buying"], dubai["selling"]) == (25000, 35000)

    # S0 — orodha ya Mauzo/Risiti: aina zote 37, kwa jina.
    res = await client.get("/products/search-list", headers=headers)
    assert res.status_code == 200, res.text
    listing = res.json()
    assert len(listing) == 37
    spec_keys = {"id", "name", "qty", "buying", "selling"}
    for item in listing:
        assert spec_keys <= set(item)
        assert isinstance(item["qty"], int)
    assert [i["name"] for i in listing] == sorted((i["name"] for i in listing), key=str.lower)
    assert sum(i["qty"] for i in listing) == 264
    assert any(i["name"] == "Mafuta ya nywele" for i in listing)


# ── MAUZO (S1–S8) ─────────────────────────────────────────────────────────────

async def test_mauzo_screen_json(client, headers, shop):
    variants = await seed_products(shop)
    await seed_sales(client, headers, variants)

    res = await client.get(f"/daily/{DAY2}", headers=headers)
    assert res.status_code == 200, res.text
    sheet = res.json()
    assert set(sheet) == {"date", "saved_at", "receipt_lines", "lines", "expenses", "summary"}
    assert sheet["date"] == DAY2
    assert sheet["saved_at"] is None
    assert sheet["summary"] == SUMMARY_20

    assert [l["name"] for l in sheet["lines"]] == [
        "Abaya ya Kituruki",
        "Kanzu ya Oman",
        "Kanzu ya Saudia",
        "Mkoba wa ngozi",
        "Viatu vya kufunga",
        "Mafuta ya nazi",
    ]
    for line in sheet["lines"]:
        assert {"id", "variant_id", "name", "qty", "selling", "buying"} <= set(line)
    assert sheet["lines"][0]["variant_id"] == variants["Abaya ya Kituruki"]
    assert sheet["lines"][-1]["variant_id"] is None
    assert (sheet["lines"][-1]["qty"], sheet["lines"][-1]["selling"]) == (3, 5000)

    assert len(sheet["receipt_lines"]) == 2
    for line in sheet["receipt_lines"]:
        assert {"id", "name", "qty", "selling", "buying", "receipt_no", "receipt_id"} <= set(line)
    assert [l["name"] for l in sheet["receipt_lines"]] == ["Alfurqan Kanzu", "Kanga za pwani"]
    assert [l["selling"] for l in sheet["receipt_lines"]] == [65000, 9000]
    assert {l["receipt_no"] for l in sheet["receipt_lines"]} == {"0001"}

    assert len(sheet["expenses"]) == 1
    expense = sheet["expenses"][0]
    assert set(expense) == {"id", "name", "amount"}
    assert (expense["name"], expense["amount"]) == ("Usafiri", 5000)

    # Siku tupu si 404
    res = await client.get("/daily/2026-11-18", headers=headers)
    assert res.status_code == 200, res.text
    empty = res.json()
    assert empty["lines"] == [] and empty["receipt_lines"] == [] and empty["expenses"] == []
    assert empty["summary"] == {
        "sales": 0,
        "capital": 0,
        "expenses": 0,
        "product_profit": 0,
        "net": 0,
    }

    # S8 — Historia kwa mwezi
    res = await client.get("/daily/history", params={"before": "2026-11-21"}, headers=headers)
    assert res.status_code == 200, res.text
    history = res.json()
    assert set(history) == {"months", "next_before"}
    assert history["months"][0]["label"] == "NOVEMBA 2026"
    day = history["months"][0]["days"][0]
    assert {"date", "label", "sales", "items", "net"} <= set(day)
    assert (day["date"], day["label"]) == (DAY2, "Ijumaa, 20 Nov")
    assert (day["sales"], day["items"], day["net"]) == (794000, 31, 228000)
    assert history["next_before"] is None

    # S6/S7 — Hifadhi na Hariri
    res = await client.post(f"/daily/{DAY2}/close", headers=headers)
    assert res.status_code == 200 and res.json()["saved_at"] is not None
    res = await client.post(
        f"/daily/{DAY2}/lines",
        json={"variant_id": variants["Kofia nyeusi"], "qty": 1, "selling": 22000},
        headers=headers,
    )
    assert res.status_code == 409
    assert res.json()["detail"] == "Siku imehifadhiwa — bonyeza Hariri kwanza"
    res = await client.post(f"/daily/{DAY2}/reopen", headers=headers)
    assert res.status_code == 200 and res.json()["saved_at"] is None

    # R1 / R7 / R9
    res = await client.post(
        f"/daily/{DAY2}/lines",
        json={"variant_id": variants["Kofia nyeusi"], "qty": 0, "selling": 22000},
        headers=headers,
    )
    assert res.status_code == 422 and res.json()["detail"] == "Jaza idadi"
    tomorrow = (today() + timedelta(days=1)).isoformat()
    res = await client.post(
        f"/daily/{tomorrow}/lines",
        json={"variant_id": variants["Kofia nyeusi"], "qty": 1, "selling": 22000},
        headers=headers,
    )
    assert res.status_code == 400 and res.json()["detail"] == "Huwezi kuandika siku ijayo"
    res = await client.patch(
        f"/daily/{DAY2}/lines/hakuna", json={"qty": 1}, headers=headers
    )
    assert res.status_code == 404 and res.json()["detail"] == "Haipo"


# ── NYUMBANI ─────────────────────────────────────────────────────────────────

async def test_home_screen_json(client, headers, shop):
    variants = await seed_products(shop)
    await seed_sales(client, headers, variants)

    res = await client.get("/home", headers=headers)
    assert res.status_code == 200, res.text
    home = res.json()
    assert set(home) == {"day", "summary", "top", "expenses"}
    assert home["day"] == DAY2
    assert home["summary"] == SUMMARY_20
    assert len(home["top"]) == 8
    assert home["top"][0] == {
        "name": "Kanzu ya Saudia",
        "qty": 10,
        "selling": 15000,
        "sales": 150000,
        "capital": 100000,
        "profit": 50000,
    }
    assert [t["qty"] for t in home["top"]] == [10, 6, 3, 3, 3, 2, 2, 2]
    assert home["expenses"] == [{"name": "Usafiri", "amount": 5000}]
    for item in home["top"]:
        assert set(item) == {"name", "qty", "selling", "sales", "capital", "profit"}


# ── RIPOTI (P1–P4) ───────────────────────────────────────────────────────────

async def test_reports_screen_json(client, headers, shop):
    variants = await seed_products(shop)
    await seed_sales(client, headers, variants)
    t = today()

    res = await client.get(f"/reports/day/{DAY2}", headers=headers)
    assert res.status_code == 200, res.text
    report = res.json()
    assert set(report) == {
        "period",
        "date",
        "label",
        "short_label",
        "has_prev",
        "has_next",
        "summary",
        "products",
        "totals",
    }
    assert (report["period"], report["date"]) == ("day", DAY2)
    assert report["label"] == "Ijumaa, 20 Nov 2026"
    assert report["short_label"] == "Ijumaa, 20 Nov"
    assert report["summary"] == SUMMARY_20
    assert report["has_prev"] is True
    assert report["has_next"] is (date(2026, 11, 20) < t)
    assert len(report["products"]) == 8
    assert report["products"][0] == {
        "name": "Kanzu ya Saudia",
        "qty": 10,
        "sales": 150000,
        "capital": 100000,
        "profit": 50000,
    }
    assert set(report["products"][0]) == {"name", "qty", "sales", "capital", "profit"}
    assert report["totals"] == {"qty": 31, "sales": 794000, "profit": 233000}

    res = await client.get("/reports/week", params={"date": DAY1}, headers=headers)
    assert res.status_code == 200, res.text
    week = res.json()
    assert set(week) == {
        "period",
        "start",
        "end",
        "label",
        "short_label",
        "has_prev",
        "has_next",
        "summary",
        "bars",
        "top",
        "low",
        "unsold",
    }
    assert (week["period"], week["start"], week["end"]) == ("week", "2026-11-15", "2026-11-21")
    assert week["label"] == "15 – 21 Novemba 2026"
    assert week["short_label"] == "15 – 21 Nov 2026"
    assert [b["label"] for b in week["bars"]] == ["Jpi", "Jtt", "Jne", "Jtn", "Alh", "Iju", "Jmo"]
    assert [b["key"] for b in week["bars"]][0] == "2026-11-15"
    nets = [b["net"] for b in week["bars"]]
    assert nets[0] == 0 and nets[2] == 82000 and nets[5] == 228000
    assert week["summary"]["net"] == sum(n for n in nets if n is not None)
    assert all(n is None for b, n in zip(week["bars"], nets) if b["key"] > t.isoformat())
    assert len(week["top"]) <= 5 and [p["qty"] for p in week["top"]] == sorted(
        (p["qty"] for p in week["top"]), reverse=True
    )
    for item in week["top"] + week["low"]:
        assert set(item) == {"name", "qty", "profit"}
    for item in week["unsold"]:
        assert set(item) == {"name", "qty", "capital"}
    sold = {p["name"] for p in week["top"] + week["low"]}
    assert not sold & {u["name"] for u in week["unsold"]}

    res = await client.get("/reports/month", params={"date": "2026-11-05"}, headers=headers)
    assert res.status_code == 200, res.text
    month = res.json()
    assert [b["label"] for b in month["bars"]] == ["1–7", "8–14", "15–21", "22–28", "29–30"]
    if t < date(2026, 11, 22):
        assert month["bars"][3]["net"] is None

    res = await client.get("/reports/year", params={"date": DAY2}, headers=headers)
    assert res.status_code == 200, res.text
    year = res.json()
    assert len(year["bars"]) == 12
    assert year["bars"][0]["key"] == "2026-01-01"
    assert year["bars"][10]["label"] == "Nov"
    assert year["bars"][10]["net"] == 310000


# ── RISITI (C0–C3) ───────────────────────────────────────────────────────────

async def test_receipts_screen_json(client, headers, shop):
    variants = await seed_products(shop)
    receipt = await seed_sales(client, headers, variants)

    res = await client.get("/receipts", params={"date": DAY2}, headers=headers)
    assert res.status_code == 200, res.text
    today_list = res.json()
    assert set(today_list) == {"date", "receipts", "count", "total", "next_number"}
    assert (today_list["date"], today_list["count"], today_list["total"]) == (DAY2, 1, 148000)
    assert today_list["next_number"] == "0002"
    row = today_list["receipts"][0]
    assert set(row) == {"id", "number", "customer", "time", "paid"}
    assert (row["number"], row["customer"], row["paid"]) == ("0001", "Said Hamad", 148000)
    assert re.fullmatch(r"\d{2}:\d{2}", row["time"])

    res = await client.get(f"/receipts/{receipt['id']}", headers=headers)
    assert res.status_code == 200, res.text
    one = res.json()
    assert set(one) == {
        "id",
        "number",
        "date",
        "time",
        "customer",
        "items",
        "gross",
        "discount",
        "paid",
        "shop",
    }
    assert (one["number"], one["date"]) == ("0001", DAY2)
    assert one["customer"] == {"name": "Said Hamad", "phone": "0712445900"}
    assert [(i["name"], i["amount"]) for i in one["items"]] == [
        ("Alfurqan Kanzu", 130000),
        ("Kanga za pwani", 18000),
    ]
    for item in one["items"]:
        assert set(item) == {"name", "qty", "price", "discount", "amount"}
    assert (one["gross"], one["discount"], one["paid"]) == (148000, 0, 148000)
    assert one["shop"] == {
        "name": "UMMU AYMAN OUTFITS",
        "phone": "0621 340 044",
        "email": "kambilatifah@gmail.com",
    }

    res = await client.get("/receipts/history", params={"q": "said"}, headers=headers)
    assert res.status_code == 200, res.text
    history = res.json()
    assert [r["number"] for d in history["days"] for r in d["receipts"]] == ["0001"]
    d = date(2026, 11, 20)
    prefix = "LEO · " if d == today() else "JANA · " if d == today() - timedelta(days=1) else ""
    assert history["days"][0]["label"] == f"{prefix}IJUMAA 20 NOV"
    assert history["days"][0]["total"] == 148000

    for q in ("0001", "1", "hamad"):
        res = await client.get("/receipts/history", params={"q": q}, headers=headers)
        assert [r["number"] for day in res.json()["days"] for r in day["receipts"]] == ["0001"]

    # Makosa ya C1
    res = await client.post("/receipts", json={"date": DAY2, "items": []}, headers=headers)
    assert res.status_code == 422 and res.json()["detail"] == "Weka bidhaa angalau moja"
    res = await client.post(
        "/receipts",
        json={
            "date": DAY2,
            "items": [{"variant_id": variants["Kofia nyeusi"], "qty": 1, "price": 11000, "discount": 12000}],
        },
        headers=headers,
    )
    assert res.status_code == 422 and res.json()["detail"] == "Punguzo ni kubwa kuliko bei"
    res = await client.post(
        "/receipts",
        json={"date": DAY2, "items": [{"variant_id": None, "name": "Mafuta", "qty": 1, "price": 5000}]},
        headers=headers,
    )
    assert res.status_code == 422 and res.json()["detail"] == "Jaza buying"
    res = await client.post(
        "/receipts",
        json={
            "date": (today() + timedelta(days=1)).isoformat(),
            "items": [{"variant_id": variants["Kofia nyeusi"], "qty": 1, "price": 11000, "discount": 0}],
        },
        headers=headers,
    )
    assert res.status_code == 400 and res.json()["detail"] == "Huwezi kuandika siku ijayo"


# ── RESET (majaribio ya duka) ────────────────────────────────────────────────

async def test_reset_restores_stock_and_home(client, headers, shop):
    variants = await seed_products(shop)
    await seed_sales(client, headers, variants)

    before = (await client.get("/stock", headers=headers)).json()["summary"]["qty"]
    # 17 Nov: 11 · 20 Nov: 24 (Viatu 6 zilizouzwa, 4 zilizopo) · risiti: 4
    assert before == 227

    res = await client.delete(f"/test/day/{DAY2}", headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["ok"] is True and sum(body["restored"].values()) == 26

    after = (await client.get("/stock", headers=headers)).json()["summary"]["qty"]
    assert after == before + sum(body["restored"].values()) == 253
    assert (await client.get("/home", headers=headers)).json()["day"] == DAY1

    res = await client.delete("/test/sales", headers=headers)
    assert res.status_code == 200 and res.json() == {"ok": True}
    assert (await client.get("/home", headers=headers)).json() == {
        "day": None,
        "summary": None,
        "top": [],
        "expenses": [],
    }
    assert (await client.get("/stock", headers=headers)).json()["summary"]["qty"] == 264
