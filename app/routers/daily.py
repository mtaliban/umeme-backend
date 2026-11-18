"""Mauzo ya leo: daftari la jioni (mistari + gharama)."""

from collections import defaultdict

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from ..auth import current_shop_id
from ..db import db
from ..schemas import DailyIn
from ..services import stock, tx
from ..services import summary as summary_service
from ..tz import now, parse_day, today

router = APIRouter(tags=["daily"])


async def daily_payload(sid, day_str: str) -> dict:
    doc = await summary_service.sheet(sid, day_str)
    sheet = summary_service.sheet_out(doc)
    return {
        "date": day_str,
        "receipt_lines": await summary_service.receipt_lines(sid, day_str),
        "lines": sheet["lines"],
        "expenses": sheet["expenses"],
        "saved_at": sheet["saved_at"],
        "summary": await summary_service.day_summary(sid, day_str),
    }


@router.get("/daily/{date}")
async def get_daily(date: str, sid=Depends(current_shop_id)):
    return await daily_payload(sid, parse_day(date).isoformat())


async def _save(
    sid,
    day_str,
    existing,
    old_qty,
    old_buying,
    new_qty,
    meta,
    lines,
    expenses,
    session=None,
) -> list[tuple[str, int]]:
    sheet_id = existing["_id"] if existing else ObjectId()
    applied: list[tuple] = []
    touched: list[tuple[str, int]] = []

    async def rollback() -> None:
        if session is not None:
            return  # transaction itajifuta yenyewe
        for pid, vid, delta, name, buying in reversed(applied):
            try:
                if delta > 0:
                    await stock.return_stock(
                        sid, pid, vid, delta, name, buying, "daily_revert", sheet_id, day_str
                    )
                else:
                    await stock.take_stock(
                        sid, pid, vid, -delta, name, buying, "daily", sheet_id, day_str
                    )
            except HTTPException:
                continue

    try:
        for vid in set(list(old_qty) + list(new_qty)):
            delta = new_qty.get(vid, 0) - old_qty.get(vid, 0)
            if delta == 0:
                continue
            info = meta.get(vid)
            if info is None:
                try:
                    product, variant = await stock.find_variant(sid, vid, session=session)
                except HTTPException:
                    continue
                info = {"product": product, "variant": variant}
            product = info["product"]
            variant = info["variant"]
            if delta > 0:
                qty_after = await stock.take_stock(
                    sid,
                    product["_id"],
                    variant["_id"],
                    delta,
                    variant["name"],
                    variant.get("buying", 0),
                    "daily",
                    sheet_id,
                    day_str,
                    session=session,
                )
            else:
                qty_after = await stock.return_stock(
                    sid,
                    product["_id"],
                    variant["_id"],
                    -delta,
                    variant["name"],
                    variant.get("buying", 0),
                    "daily_revert",
                    sheet_id,
                    day_str,
                    session=session,
                )
            applied.append(
                (
                    product["_id"],
                    variant["_id"],
                    delta,
                    variant["name"],
                    variant.get("buying", 0),
                )
            )
            touched.append((variant["name"], qty_after))

        ts = now()
        await db.daily_sheets.update_one(
            {"_id": sheet_id},
            {
                "$set": {"lines": lines, "expenses": expenses, "saved_at": ts, "updated_at": ts},
                "$setOnInsert": {"shop_id": sid, "date": day_str},
            },
            upsert=True,
            session=session,
        )
    except HTTPException:
        await rollback()
        raise
    except Exception:
        await rollback()
        raise HTTPException(500, "Imeshindikana kuhifadhi mauzo")
    return touched


@router.put("/daily/{date}")
async def put_daily(date: str, body: DailyIn, sid=Depends(current_shop_id)):
    day = parse_day(date)
    if day > today():
        raise HTTPException(400, "Huwezi kuandika siku ijayo")
    day_str = day.isoformat()

    existing = await summary_service.sheet(sid, day_str)
    old_qty: dict[str, int] = {}
    old_buying: dict[str, int] = {}
    if existing:
        for line in existing.get("lines", []):
            key = str(line["variant_id"])
            old_qty[key] = int(line["qty"])
            old_buying[key] = int(line.get("buying", 0) or 0)

    new_qty: dict[str, int] = defaultdict(int)
    meta: dict[str, dict] = {}
    lines: list[dict] = []
    for line in body.lines:
        if int(line.qty) <= 0:
            raise HTTPException(400, "Idadi iwe kubwa kuliko 0")
        if int(line.selling) <= 0:
            raise HTTPException(400, "Bei iwe kubwa kuliko 0")
        product, variant = await stock.find_variant(sid, line.variant_id)
        vid = str(variant["_id"])
        new_qty[vid] += int(line.qty)
        meta[vid] = {"product": product, "variant": variant}
        # Aina iliyokuwepo awali inabaki na buying yake ya zamani.
        buying = old_buying.get(vid, int(variant.get("buying", 0)))
        lines.append(
            {
                "variant_id": variant["_id"],
                "product_id": product["_id"],
                "name": variant["name"],
                "qty": int(line.qty),
                "selling": int(line.selling),
                "buying": buying,
                "stock_selling": int(variant.get("selling", 0)),
            }
        )

    expenses: list[dict] = []
    for raw_expense in body.expenses:
        expense = dict(raw_expense or {})
        name = str(expense.get("name", "") or "").strip()
        if not name:
            raise HTTPException(400, "Andika jina la gharama")
        try:
            amount = int(expense.get("amount"))
        except (TypeError, ValueError):
            raise HTTPException(400, "Kiasi si sahihi")
        if amount <= 0:
            raise HTTPException(400, "Kiasi kiwe kubwa kuliko 0")
        expense["name"] = name
        expense["amount"] = amount
        expenses.append(expense)

    args = (sid, day_str, existing, old_qty, old_buying, new_qty, meta, lines, expenses)
    if await tx.supported():
        async with tx.transaction() as session:
            touched = await _save(*args, session=session)
    else:
        touched = await _save(*args, session=None)

    for name, qty_after in touched:
        await stock.check_stock(sid, name, qty_after)

    return await daily_payload(sid, day_str)
