"""Stock: kutoa, kurudisha na kumbukumbu za mwendo wa bidhaa."""

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException

from ..config import settings
from ..db import db
from ..tz import day_start, now, today, today_str
from . import notify

PRODUCT_KEYS = {"_id", "shop_id", "name", "name_lc", "has_types", "variants", "created_at", "updated_at"}
VARIANT_KEYS = {"_id", "name", "name_lc", "qty", "buying", "selling", "created_at"}


def oid(value, what: str = "Kipengele") -> ObjectId:
    try:
        return ObjectId(str(value))
    except (InvalidId, TypeError):
        raise HTTPException(404, f"{what} haipo")


def clean_extra(values: dict, base: set[str]) -> dict:
    """Fields za ziada tu — zisizogusa fields za mfumo."""
    return {k: v for k, v in (values or {}).items() if k not in base}


def new_variant(name: str, qty: int, buying: int, selling: int, ts=None, extra: dict | None = None) -> dict:
    doc = {
        "_id": ObjectId(),
        "name": name,
        "name_lc": name.lower(),
        "qty": int(qty),
        "buying": int(buying),
        "selling": int(selling),
        "created_at": ts or now(),
    }
    for key, value in (extra or {}).items():
        if key not in VARIANT_KEYS:
            doc[key] = value
    return doc


def variant_out(product: dict, variant: dict) -> dict:
    out = {
        "id": str(variant["_id"]),
        "product_id": str(product["_id"]),
        "product_name": product["name"],
        "name": variant["name"],
        "qty": int(variant.get("qty", 0)),
        "buying": int(variant.get("buying", 0)),
        "selling": int(variant.get("selling", 0)),
    }
    out.update(clean_extra(variant, VARIANT_KEYS))
    return out


def product_out(product: dict) -> dict:
    out = {
        "id": str(product["_id"]),
        "name": product["name"],
        "has_types": bool(product.get("has_types", True)),
        "variants": [variant_out(product, v) for v in product.get("variants", [])],
    }
    out.update(clean_extra(product, PRODUCT_KEYS))
    return out


async def find_product(sid, product_id, session=None) -> dict:
    product = await db.products.find_one(
        {"_id": oid(product_id, "Bidhaa"), "shop_id": sid}, session=session
    )
    if not product:
        raise HTTPException(404, "Bidhaa haipo")
    return product


async def find_variant(sid, variant_id, session=None) -> tuple[dict, dict]:
    vid = oid(variant_id, "Aina")
    product = await db.products.find_one({"shop_id": sid, "variants._id": vid}, session=session)
    if not product:
        raise HTTPException(404, "Bidhaa haipo")
    variant = next((v for v in product.get("variants", []) if v["_id"] == vid), None)
    if variant is None:
        raise HTTPException(404, "Bidhaa haipo")
    return product, variant


async def variant_qty(sid, product_id, variant_id, session=None) -> int:
    product = await db.products.find_one(
        {"_id": product_id, "shop_id": sid, "variants._id": variant_id},
        {"variants.$": 1},
        session=session,
    )
    if not product or not product.get("variants"):
        return 0
    return int(product["variants"][0].get("qty", 0))


async def log_movement(
    sid,
    product_id,
    variant_id,
    name,
    change,
    qty_after,
    buying,
    reason,
    ref_id=None,
    day=None,
    session=None,
) -> None:
    await db.stock_movements.insert_one(
        {
            "shop_id": sid,
            "product_id": product_id,
            "variant_id": variant_id,
            "name": name,
            "change": int(change),
            "qty_after": int(qty_after),
            "buying": int(buying or 0),
            "reason": reason,
            "ref_id": ref_id,
            "date": day or today_str(),
            "at": now(),
        },
        session=session,
    )


async def take_stock(
    sid,
    product_id,
    variant_id,
    qty,
    name,
    buying,
    reason,
    ref_id=None,
    day=None,
    session=None,
) -> int:
    """Punguza stock kwa usalama — haishuki chini ya 0 kamwe."""
    pid = oid(product_id, "Bidhaa")
    vid = oid(variant_id, "Aina")
    res = await db.products.update_one(
        {"_id": pid, "shop_id": sid, "variants": {"$elemMatch": {"_id": vid, "qty": {"$gte": int(qty)}}}},
        {"$inc": {"variants.$.qty": -int(qty)}, "$set": {"updated_at": now()}},
        session=session,
    )
    if res.modified_count == 0:
        current = await variant_qty(sid, pid, vid, session=session)
        raise HTTPException(400, f"{name}: zipo {current} tu")
    qty_after = await variant_qty(sid, pid, vid, session=session)
    await log_movement(
        sid, pid, vid, name, -int(qty), qty_after, buying, reason, ref_id, day, session=session
    )
    return qty_after


async def return_stock(
    sid,
    product_id,
    variant_id,
    qty,
    name,
    buying,
    reason,
    ref_id=None,
    day=None,
    session=None,
) -> int:
    pid = oid(product_id, "Bidhaa")
    vid = oid(variant_id, "Aina")
    await db.products.update_one(
        {"_id": pid, "shop_id": sid},
        {"$inc": {"variants.$[v].qty": int(qty)}, "$set": {"updated_at": now()}},
        array_filters=[{"v._id": vid}],
        session=session,
    )
    qty_after = await variant_qty(sid, pid, vid, session=session)
    await log_movement(
        sid, pid, vid, name, int(qty), qty_after, buying, reason, ref_id, day, session=session
    )
    return qty_after


async def check_stock(sid, name: str, qty: int) -> None:
    """Tuma stock_out / stock_low baada ya stock kubadilika."""
    if qty <= 0:
        await notify.send(
            sid,
            "stock_out",
            "Imeisha",
            f"{name} imeisha kwenye stock",
            {"name": name, "qty": qty},
        )
    elif qty <= settings.low_stock_threshold:
        already = await db.notifications_log.find_one(
            {
                "shop_id": sid,
                "type": "stock_low",
                "data.name": name,
                "sent_at": {"$gte": day_start(today())},
            },
            {"_id": 1},
        )
        if not already:
            await notify.send(
                sid,
                "stock_low",
                "Inakaribia kuisha",
                f"{name}: zimebaki {qty}",
                {"name": name, "qty": qty},
            )
