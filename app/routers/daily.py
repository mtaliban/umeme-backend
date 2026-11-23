"""Mauzo ya leo: daftari (mistari + gharama) kwa mstari mmoja mmoja."""

from collections import defaultdict
from datetime import date, timedelta

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from ..auth import current_shop_id
from ..db import db
from ..schemas import DailyExpenseAdd, DailyExpenseEdit, DailyIn, DailyLineAdd, DailyLineEdit
from ..services import stock, tx
from ..services import summary as summary_service
from ..tz import DAY_NAMES, MONTH_NAMES, MONTH_SHORT, now, parse_day, today

router = APIRouter(tags=["daily"])


async def _sheet(sid, day_str: str) -> dict | None:
    return await db.daily_sheets.find_one({"shop_id": sid, "date": day_str})


async def daily_payload(sid, day_str: str) -> dict:
    doc = await _sheet(sid, day_str)
    sheet = summary_service.sheet_out(
        doc, await summary_service.variant_buying(sid, (doc or {}).get("lines", []))
    )
    return {
        "date": day_str,
        "receipt_lines": await summary_service.receipt_lines(sid, day_str),
        "lines": sheet["lines"],
        "expenses": sheet["expenses"],
        "saved_at": sheet["saved_at"],
        "summary": await summary_service.day_summary(sid, day_str),
    }


def _ensure_open(doc: dict | None) -> None:
    """Siku iliyofungwa (saved_at) hairuhusiwi kubadilishwa — 409."""
    if doc and doc.get("saved_at"):
        raise HTTPException(409, "Siku imehifadhiwa — bonyeza Hariri kwanza")


# ── GET /daily/history ────────────────────────────────────────────────────────
# Lazima isajiliwe KABLA ya GET /daily/{date}, vinginevyo "history" inachukuliwa
# kama tarehe.

@router.get("/daily/history")
async def daily_history(
    before: str | None = None,
    limit: int = 40,
    sid=Depends(current_shop_id),
):
    # Siku kabla ya leo peke yake; `before` ni tarehe ya kuendelea kupakia.
    end = parse_day(before) if before else today()
    limit = max(1, min(int(limit or 40), 366))
    end_str = end.isoformat()

    found: dict[str, dict] = {}
    async for doc in db.daily_sheets.find(
        {
            "shop_id": sid,
            "date": {"$lt": end_str},
            "$or": [
                {"lines.0": {"$exists": True}},
                {"expenses.0": {"$exists": True}},
            ],
        },
        {"date": 1, "saved_at": 1},
    ):
        found[doc["date"]] = {"saved_at": doc.get("saved_at")}
    async for receipt in db.receipts.find(
        {"shop_id": sid, "date": {"$lt": end_str}, **summary_service.LIVE},
        {"date": 1},
    ):
        found.setdefault(receipt["date"], {"saved_at": None})

    ordered = sorted(found, reverse=True)
    page = ordered[:limit]

    months: list[dict] = []
    by_month: dict[str, dict] = {}
    for day_str in page:
        d = date.fromisoformat(day_str)
        summary = await summary_service.day_summary(sid, day_str)
        key = f"{d.year}-{d.month:02d}"
        month = by_month.get(key)
        if month is None:
            month = {
                "label": f"{MONTH_NAMES[d.month - 1].upper()} {d.year}",
                "month": key,
                "year": d.year,
                "month_no": d.month,
                "sales": 0,
                "expenses": 0,
                "net": 0,
                "days": [],
            }
            by_month[key] = month
            months.append(month)
        month["days"].append(
            {
                "date": day_str,
                "label": f"{DAY_NAMES[d.weekday()]}, {d.day} {MONTH_SHORT[d.month - 1]}",
                "sales": summary["sales"],
                "items": await summary_service.day_items(sid, day_str),
                "capital": summary["capital"],
                "expenses": summary["expenses"],
                "product_profit": summary["product_profit"],
                "net": summary["net"],
                "saved": bool(found[day_str].get("saved_at")),
                "saved_at": found[day_str].get("saved_at"),
            }
        )
        for field in ("sales", "expenses", "net"):
            month[field] += summary[field]

    return {
        "months": months,
        "next_before": page[-1] if len(ordered) > limit and page else None,
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

    if body.qty is None or int(body.qty) <= 0:
        raise HTTPException(422, "Jaza idadi")
    if body.selling is None or int(body.selling) <= 0:
        raise HTTPException(422, "Jaza bei")

    _ensure_open(await _sheet(sid, day_str))

    qty = int(body.qty)
    selling = int(body.selling)
    out_of_stock = body.variant_id is None
    qty_after = None
    stock_taken = 0
    line_id = str(ObjectId())

    if out_of_stock:
        name = (body.name or "").strip()
        if not name:
            raise HTTPException(422, "Jaza jina la bidhaa")
        if body.buying is None or int(body.buying) <= 0:
            raise HTTPException(422, "Jaza buying")
        buying = int(body.buying)
        line = {
            "id": line_id,
            "variant_id": None,
            "product_id": None,
            "name": name,
            "qty": qty,
            "selling": selling,
            "buying": buying,
            "stock_taken": 0,
            "out_of_stock": True,
            "created_at": now(),
        }
    else:
        product, variant = await stock.find_variant(sid, body.variant_id)
        # Snapshot ya mstari: buying ya mauzo haya inaweza kutofautiana na stock.
        # variants.buying, stock_selling na selling za stock hazibadiliki.
        if body.buying is not None:
            if int(body.buying) < 0:
                raise HTTPException(422, "Jaza buying")
            buying = int(body.buying)
        else:
            buying = int(variant.get("buying", 0))
        stock_taken, qty_after = await stock.take_stock(
            sid,
            product["_id"],
            variant["_id"],
            qty,
            variant["name"],
            buying,
            "daily",
            line_id,
            day_str,
        )
        line = {
            "id": line_id,
            "variant_id": variant["_id"],
            "product_id": product["_id"],
            "name": variant["name"],
            "qty": qty,
            "selling": selling,
            "buying": buying,
            "stock_selling": int(variant.get("selling", 0)),
            "stock_taken": stock_taken,
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
    old_line = next((l for l in (doc or {}).get("lines", []) if l.get("id") == line_id), None)
    if not old_line:
        raise HTTPException(404, "Haipo")

    _ensure_open(doc)

    new_qty = int(body.qty) if body.qty is not None else int(old_line["qty"])
    new_selling = int(body.selling) if body.selling is not None else int(old_line["selling"])

    if new_qty <= 0:
        raise HTTPException(422, "Jaza idadi")
    if new_selling <= 0:
        raise HTTPException(422, "Jaza bei")

    out_of_stock = bool(old_line.get("out_of_stock"))

    new_buying = None
    if body.buying is not None:
        new_buying = int(body.buying)
        if new_buying < 0 or (out_of_stock and new_buying <= 0):
            raise HTTPException(422, "Jaza buying")

    qty_after = None
    stock_taken = 0 if out_of_stock else int(old_line.get("stock_taken", 0) or 0)

    if not out_of_stock:
        delta = new_qty - int(old_line["qty"])
        if delta > 0:
            taken, qty_after = await stock.take_stock(
                sid,
                old_line["product_id"],
                old_line["variant_id"],
                delta,
                old_line["name"],
                int(old_line.get("buying", 0)),
                "daily_edit",
                line_id,
                day_str,
            )
            stock_taken += taken
        elif delta < 0:
            qty_after = await stock.return_stock(
                sid,
                old_line["product_id"],
                old_line["variant_id"],
                -delta,
                old_line["name"],
                int(old_line.get("buying", 0)),
                "daily_edit",
                line_id,
                day_str,
            )
            stock_taken = max(0, stock_taken + delta)

    updates: dict = {
        "lines.$.qty": new_qty,
        "lines.$.selling": new_selling,
        "lines.$.stock_taken": stock_taken,
        "updated_at": now(),
    }
    # Buying ya mstari pekee — stock haibadiliki.
    if new_buying is not None:
        updates["lines.$.buying"] = new_buying

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
    old_line = next((l for l in (doc or {}).get("lines", []) if l.get("id") == line_id), None)
    if not old_line:
        raise HTTPException(404, "Haipo")

    _ensure_open(doc)

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
        raise HTTPException(422, "Jaza jina la gharama")
    if body.amount is None or int(body.amount) <= 0:
        raise HTTPException(422, "Jaza kiasi")

    _ensure_open(await _sheet(sid, day_str))

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
    day = parse_day(date)
    if day > today():
        raise HTTPException(400, "Huwezi kuandika siku ijayo")
    day_str = day.isoformat()

    doc = await _sheet(sid, day_str)
    if not any(e.get("id") == expense_id for e in (doc or {}).get("expenses", [])):
        raise HTTPException(404, "Haipo")

    _ensure_open(doc)

    updates: dict = {"updated_at": now()}
    if body.name is not None:
        name = body.name.strip()
        if not name:
            raise HTTPException(422, "Jaza jina la gharama")
        updates["expenses.$.name"] = name
    if body.amount is not None:
        if int(body.amount) <= 0:
            raise HTTPException(422, "Jaza kiasi")
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
    day = parse_day(date)
    if day > today():
        raise HTTPException(400, "Huwezi kuandika siku ijayo")
    day_str = day.isoformat()

    doc = await _sheet(sid, day_str)
    if not any(e.get("id") == expense_id for e in (doc or {}).get("expenses", [])):
        raise HTTPException(404, "Haipo")

    _ensure_open(doc)

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
        taken_by_variant: dict[str, int] = {}
        for vid in set(list(old_qty) + list(new_qty)):
            delta = new_qty.get(vid, 0) - old_qty.get(vid, 0)
            if delta == 0:
                taken_by_variant[vid] = old_qty.get(vid, 0)
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
                taken, qa = await stock.take_stock(
                    sid, product["_id"], variant["_id"], delta, variant["name"],
                    variant.get("buying", 0), "daily", sheet_id, day_str, session=session,
                )
                taken_by_variant[vid] = old_qty.get(vid, 0) + taken
            else:
                qa = await stock.return_stock(
                    sid, product["_id"], variant["_id"], -delta, variant["name"],
                    variant.get("buying", 0), "daily_revert", sheet_id, day_str, session=session,
                )
                taken_by_variant[vid] = new_qty.get(vid, 0)
            touched.append((variant["name"], qa))

        # stock_taken halisi kwa kila mstari (stock pungufu inagawanywa kwa mstari wa kwanza)
        remaining = dict(taken_by_variant)
        for line in lines:
            vid = str(line["variant_id"])
            available = remaining.get(vid, int(line["qty"]))
            taken = min(int(line["qty"]), max(0, available))
            line["stock_taken"] = taken
            remaining[vid] = available - taken

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
