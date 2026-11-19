"""Ingiza bidhaa zote kutoka products.json kwenye MongoDB moja kwa moja.

Matumizi:
  python scripts/seed_products.py
  python scripts/seed_products.py --force   # futa za zamani, anza upya
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import create_indexes, db  # noqa: E402
from app.services import stock  # noqa: E402
from app.tz import now, today  # noqa: E402


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="futa bidhaa za zamani, anza upya")
    args = parser.parse_args()

    await create_indexes()

    shop = await db.shops.find_one({})
    if not shop:
        print("Hakuna duka. Endesha kwanza:\n  python scripts/create_shop.py")
        db.client.close()
        return

    sid = shop["_id"]

    if args.force:
        await db.products.delete_many({"shop_id": sid})
        await db.stock_movements.delete_many({"shop_id": sid})
        print("Bidhaa za zamani zimefutwa.")

    products_file = Path(__file__).resolve().parent.parent / "products.json"
    products = json.loads(products_file.read_text(encoding="utf-8"))

    day = today().isoformat()
    ts = now()
    inserted = 0
    skipped = 0

    for item in products:
        name_lc = item["name"].lower()
        if await db.products.find_one({"shop_id": sid, "name_lc": name_lc}, {"_id": 1}):
            print(f"  ipo tayari: {item['name']}")
            skipped += 1
            continue

        variants = []
        for v in item["variants"]:
            variants.append(
                stock.new_variant(v["name"], v["qty"], v["buying"], v["selling"], ts)
            )

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
            if int(variant["qty"]) > 0:
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

        total_qty = sum(v["qty"] for v in item["variants"])
        print(f"  imeingia: {item['name']} ({len(variants)} aina, qty {total_qty})")
        inserted += 1

    total_qty_all = sum(
        int(v.get("qty", 0))
        for p in await db.products.find({"shop_id": sid}).to_list(None)
        for v in p.get("variants", [])
    )
    print(f"\nImeingizwa: {inserted} | Ilikuwepo: {skipped}")
    print(f"Stock yote: {total_qty_all} vipande")

    db.client.close()


if __name__ == "__main__":
    asyncio.run(main())
