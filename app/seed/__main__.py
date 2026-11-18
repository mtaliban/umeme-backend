"""`python -m app.seed` — hutumika kwenye deploy (idempotent).

Hutengeneza duka la UMMU AYMAN OUTFITS kama hakuna; kama lipo, haliibadilishi.
PIN inasomwa kutoka SHOP_PIN (default 1234).
"""

import asyncio

from ..auth import hash_pin
from ..config import settings
from ..db import create_indexes, db
from ..tz import now

SHOP = {
    "name": "UMMU AYMAN OUTFITS",
    "phone": "0621 340 044",
    "email": "kambilatifah@gmail.com",
}


def _pin() -> str:
    pin = str(settings.shop_pin or "").strip()
    return pin if len(pin) == 4 and pin.isdigit() else "1234"


async def main() -> None:
    await create_indexes()
    existing = await db.shops.find_one({}, {"_id": 1, "name": 1})
    if existing:
        print(f"Duka lipo tayari: {existing.get('name', '')} — hakuna kilichobadilishwa.")
        db.client.close()
        return

    await db.shops.insert_one(
        {
            **SHOP,
            "pin_hash": hash_pin(_pin()),
            "receipt_seq": 0,
            "settings": {
                "low_stock_threshold": settings.low_stock_threshold,
                "close_day_reminder": settings.close_day_reminder,
            },
            "created_at": now(),
        }
    )
    print("Duka limetengenezwa (PIN kutoka SHOP_PIN, default 1234).")
    db.client.close()


if __name__ == "__main__":
    asyncio.run(main())
