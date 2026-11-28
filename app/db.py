"""Muunganisho wa MongoDB kupitia Motor."""

from motor.motor_asyncio import AsyncIOMotorClient

from .config import settings

client = AsyncIOMotorClient(settings.database_url, tz_aware=True)
db = client[settings.db_name]


def get_db():
    """Database ya sasa (duka moja kwa server, shop_id kwenye kila document)."""
    return db


async def create_indexes() -> None:
    """Index za haraka (sehemu 7.3) — `shop_id` ndio kichujio cha kila query."""
    await db.devices.create_index("fcm_token", unique=True)
    await db.products.create_index([("shop_id", 1), ("name_lc", 1)], unique=True)
    await db.products.create_index([("shop_id", 1), ("name", 1)])
    await db.products.create_index([("shop_id", 1)])
    # Aina (variants) ziko ndani ya document ya bidhaa — index hizi zinatosha.
    await db.products.create_index([("shop_id", 1), ("variants._id", 1)])
    await db.receipts.create_index([("shop_id", 1), ("date", 1)])
    await db.receipts.create_index([("shop_id", 1), ("date", -1), ("number", -1)])
    await db.receipts.create_index([("shop_id", 1), ("customer.name", 1)])
    await db.receipts.create_index([("shop_id", 1), ("number", 1)], unique=True)
    # Risiti isiyoghairiwa kwa siku (orodha ya siku/historia).
    await db.receipts.create_index([("shop_id", 1), ("cancelled", 1), ("date", 1)])
    # Kila ombi la kuandika linaweza kuja mara mbili (Awamu 2 — offline retry).
    # Partial index (compound sparse bado ina-index `null` kwa sababu shop_id
    # ipo) — inaruka risiti zisizo na client_id kabisa.
    await db.receipts.create_index(
        [("shop_id", 1), ("client_id", 1)],
        unique=True,
        partialFilterExpression={"client_id": {"$type": "string"}},
    )
    await db.daily_sheets.create_index([("shop_id", 1), ("date", 1)], unique=True)
    await db.daily_sheets.create_index(
        [("shop_id", 1), ("lines.client_id", 1)],
        partialFilterExpression={"lines.client_id": {"$type": "string"}},
    )
    await db.daily_sheets.create_index(
        [("shop_id", 1), ("expenses.client_id", 1)],
        partialFilterExpression={"expenses.client_id": {"$type": "string"}},
    )
    await db.stock_movements.create_index([("shop_id", 1), ("date", 1)])
    await db.stock_movements.create_index([("variant_id", 1)])
    await db.stock_movements.create_index([("shop_id", 1), ("product_id", 1)])
    await db.notifications_log.create_index([("shop_id", 1), ("sent_at", -1)])
