"""Data ya majaribio (hiari).

python scripts/seed_demo.py
"""

import argparse
import asyncio
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import create_indexes, db  # noqa: E402
from app.services import stock  # noqa: E402
from app.tz import now, today  # noqa: E402

DEMO = [
    {
        "name": "Kanzu",
        "has_types": True,
        "variants": [
            {"name": "Alfurqan Kanzu", "qty": 6, "buying": 50000, "selling": 65000},
            {"name": "Kanzu ya Oman", "qty": 6, "buying": 30000, "selling": 40000},
        ],
    },
    {
        "name": "Kofia",
        "has_types": True,
        "variants": [
            {"name": "Kofia nyeusi", "qty": 8, "buying": 15000, "selling": 22000},
            {"name": "Kofia nyeupe", "qty": 5, "buying": 15000, "selling": 22000},
        ],
    },
    {
        "name": "Udi",
        "has_types": False,
        "variants": [{"name": "Udi", "qty": 10, "buying": 10000, "selling": 15000}],
    },
]


async def main() -> None:
    parser = argparse.ArgumentParser(description="Ingiza data ya majaribio")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    await create_indexes()
    shop = await db.shops.find_one({})
    if not shop:
        print("Hakuna duka. Endesha kwanza: python scripts/create_shop.py")
        return
    sid = shop["_id"]
    if await db.products.count_documents({"shop_id": sid}) and not args.force:
        print("Stock ipo tayari — hakuna kilichobadilishwa (tumia --force).")
        db.client.close()
        return

    day = today().isoformat()
    ts = now()
    first_variants: dict[str, dict] = {}

    for item in DEMO:
        name_lc = item["name"].lower()
        if await db.products.find_one({"shop_id": sid, "name_lc": name_lc}, {"_id": 1}):
            continue
        variants = []
        for v in item["variants"]:
            variants.append(stock.new_variant(v["name"], v["qty"], v["buying"], v["selling"], ts))
        doc = {
            "shop_id": sid,
            "name": item["name"],
            "name_lc": name_lc,
            "has_types": item["has_types"],
            "variants": variants,
            "created_at": ts,
            "updated_at": ts,
        }
        result = await db.products.insert_one(doc)
        doc["_id"] = result.inserted_id
        for variant in variants:
            await stock.log_movement(
                sid,
                doc["_id"],
                variant["_id"],
                variant["name"],
                variant["qty"],
                variant["qty"],
                variant["buying"],
                "new",
                None,
                day,
            )
        first_variants[item["name"]] = {"product": doc, "variants": variants}

    # Daftari la jana
    yesterday = (today() - timedelta(days=1)).isoformat()
    existing_sheet = await db.daily_sheets.find_one({"shop_id": sid, "date": yesterday})
    if not existing_sheet and "Kofia" in first_variants:
        kofia = first_variants["Kofia"]
        variant = kofia["variants"][0]
        await db.daily_sheets.insert_one(
            {
                "shop_id": sid,
                "date": yesterday,
                "lines": [
                    {
                        "variant_id": variant["_id"],
                        "product_id": kofia["product"]["_id"],
                        "name": variant["name"],
                        "qty": 2,
                        "selling": 22000,
                        "buying": 15000,
                        "stock_selling": 22000,
                    }
                ],
                "expenses": [
                    {"name": "Usafirishaji", "amount": 2000},
                    {"name": "Bando", "amount": 1000, "mtandao": "Vodacom"},
                ],
                "saved_at": now(),
                "updated_at": now(),
            }
        )

    print("Data ya majaribio imeingizwa.")
    db.client.close()


if __name__ == "__main__":
    asyncio.run(main())
