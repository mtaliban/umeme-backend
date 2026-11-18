"""Muunganisho wa MongoDB kupitia Motor."""

from motor.motor_asyncio import AsyncIOMotorClient

from .config import settings

client = AsyncIOMotorClient(settings.mongo_url, tz_aware=True)
db = client[settings.db_name]


def get_db():
    """Database ya sasa (duka moja kwa server, shop_id kwenye kila document)."""
    return db


async def create_indexes() -> None:
    await db.devices.create_index("fcm_token", unique=True)
    await db.products.create_index([("shop_id", 1), ("name_lc", 1)], unique=True)
    await db.products.create_index([("shop_id", 1), ("variants._id", 1)])
    await db.receipts.create_index([("shop_id", 1), ("date", 1)])
    await db.receipts.create_index([("shop_id", 1), ("number", 1)], unique=True)
    await db.daily_sheets.create_index([("shop_id", 1), ("date", 1)], unique=True)
    await db.stock_movements.create_index([("shop_id", 1), ("date", 1)])
    await db.notifications_log.create_index([("shop_id", 1), ("sent_at", -1)])
