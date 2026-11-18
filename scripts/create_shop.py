"""Tengeneza duka la UMMU AYMAN OUTFITS.

python scripts/create_shop.py --name "UMMU AYMAN OUTFITS" --phone "0621 340 044" \
    --email kambilatifah@gmail.com --pin 1234
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.auth import hash_pin  # noqa: E402
from app.config import settings  # noqa: E402
from app.db import create_indexes, db  # noqa: E402
from app.tz import now  # noqa: E402


async def main() -> None:
    parser = argparse.ArgumentParser(description="Tengeneza duka")
    parser.add_argument("--name", default="UMMU AYMAN OUTFITS")
    parser.add_argument("--phone", default="0621 340 044")
    parser.add_argument("--email", default="kambilatifah@gmail.com")
    parser.add_argument("--pin", default="1234")
    args = parser.parse_args()

    if not (len(args.pin) == 4 and args.pin.isdigit()):
        print("PIN iwe tarakimu 4.")
        raise SystemExit(1)

    await create_indexes()
    existing = await db.shops.find_one({"name": args.name})
    if existing:
        await db.shops.update_one(
            {"_id": existing["_id"]},
            {
                "$set": {
                    "phone": args.phone,
                    "email": args.email,
                    "pin_hash": hash_pin(args.pin),
                    "updated_at": now(),
                }
            },
        )
        print(f"Duka lipo tayari: {args.name} (PIN imebadilishwa)")
    else:
        await db.shops.insert_one(
            {
                "name": args.name,
                "phone": args.phone,
                "email": args.email,
                "pin_hash": hash_pin(args.pin),
                "receipt_seq": 0,
                "settings": {
                    "low_stock_threshold": settings.low_stock_threshold,
                    "close_day_reminder": settings.close_day_reminder,
                },
                "created_at": now(),
            }
        )
        print(f"Duka limetengenezwa: {args.name}")
    db.client.close()


if __name__ == "__main__":
    asyncio.run(main())
