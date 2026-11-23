"""Migration ya data za zamani (idempotent — salama kuirudia).

- `receipts.customer.location` isiyopo/None → `""`
- mistari ya `daily_sheets` isiyo na `buying` → `variants.buying` ya sasa

Matumizi:
  python scripts/migrate_location_line_buying.py --dry-run
  python scripts/migrate_location_line_buying.py

Baada ya migration, hesabu za /daily, /home na /reports zinatumia buying ya
mstari (snapshot) kama zilivyoandikwa wakati wa mauzo.
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import db  # noqa: E402


async def main() -> None:
    parser = argparse.ArgumentParser(description="Migration: customer.location + line buying")
    parser.add_argument("--dry-run", action="store_true", help="onyesha tu, usibadilishe")
    args = parser.parse_args()

    # ── 1) Risiti: customer.location tupu → "" ────────────────────────────────
    receipts_query = {
        "$or": [
            {"customer.location": {"$exists": False}},
            {"customer.location": None},
        ]
    }
    receipts_total = await db.receipts.count_documents(receipts_query)
    receipts_done = 0
    if not args.dry_run and receipts_total:
        result = await db.receipts.update_many(
            receipts_query, {"$set": {"customer.location": ""}}
        )
        receipts_done = result.modified_count

    # ── 2) Mistari ya daftari: buying isiyopo → variants.buying ───────────────
    buying: dict = {}
    async for product in db.products.find({}, {"variants": 1}):
        for variant in product.get("variants", []):
            buying[variant["_id"]] = int(variant.get("buying", 0) or 0)

    lines_total = 0
    lines_done = 0
    sheets_done = 0
    async for sheet in db.daily_sheets.find({"lines.buying": {"$exists": False}}):
        changed = False
        for line in sheet.get("lines", []):
            if "buying" in line:
                continue
            lines_total += 1
            if args.dry_run:
                continue
            variant_id = line.get("variant_id")
            line["buying"] = buying.get(variant_id, 0) if variant_id else 0
            lines_done += 1
            changed = True
        if changed:
            sheets_done += 1
            await db.daily_sheets.update_one(
                {"_id": sheet["_id"]}, {"$set": {"lines": sheet["lines"]}}
            )

    print(
        ("[dry-run] " if args.dry_run else "")
        + f"Risiti zinazohitaji location: {receipts_total} (zilizosasishwa: {receipts_done})"
    )
    print(
        ("[dry-run] " if args.dry_run else "")
        + f"Mistari isiyo na buying: {lines_total} "
        + f"(zilizosasishwa: {lines_done}, daftari: {sheets_done})"
    )

    db.client.close()


if __name__ == "__main__":
    asyncio.run(main())
