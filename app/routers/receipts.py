"""Risiti: kuandika, kuona, kufuta na historia."""

import re
from datetime import date, timedelta

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from ..auth import current_shop_id
from ..config import settings
from ..db import db
from ..schemas import ReceiptIn
from ..services import notify, stock, tx
from ..tz import DAY_NAMES, MONTH_SHORT, TZ, local_now, now, parse_day, today

router = APIRouter(tags=["receipts"])


def _fmt_time(dt) -> str:
    if not dt:
        return ""
    try:
        return dt.astimezone(TZ).strftime("%H:%M")
    except Exception:
        return ""


# Risiti zisizofutwa
LIVE = {"status": {"$ne": "cancelled"}, "cancelled": {"$ne": True}}


def _customer(receipt: dict) -> dict:
    customer = {"name": "", "phone": "", "location": "", "address": ""}
    customer.update({k: v for k, v in (receipt.get("customer") or {}).items() if k != "_id"})
    # `address` ni jina jipya; risiti/ombi la zamani linatumia `location`.
    # Zote mbili zinarudishwa, tupu ni "" (sio None).
    address = str(customer.get("address") or customer.get("location") or "").strip()
    customer["address"] = address
    customer["location"] = address
    return customer


def _paid(receipt: dict) -> int:
    return sum(
        int(it["qty"]) * (int(it["price"]) - int(it.get("discount", 0) or 0))
        for it in receipt.get("items", [])
    )


def _shop_public(shop: dict | None) -> dict:
    shop = shop or {}
    return {
        "name": shop.get("name", "UMMU AYMAN OUTFITS"),
        "phone": shop.get("phone", ""),
        "email": shop.get("email", ""),
        # Jina la muuzaji linalochapishwa kwenye risiti.
        "signature_name": shop.get("signature_name") or settings.signature_name,
    }


def receipt_out(receipt: dict, shop: dict | None = None) -> dict:
    """Receipt (C1/C2) — JSON kamili ya UMMU-RISITI."""
    items = []
    for it in receipt.get("items", []):
        qty = int(it["qty"])
        price = int(it["price"])
        discount = int(it.get("discount", 0) or 0)
        items.append(
            {
                "name": it["name"],
                # Jina la bidhaa kuu (mfano "Abaya") — liliwekwa wakati wa kuunda.
                "category": str(it.get("category") or ""),
                "qty": qty,
                "price": price,
                "discount": discount,
                "amount": qty * (price - discount),
            }
        )
    gross = sum(i["qty"] * i["price"] for i in items)
    discount_total = sum(i["qty"] * i["discount"] for i in items)
    return {
        "id": str(receipt["_id"]),
        "number": receipt["number"],
        "date": receipt["date"],
        "time": receipt.get("time") or _fmt_time(receipt.get("created_at")),
        "customer": _customer(receipt),
        "items": items,
        "total_qty": sum(i["qty"] for i in items),
        "gross": gross,
        "discount": discount_total,
        "paid": gross - discount_total,
        "shop": _shop_public(shop),
    }


def receipt_row(receipt: dict, shop: dict | None = None) -> dict:
    """Mstari wa TodayList / History (C0/C3).

    `customer` linabaki jina (string) kwa app ya zamani; fields za risiti
    zinaongezwa bila kubadilisha yaliyopo.
    """
    items = receipt.get("items", [])
    gross = sum(int(it["qty"]) * int(it["price"]) for it in items)
    discount = sum(int(it["qty"]) * int(it.get("discount", 0) or 0) for it in items)
    return {
        "id": str(receipt["_id"]),
        "number": receipt["number"],
        "date": receipt["date"],
        "customer": _customer(receipt)["name"] or "Mteja",
        "time": receipt.get("time") or _fmt_time(receipt.get("created_at")),
        "total_qty": sum(int(it["qty"]) for it in items),
        "gross": gross,
        "discount": discount,
        "paid": gross - discount,
        "shop": _shop_public(shop),
    }


# ── GET /receipts?date= ───────────────────────────────────────────────────────

@router.get("/receipts")
async def list_receipts(date: str | None = None, sid=Depends(current_shop_id)):
    """TodayList (C0)."""
    day = parse_day(date).isoformat()
    shop = await db.shops.find_one({"_id": sid}) or {}
    rows = []
    async for receipt in db.receipts.find({"shop_id": sid, "date": day, **LIVE}).sort("number", -1):
        row = receipt_row(receipt, shop)
        # TodayList: location ile ile iliyohifadhiwa kwenye risiti.
        row["location"] = _customer(receipt)["location"]
        rows.append(row)
    return {
        "date": day,
        "receipts": rows,
        "count": len(rows),
        "total": sum(row["paid"] for row in rows),
        "next_number": str(int(shop.get("receipt_seq", 0) or 0) + 1).zfill(4),
    }


# ── GET /receipts/history ─────────────────────────────────────────────────────

@router.get("/receipts/history")
async def receipts_history(
    q: str | None = None,
    before: str | None = None,
    limit: int = 50,
    sid=Depends(current_shop_id),
):
    """History (C3): tafuta kwa jina (neno la kwanza) au namba; panga kwa siku."""
    query: dict = {"shop_id": sid, **LIVE}
    if before:
        query["date"] = {"$lt": before}

    text = (q or "").strip()
    if text:
        if text.isdigit():
            query["number"] = text.zfill(4)
        else:
            query["customer.name"] = {"$regex": r"(^|\s)" + re.escape(text), "$options": "i"}

    limit = max(1, min(int(limit or 50), 500))
    receipts_list = [
        r async for r in db.receipts.find(query).sort([("date", -1), ("number", -1)]).limit(limit + 1)
    ]

    has_more = len(receipts_list) > limit
    if has_more:
        receipts_list = receipts_list[:limit]

    days: list[dict] = []
    index: dict[str, dict] = {}
    t = today()
    shop = await db.shops.find_one({"_id": sid})
    for receipt in receipts_list:
        day_str = receipt["date"]
        if day_str not in index:
            d = date.fromisoformat(day_str)
            base = f"{DAY_NAMES[d.weekday()].upper()} {d.day} {MONTH_SHORT[d.month - 1].upper()}"
            if d == t:
                label = f"LEO · {base}"
            elif d == t - timedelta(days=1):
                label = f"JANA · {base}"
            else:
                label = base
            index[day_str] = {"date": day_str, "label": label, "total": 0, "receipts": []}
            days.append(index[day_str])
        row = receipt_row(receipt, shop)
        index[day_str]["receipts"].append(row)
        index[day_str]["total"] += row["paid"]

    return {"days": days, "next_before": receipts_list[-1]["date"] if has_more and receipts_list else None}


# ── POST /receipts ────────────────────────────────────────────────────────────

async def _persist(sid, customer, items, day, session=None, client_id=None) -> dict:
    """Punguza stock (ya stock peke yake), chukua namba, hifadhi risiti."""
    applied: list[tuple] = []
    seq_taken = False

    async def rollback() -> None:
        if session is not None:
            return
        for pid, vid, qty, name, buying in reversed(applied):
            if pid is None:
                continue
            try:
                await stock.return_stock(sid, pid, vid, qty, name, buying, "receipt_cancel", None, day)
            except HTTPException:
                continue
        if seq_taken:
            await db.shops.update_one({"_id": sid}, {"$inc": {"receipt_seq": -1}})

    try:
        for item in items:
            if item.get("out_of_stock"):
                item["qty_after"] = None
                continue
            taken, qty_after = await stock.take_stock(
                sid,
                item["product_id"],
                item["variant_id"],
                item["qty"],
                item["name"],
                item["buying"],
                "receipt",
                None,
                day,
                session=session,
            )
            applied.append((item["product_id"], item["variant_id"], item["qty"], item["name"], item["buying"]))
            item["stock_taken"] = taken
            item["qty_after"] = qty_after

        shop = await db.shops.find_one_and_update(
            {"_id": sid},
            {"$inc": {"receipt_seq": 1}},
            return_document=ReturnDocument.AFTER,
            session=session,
        )
        seq_taken = True
        number = str(int((shop or {}).get("receipt_seq", 1))).zfill(4)

        totals = {
            "qty": sum(item["qty"] for item in items),
            "gross": sum(item["qty"] * item["price"] for item in items),
            "discount": sum(item["qty"] * item["discount"] for item in items),
            "paid": sum(item["qty"] * (item["price"] - item["discount"]) for item in items),
            "capital": sum(item["qty"] * item["buying"] for item in items),
        }
        totals["profit"] = totals["paid"] - totals["capital"]

        receipt = {
            "shop_id": sid,
            "number": number,
            "date": day,
            "time": local_now().strftime("%H:%M"),
            "created_at": now(),
            "status": "paid",
            "customer": customer,
            "items": [{k: v for k, v in item.items() if k != "qty_after"} for item in items],
            "totals": totals,
        }
        if client_id:
            receipt["client_id"] = client_id
        result = await db.receipts.insert_one(receipt, session=session)
        receipt["_id"] = result.inserted_id
        return receipt
    except HTTPException:
        await rollback()
        raise
    except DuplicateKeyError:
        await rollback()
        raise
    except Exception:
        await rollback()
        raise HTTPException(500, "Imeshindikana kuhifadhi risiti")


@router.post("/receipts", status_code=201)
async def create_receipt(body: ReceiptIn, request: Request, sid=Depends(current_shop_id)):
    if not body.items:
        raise HTTPException(422, "Weka bidhaa angalau moja")

    # Awamu 2: ombi lile lile (client_id ile ile) lisitoe risiti mbili.
    client_id = (body.client_id or "").strip() or None
    if client_id:
        existing = await db.receipts.find_one({"shop_id": sid, "client_id": client_id})
        if existing:
            return receipt_out(existing, await db.shops.find_one({"_id": sid}))

    day = parse_day(body.date)
    if day > today():
        raise HTTPException(400, "Huwezi kuandika siku ijayo")

    customer = dict(body.customer.model_dump() if body.customer else {})
    customer.pop("_id", None)
    customer["name"] = str(customer.get("name") or "").strip()
    customer["phone"] = str(customer.get("phone") or "").strip()
    # Hiari: haisababishi 422; tupu/None → "" (sio None), trim na kikomo cha 120.
    address = str(customer.get("address") or customer.get("location") or "").strip()[:120]
    customer["address"] = address
    customer["location"] = address  # jina la zamani — linabaki kwa app ya zamani

    items: list[dict] = []

    for line in body.items:
        if int(line.qty) < 1:
            raise HTTPException(422, "Jaza idadi")
        if int(line.price) < 1:
            raise HTTPException(422, "Jaza bei")
        if int(line.discount) < 0 or int(line.discount) > int(line.price):
            raise HTTPException(422, "Punguzo ni kubwa kuliko bei")

        if line.variant_id is None:
            # Bidhaa nje ya stock
            name = (line.name or "").strip()
            if not name:
                raise HTTPException(422, "Jaza jina la bidhaa")
            if line.buying is None:
                raise HTTPException(422, "Jaza buying")
            items.append(
                {
                    "variant_id": None,
                    "product_id": None,
                    "name": name,
                    "category": name,
                    "qty": int(line.qty),
                    "price": int(line.price),
                    "discount": int(line.discount),
                    "buying": max(0, int(line.buying)),
                    "out_of_stock": True,
                }
            )
        else:
            product, variant = await stock.find_variant(sid, line.variant_id)
            items.append(
                {
                    "product_id": product["_id"],
                    "variant_id": variant["_id"],
                    "name": variant["name"],
                    # Jina la bidhaa kuu (mfano "Abaya"), si la aina.
                    "category": product["name"],
                    "qty": int(line.qty),
                    "price": int(line.price),
                    "discount": int(line.discount),
                    "buying": int(variant.get("buying", 0)),
                    "out_of_stock": False,
                }
            )

    try:
        if await tx.supported():
            async with tx.transaction() as session:
                receipt = await _persist(
                    sid, customer, items, day.isoformat(), session, client_id
                )
        else:
            receipt = await _persist(sid, customer, items, day.isoformat(), None, client_id)
    except DuplicateKeyError:
        # Ombi lile lile lilifika wakati mmoja — rudisha risiti ya kwanza.
        if not client_id:
            raise
        existing = await db.receipts.find_one({"shop_id": sid, "client_id": client_id})
        if not existing:
            raise HTTPException(409, "Risiti imeshafanyika")
        return receipt_out(existing, await db.shops.find_one({"_id": sid}))

    device_token = request.headers.get("x-device-token")
    await notify.send(
        sid,
        "new_receipt",
        f"Risiti mpya Na. {receipt['number']}",
        f"{customer['name']} · {receipt['totals']['paid']}",
        {"receipt_id": str(receipt["_id"]), "number": receipt["number"]},
        exclude=device_token,
    )
    for item in items:
        qa = item.get("qty_after")
        if qa is not None:
            await stock.check_stock(sid, item["name"], int(qa))

    return receipt_out(receipt, await db.shops.find_one({"_id": sid}))


# ── GET /receipts/{id} ────────────────────────────────────────────────────────

@router.get("/receipts/{receipt_id}")
async def get_receipt(receipt_id: str, sid=Depends(current_shop_id)):
    try:
        rid = ObjectId(str(receipt_id))
    except Exception:
        raise HTTPException(404, "Haipo")
    receipt = await db.receipts.find_one({"_id": rid, "shop_id": sid})
    if not receipt:
        raise HTTPException(404, "Haipo")
    return receipt_out(receipt, await db.shops.find_one({"_id": sid}))


# ── POST /receipts/{id}/cancel ────────────────────────────────────────────────

async def _cancel(sid, receipt, rid, day, session=None) -> None:
    for item in receipt.get("items", []):
        if bool(item.get("out_of_stock")):
            continue
        qty = int(item.get("qty", 0))
        if qty <= 0:
            continue
        pid = item.get("product_id")
        vid = item.get("variant_id")
        if not pid or not vid:
            continue
        exists = await db.products.find_one({"_id": pid, "shop_id": sid}, {"_id": 1}, session=session)
        if not exists:
            continue
        await stock.return_stock(
            sid, pid, vid, qty, item["name"], item.get("buying", 0),
            "receipt_cancel", rid, day, session=session,
        )
    await db.receipts.update_one(
        {"_id": rid},
        {"$set": {"status": "cancelled", "cancelled": True, "cancelled_at": now()}},
        session=session,
    )


@router.post("/receipts/{receipt_id}/cancel")
async def cancel_receipt(receipt_id: str, sid=Depends(current_shop_id)):
    rid = stock.oid(receipt_id, "Risiti")
    receipt = await db.receipts.find_one({"_id": rid, "shop_id": sid})
    if not receipt:
        raise HTTPException(404, "Risiti haipo")
    if receipt.get("status") == "cancelled":
        raise HTTPException(400, "Risiti imekwisha kufutwa")

    day = today().isoformat()
    if await tx.supported():
        async with tx.transaction() as session:
            await _cancel(sid, receipt, rid, day, session)
    else:
        await _cancel(sid, receipt, rid, day, None)
    return {"ok": True}
