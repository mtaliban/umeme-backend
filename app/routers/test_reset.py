"""Test reset endpoints — zinafanya kazi tu kama ALLOW_TEST_RESET=true."""

import os
from collections import defaultdict

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from ..auth import current_shop_id
from ..db import db
from ..tz import parse_day

router = APIRouter(tags=["test"])

_SALE_REASONS = ["receipt", "daily", "daily_edit", "daily_delete", "daily_revert",
                 "receipt_cancel"]


def _check():
    if os.getenv("ALLOW_TEST_RESET", "false").lower() != "true":
        raise HTTPException(404, "Not found")


async def _restore_stock(sid, items: list[dict]) -> dict[str, int]:
    totals: dict[tuple, int] = defaultdict(int)
    for it in items:
        if it.get("out_of_stock"):
            continue
        pid = it.get("product_id")
        vid = it.get("variant_id")
        if not pid or not vid:
            continue
        totals[(pid, vid)] += int(it.get("qty", 0))

    restored: dict[str, int] = {}
    for (pid, vid), qty in totals.items():
        if qty <= 0:
            continue
        await db.products.update_one(
            {"_id": pid, "shop_id": sid, "variants._id": vid},
            {"$inc": {"variants.$.qty": qty}},
        )
        restored[str(vid)] = restored.get(str(vid), 0) + qty
    return restored


@router.delete("/test/day/{date}", include_in_schema=False)
async def delete_test_day(date: str, sid=Depends(current_shop_id)):
    _check()
    day_str = parse_day(date).isoformat()

    items: list[dict] = []
    async for r in db.receipts.find({"shop_id": sid, "date": day_str, "status": "paid"}):
        items.extend(r.get("items", []))
    sheet = await db.daily_sheets.find_one({"shop_id": sid, "date": day_str})
    if sheet:
        items.extend(sheet.get("lines", []))

    restored = await _restore_stock(sid, items)

    await db.receipts.delete_many({"shop_id": sid, "date": day_str})
    await db.daily_sheets.delete_many({"shop_id": sid, "date": day_str})
    await db.stock_movements.delete_many(
        {"shop_id": sid, "date": day_str, "reason": {"$in": _SALE_REASONS}}
    )

    return {"ok": True, "restored": restored}


@router.delete("/test/sales", include_in_schema=False)
async def delete_test_sales(sid=Depends(current_shop_id)):
    _check()

    items: list[dict] = []
    async for r in db.receipts.find({"shop_id": sid, "status": "paid"}):
        items.extend(r.get("items", []))
    async for sheet in db.daily_sheets.find({"shop_id": sid}):
        items.extend(sheet.get("lines", []))

    await _restore_stock(sid, items)

    await db.receipts.delete_many({"shop_id": sid})
    await db.daily_sheets.delete_many({"shop_id": sid})
    await db.stock_movements.delete_many(
        {"shop_id": sid, "reason": {"$in": _SALE_REASONS}}
    )
    await db.shops.update_one({"_id": sid}, {"$set": {"receipt_seq": 0}})

    return {"ok": True}
