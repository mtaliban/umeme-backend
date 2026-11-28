"""Majaribio ya RIPOTI (P1–P4) — UMMU-RIPOTI, sehemu A4."""

import os

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ["DB_NAME"] = "ummu_ayman_test"
os.environ["JWT_SECRET"] = "test-secret-ndefu-sana-kwa-majaribio"

import pytest  # noqa: E402
from bson import ObjectId  # noqa: E402
from datetime import date  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app import auth as auth_mod  # noqa: E402
from app.auth import hash_pin  # noqa: E402
from app.db import create_indexes, db  # noqa: E402
from app.main import app  # noqa: E402
from app.tz import now, today  # noqa: E402

DAY_17 = "2026-11-17"
DAY_20 = "2026-11-20"


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


async def add_sheet(day, lines=(), expenses=()):
    await db.daily_sheets.insert_one(
        {
            "shop_id": await sid(),
            "date": day,
            "saved_at": None,
            "updated_at": now(),
            "lines": [
                {
                    "id": f"l{i}",
                    "name": name,
                    "qty": qty,
                    "selling": selling,
                    "buying": buying,
                    "variant_id": None,
                    "product_id": None,
                    "stock_taken": 0,
                    "out_of_stock": False,
                    "stock_selling": selling,
                }
                for i, (name, qty, selling, buying) in enumerate(lines)
            ],
            "expenses": [
                {"id": f"e{i}", "name": name, "amount": amount, "created_at": now()}
                for i, (name, amount) in enumerate(expenses)
            ],
        }
    )


async def add_receipt(day, number, items, status="paid", cancelled=False):
    await db.receipts.insert_one(
        {
            "shop_id": await sid(),
            "date": day,
            "number": number,
            "status": status,
            "cancelled": cancelled,
            "created_at": now(),
            "totals": {
                "paid": sum(qty * (price - discount) for _, qty, price, discount, _ in items),
                "capital": sum(qty * buying for _, qty, _, _, buying in items),
            },
            "items": [
                {
                    "name": name,
                    "qty": qty,
                    "price": price,
                    "discount": discount,
                    "buying": buying,
                    "variant_id": None,
                    "product_id": None,
                }
                for name, qty, price, discount, buying in items
            ],
        }
    )


async def seed_day_17():
    await add_sheet(
        DAY_17,
        [
            ("Viatu vya kufunga", 3, 33000, 25000),
            ("Abaya nyeusi", 3, 11000, 7000),
            ("Alfurqan Kanzu", 2, 65000, 50000),
            ("Kofia nyeusi", 2, 22000, 15000),
            ("Tasbihi", 1, 4000, 2000),
        ],
    )


async def seed_day_20():
    await add_sheet(
        DAY_20,
        [
            ("Abaya ya Kituruki", 2, 8000, 5000),
            ("Kanzu ya Oman", 3, 40000, 30000),
            ("Kanzu ya Saudia", 10, 15000, 10000),
            ("Mkoba wa ngozi", 3, 45000, 30000),
            ("Viatu vya kufunga", 6, 35000, 25000),
            ("Mafuta ya nazi", 3, 5000, 3000),
        ],
        expenses=[("Usafiri", 5000)],
    )
    await add_receipt(
        DAY_20,
        "0001",
        [
            ("Alfurqan Kanzu", 2, 65000, 0, 50000),
            ("Kanga za pwani", 2, 9000, 0, 6000),
        ],
    )


async def test_day_17_json(client, headers):
    await seed_day_17()
    res = await client.get(f"/reports/day/{DAY_17}", headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()

    assert set(data) == {
        "period",
        "date",
        "label",
        "short_label",
        "has_prev",
        "has_next",
        "summary",
        "products",
        "totals",
        "expenses",
    }
    assert data["period"] == "day"
    assert data["date"] == DAY_17
    assert data["label"] == "Jumanne, 17 Nov 2026"
    assert data["short_label"] == "Jumanne, 17 Nov"
    assert data["has_prev"] is False
    assert data["has_next"] is True
    assert data["summary"] == {
        "sales": 310000,
        "capital": 228000,
        "expenses": 0,
        "product_profit": 82000,
        "net": 82000,
    }
    assert data["products"][0] == {
        "name": "Viatu vya kufunga",
        "qty": 3,
        "sales": 99000,
        "capital": 75000,
        "profit": 24000,
    }
    assert all(set(p) == {"name", "qty", "sales", "capital", "profit"} for p in data["products"])
    assert [p["qty"] for p in data["products"]] == [3, 3, 2, 2, 1]
    assert data["totals"] == {"qty": 11, "sales": 310000, "profit": 82000}


async def test_day_20_matches_home_screen(client, headers):
    await seed_day_17()
    await seed_day_20()
    data = (await client.get(f"/reports/day/{DAY_20}", headers=headers)).json()

    assert data["label"] == "Ijumaa, 20 Nov 2026"
    assert data["has_next"] is (date(2026, 11, 20) < today())
    assert data["has_prev"] is True
    assert data["summary"] == {
        "sales": 794000,
        "capital": 561000,
        "expenses": 5000,
        "product_profit": 233000,
        "net": 228000,
    }
    assert len(data["products"]) == 8
    assert data["products"][0] == {
        "name": "Kanzu ya Saudia",
        "qty": 10,
        "sales": 150000,
        "capital": 100000,
        "profit": 50000,
    }
    assert data["products"][1]["name"] == "Viatu vya kufunga"
    assert data["totals"] == {"qty": 31, "sales": 794000, "profit": 233000}


async def test_day_without_sales_is_zero_not_404(client, headers):
    res = await client.get("/reports/day/2026-11-18", headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["products"] == []
    assert data["summary"] == {
        "sales": 0,
        "capital": 0,
        "expenses": 0,
        "product_profit": 0,
        "net": 0,
    }
    assert data["totals"] == {"qty": 0, "sales": 0, "profit": 0}


async def test_week_bars_seven_days(client, headers):
    await seed_day_17()
    await seed_day_20()
    data = (await client.get("/reports/week", params={"date": DAY_17}, headers=headers)).json()

    assert data["period"] == "week"
    assert data["start"] == "2026-11-15" and data["end"] == "2026-11-21"
    assert data["label"] == "15 – 21 Novemba 2026"
    assert data["short_label"] == "15 – 21 Nov 2026"
    assert data["has_next"] is (date(2026, 11, 21) < today())
    assert [bar["label"] for bar in data["bars"]] == ["Jpi", "Jtt", "Jne", "Jtn", "Alh", "Iju", "Jmo"]
    assert data["bars"][0]["key"] == "2026-11-15"
    assert data["bars"][0]["net"] == 0
    assert data["bars"][2]["net"] == 82000
    assert data["bars"][5]["net"] == 228000
    now_day = today()
    for bar in data["bars"]:
        if date.fromisoformat(bar["key"]) > now_day:
            assert bar["net"] is None
        else:
            assert isinstance(bar["net"], int)
    assert data["summary"]["net"] == sum(b["net"] for b in data["bars"] if b["net"] is not None)
    assert set(data) == {
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
        "expense_list",
    }


async def test_past_week_has_next(client, headers):
    data = (await client.get("/reports/week", params={"date": "2026-11-10"}, headers=headers)).json()
    assert data["start"] == "2026-11-08" and data["end"] == "2026-11-14"
    assert data["has_next"] is True
    assert data["has_prev"] is False


async def test_month_week_chunks(client, headers):
    await seed_day_17()
    await seed_day_20()
    data = (await client.get("/reports/month", params={"date": "2026-11-05"}, headers=headers)).json()

    assert data["period"] == "month"
    assert data["start"] == "2026-11-01" and data["end"] == "2026-11-30"
    assert data["label"] == "Novemba 2026"
    assert [bar["label"] for bar in data["bars"]] == ["1–7", "8–14", "15–21", "22–28", "29–30"]
    assert data["bars"][0]["key"] == "2026-11-01"
    assert data["bars"][2]["net"] == 310000
    # Bars za siku zijazo ni None; wiki iliyoanza tayari ina 0.
    assert data["bars"][3]["net"] is (None if today() < date(2026, 11, 22) else 0)
    assert data["bars"][4]["net"] is (None if today() < date(2026, 11, 29) else 0)


async def test_year_months(client, headers):
    await seed_day_17()
    await seed_day_20()
    data = (await client.get("/reports/year", params={"date": DAY_20}, headers=headers)).json()

    assert data["period"] == "year"
    assert data["label"] == "2026" and data["short_label"] == "2026"
    assert len(data["bars"]) == 12
    assert data["bars"][10]["label"] == "Nov"
    assert data["bars"][10]["key"] == "2026-11-01"
    assert data["bars"][10]["net"] == 310000
    assert data["bars"][11]["net"] is None


async def test_top_five_and_low_three(client, headers):
    await seed_day_20()
    data = (await client.get("/reports/week", params={"date": DAY_20}, headers=headers)).json()

    assert [p["name"] for p in data["top"]] == [
        "Kanzu ya Saudia",
        "Viatu vya kufunga",
        "Mkoba wa ngozi",
        "Kanzu ya Oman",
        "Mafuta ya nazi",
    ]
    assert all(set(p) == {"name", "qty", "profit"} for p in data["top"] + data["low"])
    top_names = {p["name"] for p in data["top"]}
    assert not top_names & {p["name"] for p in data["low"]}
    assert [p["name"] for p in data["low"]] == [
        "Abaya ya Kituruki",
        "Kanga za pwani",
        "Alfurqan Kanzu",
    ]


async def test_unsold_variants_with_capital(client, headers):
    sid_ = await sid()
    sold = ObjectId()
    other = ObjectId()
    await db.products.insert_one(
        {
            "shop_id": sid_,
            "name": "Abaya",
            "name_lc": "abaya",
            "has_types": True,
            "variants": [
                {"_id": sold, "name": "Abaya nyeusi", "qty": 5, "buying": 7000, "selling": 11000},
                {"_id": other, "name": "Abaya ya Kituruki", "qty": 16, "buying": 5000, "selling": 8000},
            ],
            "created_at": now(),
            "updated_at": now(),
        }
    )
    await db.daily_sheets.insert_one(
        {
            "shop_id": sid_,
            "date": DAY_17,
            "saved_at": None,
            "lines": [
                {
                    "id": "l1",
                    "name": "Abaya nyeusi",
                    "qty": 2,
                    "selling": 11000,
                    "buying": 7000,
                    "variant_id": sold,
                    "product_id": None,
                }
            ],
            "expenses": [],
        }
    )

    data = (await client.get("/reports/week", params={"date": DAY_17}, headers=headers)).json()
    assert data["unsold"] == [
        {"name": "Abaya ya Kituruki", "qty": 16, "capital": 80000},
    ]


async def test_cancelled_receipt_not_counted(client, headers):
    await add_receipt("2026-11-19", "0002", [("Kanzu ya Saudia", 2, 15000, 0, 10000)], status="cancelled", cancelled=True)
    await add_receipt("2026-11-19", "0003", [("Kanzu ya Saudia", 1, 15000, 0, 10000)], cancelled=True)
    data = (await client.get("/reports/day/2026-11-19", headers=headers)).json()
    assert data["products"] == []
    assert data["summary"]["sales"] == 0

    await add_receipt("2026-11-19", "0004", [("Kanzu ya Saudia", 1, 15000, 0, 10000)])
    data = (await client.get("/reports/day/2026-11-19", headers=headers)).json()
    assert data["summary"]["sales"] == 15000
    assert data["summary"]["net"] == 5000
