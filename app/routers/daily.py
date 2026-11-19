"""Mauzo ya leo: daftari (mistari + gharama) kwa mstari mmoja mmoja."""

from collections import defaultdict

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from ..auth import current_shop_id
from ..db import db
from ..schemas import DailyExpenseAdd, DailyExpenseEdit, DailyIn, DailyLineAdd, DailyLineEdit
from ..services import stock, tx
from ..services import summary as summary_service
from ..tz import now, parse_day, today

router = APIRouter(tags=["daily"])


async def _sheet(sid, day_str: str) -> dict | None:
    return await db.daily_sheets.find_one({"shop_id": sid, "date": day_str})


async def daily_payload(sid, day_str: str) -> dict:
    doc = await _sheet(sid, day_str)
    sheet = summary_service.sheet_out(doc)
    return {
        "date": day_str,
        "receipt_lines": await summary_service.receipt_lines(sid, day_str),
        "lines": sheet["lines"],
        "expenses": sheet["expenses"],
        "saved_at": sheet["saved_at"],
        "summary": await summary_service.day_summary(sid, day_str),
    }


# ── GET /daily/{date} ─────────────────────────────────────────────────────────

@router.get("/daily/{date}")
async def get_daily(date: str, sid=Depends(current_shop_id)):
    return await daily_payload(sid, parse_day(date).isoformat())


# ── POST /daily/{date}/lines ──────────────────────────────────────────────────

@router.post("/daily/{date}/lines")
async def add_line(date: str, body: DailyLineAdd, sid=Depends(current_shop_id)):
    day = parse_day(date)
    if day > today():
        raise HTTPException(400, "Huwezi kuandika siku ijayo")
    day_str = day.isoformat()

    if int(body.qty) <= 0:
        raise HTTPException(400, "Idadi iwe kubwa kuliko 0")
    if int(body.selling) <= 0:
        raise HTTPException(400, "Bei iwe kubwa kuliko 0")

    out_of_stock = body.variant_id is None
    qty_after = None

    if out_of_stock:
        name = (body.name or "").strip()
        if not name:
            raise HTTPException(400, "Andika jina la bidhaa")
        buying = max(0, int(body.buying or 0))
        line = {
            "id": str(ObjectId()),
            "variant_id": None,
            "product_id": None,
            "name": name,
            "qty": int(body.qty),
            "selling": int(body.selling),
            "buying": buying,
            "out_of_stock": True,
            "created_at": now(),
        }
    else:
        product, variant = await stock.find_variant(sid, body.variant_id)
        buying = int(variant.get("buying", 0))
        qty_after = await stock.take_stock(
            sid,
            product["_id"],
            variant["_id"],
            int(body.qty),
            variant["name"],
            buying,
            "daily",
            None,
            day_str,
        )
        line = {
            "id": str(ObjectId()),
            "variant_id": variant["_id"],
            "product_id": product["_id"],
            "name": variant["name"],
            "qty": int(body.qty),
            "selling": int(body.selling),
            "buying": buying,
            "stock_selling": int(variant.get("selling", 0)),
            "out_of_stock": False,
            "created_at": now(),
        }

    ts = now()
    await db.daily_sheets.update_one(
        {"shop_id": sid, "date": day_str},
        {
            "$push": {"lines": line},
            "$set": {"updated_at": ts},
            "$setOnInsert": {"shop_id": sid, "date": day_str, "expenses": [], "saved_at": None},
        },
        upsert=True,
    )

    if qty_after is not None:
        await stock.check_stock(sid, line["name"], qty_after)

    return await daily_payload(sid, day_str)


# ── PATCH /daily/{date}/lines/{id} ───────────────────────────────────────────

@router.patch("/daily/{date}/lines/{line_id}")
async def edit_line(date: str, line_id: str, body: DailyLineEdit, sid=Depends(current_shop_id)):
    day = parse_day(date)
    if day > today():
        raise HTTPException(400, "Huwezi kuandika siku ijayo")
    day_str = day.isoformat()

    doc = await _sheet(sid, day_str)
    if not doc:
        raise HTTPException(404, "Hakuna daftari kwa siku hii")

    old_line = next((l for l in doc.get("lines", []) if l.get("id") == line_id), None)
    if not old_line:
        raise HTTPException(404, "Mstari huo haupo")

    new_qty = int(body.qty) if body.qty is not None else int(old_line["qty"])
    new_selling = int(body.selling) if body.selling is not None else int(old_line["selling"])

    if new_qty <= 0:
        raise HTTPException(400, "Idadi iwe kubwa kuliko 0")
    if new_selling <= 0:
        raise HTTPException(400, "Bei iwe kubwa kuliko 0")

    out_of_stock = bool(old_line.get("out_of_stock"))
    qty_after = None

    if not out_of_stock:
        delta = new_qty - int(old_line["qty"])
        if delta > 0:
            qty_after = await stock.take_stock(
                sid,
                old_line["product_id"],
                old_line["variant_id"],
                delta,
                old_line["name"],
                int(old_line.get("buying", 0)),
                "daily_edit",
                None,
                day_str,
            )
        elif delta < 0:
            qty_after = await stock.return_stock(
                sid,
                old_line["product_id"],
                old_line["variant_id"],
                -delta,
                old_line["name"],
                int(old_line.get("buying", 0)),
                "daily_edit",
                None,
                day_str,
            )

    updates: dict = {
        "lines.$.qty": new_qty,
        "lines.$.selling": new_selling,
        "updated_at": now(),
    }
    if out_of_stock and body.buying is not None:
        updates["lines.$.buying"] = max(0, int(body.buying))

    await db.daily_sheets.update_one(
        {"shop_id": sid, "date": day_str, "lines.id": line_id},
        {"$set": updates},
    )

    if qty_after is not None:
        await stock.check_stock(sid, old_line["name"], qty_after)

    return await daily_payload(sid, day_str)


# ── DELETE /daily/{date}/lines/{id} ──────────────────────────────────────────

@router.delete("/daily/{date}/lines/{line_id}")
async def delete_line(date: str, line_id: str, sid=Depends(current_shop_id)):
    day = parse_day(date)
    if day > today():
        raise HTTPException(400, "Huwezi kuandika siku ijayo")
    day_str = day.isoformat()

    doc = await _sheet(sid, day_str)
    if not doc:
        raise HTTPException(404, "Hakuna daftari kwa siku hii")

    old_line = next((l for l in doc.get("lines", []) if l.get("id") == line_id), None)
    if not old_line:
        raise HTTPException(404, "Mstari huo haupo")

    if not bool(old_line.get("out_of_stock")):
        await stock.return_stock(
            sid,
            old_line["product_id"],
            old_line["variant_id"],
            int(old_line["qty"]),
            old_line["name"],
            int(old_line.get("buying", 0)),
            "daily_delete",
            None,
            day_str,
        )

    await db.daily_sheets.update_one(
        {"shop_id": sid, "date": day_str},
        {"$pull": {"lines": {"id": line_id}}, "$set": {"updated_at": now()}},
    )

    return await daily_payload(sid, day_str)


# ── POST /daily/{date}/expenses ───────────────────────────────────────────────

@router.post("/daily/{date}/expenses")
async def add_expense(date: str, body: DailyExpenseAdd, sid=Depends(current_shop_id)):
    day = parse_day(date)
    if day > today():
        raise HTTPException(400, "Huwezi kuandika siku ijayo")
    day_str = day.isoformat()

    name = (body.name or "").strip()
    if not name:
        raise HTTPException(400, "Andika jina la gharama")
    if int(body.amount) <= 0:
        raise HTTPException(400, "Kiasi kiwe kubwa kuliko 0")

    extra = {k: v for k, v in body.model_dump(exclude={"name", "amount"}).items() if v is not None}
    expense = {"id": str(ObjectId()), "name": name, "amount": int(body.amount), "created_at": now(), **extra}

    ts = now()
    await db.daily_sheets.update_one(
        {"shop_id": sid, "date": day_str},
        {
            "$push": {"expenses": expense},
            "$set": {"updated_at": ts},
            "$setOnInsert": {"shop_id": sid, "date": day_str, "lines": [], "saved_at": None},
        },
        upsert=True,
    )

    return await daily_payload(sid, day_str)


# ── PATCH /daily/{date}/expenses/{id} ────────────────────────────────────────

@router.patch("/daily/{date}/expenses/{expense_id}")
async def edit_expense(
    date: str, expense_id: str, body: DailyExpenseEdit, sid=Depends(current_shop_id)
):
    day_str = parse_day(date).isoformat()

    doc = await _sheet(sid, day_str)
    if not doc:
        raise HTTPException(404, "Hakuna daftari kwa siku hii")
    if not any(e.get("id") == expense_id for e in doc.get("expenses", [])):
        raise HTTPException(404, "Gharama hiyo haipo")

    updates: dict = {"updated_at": now()}
    if body.name is not None:
        name = body.name.strip()
        if not name:
            raise HTTPException(400, "Andika jina la gharama")
        updates["expenses.$.name"] = name
    if body.amount is not None:
        if int(body.amount) <= 0:
            raise HTTPException(400, "Kiasi kiwe kubwa kuliko 0")
        updates["expenses.$.amount"] = int(body.amount)
    extra = {k: v for k, v in (body.model_dump(exclude={"name", "amount"}) or {}).items() if v is not None}
    for k, v in extra.items():
        updates[f"expenses.$.{k}"] = v

    await db.daily_sheets.update_one(
        {"shop_id": sid, "date": day_str, "expenses.id": expense_id},
        {"$set": updates},
    )

    return await daily_payload(sid, day_str)


# ── DELETE /daily/{date}/expenses/{id} ───────────────────────────────────────

@router.delete("/daily/{date}/expenses/{expense_id}")
async def delete_expense(date: str, expense_id: str, sid=Depends(current_shop_id)):
    day_str = parse_day(date).isoformat()

    doc = await _sheet(sid, day_str)
    if not doc:
        raise HTTPException(404, "Hakuna daftari kwa siku hii")

    await db.daily_sheets.update_one(
        {"shop_id": sid, "date": day_str},
        {"$pull": {"expenses": {"id": expense_id}}, "$set": {"updated_at": now()}},
    )

    return await daily_payload(sid, day_str)


# ── POST /daily/{date}/close ──────────────────────────────────────────────────

@router.post("/daily/{date}/close")
async def close_day(date: str, sid=Depends(current_shop_id)):
    day = parse_day(date)
    if day > today():
        raise HTTPException(400, "Huwezi kufunga siku ijayo")
    day_str = day.isoformat()

    ts = now()
    await db.daily_sheets.update_one(
        {"shop_id": sid, "date": day_str},
        {
            "$set": {"saved_at": ts, "updated_at": ts},
            "$setOnInsert": {"shop_id": sid, "date": day_str, "lines": [], "expenses": []},
        },
        upsert=True,
    )

    return await daily_payload(sid, day_str)


# ── POST /daily/{date}/reopen ─────────────────────────────────────────────────

@router.post("/daily/{date}/reopen")
async def reopen_day(date: str, sid=Depends(current_shop_id)):
    day_str = parse_day(date).isoformat()

    await db.daily_sheets.update_one(
        {"shop_id": sid, "date": day_str},
        {"$set": {"saved_at": None, "updated_at": now()}},
    )

    return await daily_payload(sid, day_str)


# ── PUT /daily/{date} (backward compatibility) ────────────────────────────────

@router.put("/daily/{date}")
async def put_daily(date: str, body: DailyIn, sid=Depends(current_shop_id)):
    day = parse_day(date)
    if day > today():
        raise HTTPException(400, "Huwezi kuandika siku ijayo")
    day_str = day.isoformat()

    existing = await _sheet(sid, day_str)
    old_qty: dict[str, int] = {}
    old_buying: dict[str, int] = {}
    if existing:
        for line in existing.get("lines", []):
            if line.get("out_of_stock"):
                continue
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
        buying = old_buying.get(vid, int(variant.get("buying", 0)))
        lines.append(
            {
                "id": str(ObjectId()),
                "variant_id": variant["_id"],
                "product_id": product["_id"],
                "name": variant["name"],
                "qty": int(line.qty),
                "selling": int(line.selling),
                "buying": buying,
                "stock_selling": int(variant.get("selling", 0)),
                "out_of_stock": False,
                "created_at": now(),
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
        expense["id"] = expense.get("id") or str(ObjectId())
        expense["name"] = name
        expense["amount"] = amount
        expenses.append(expense)

    # Apply stock delta
    sheet_id = existing["_id"] if existing else ObjectId()
    touched: list[tuple[str, int]] = []

    async def _apply_deltas(session=None) -> None:
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
                qa = await stock.take_stock(
                    sid, product["_id"], variant["_id"], delta, variant["name"],
                    variant.get("buying", 0), "daily", sheet_id, day_str, session=session,
                )
            else:
                qa = await stock.return_stock(
                    sid, product["_id"], variant["_id"], -delta, variant["name"],
                    variant.get("buying", 0), "daily_revert", sheet_id, day_str, session=session,
                )
            touched.append((variant["name"], qa))

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

    if await tx.supported():
        async with tx.transaction() as session:
            await _apply_deltas(session)
    else:
        await _apply_deltas(None)

    for name, qty_after in touched:
        await stock.check_stock(sid, name, qty_after)

    return await daily_payload(sid, day_str)
