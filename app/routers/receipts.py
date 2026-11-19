"""Risiti: kuandika, kuona, kufuta na historia."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from pymongo import ReturnDocument

from ..auth import current_shop_id
from ..db import db
from ..schemas import ReceiptIn
from ..services import notify, stock, tx
from ..tz import DAY_NAMES, MONTH_SHORT, TZ, now, parse_day, today, today_str

router = APIRouter(tags=["receipts"])


def _fmt_time(dt) -> str:
    if not dt:
        return ""
    try:
        return dt.astimezone(TZ).strftime("%H:%M")
    except Exception:
        return ""


def receipt_out(receipt: dict) -> dict:
    customer = {"name": "", "phone": ""}
    customer.update({k: v for k, v in (receipt.get("customer") or {}).items() if k != "_id"})
    items = []
    for it in receipt.get("items", []):
        qty = int(it["qty"])
        price = int(it["price"])
        discount = int(it.get("discount", 0) or 0)
        vid = it.get("variant_id")
        pid = it.get("product_id")
        items.append(
            {
                "variant_id": str(vid) if vid else None,
                "product_id": str(pid) if pid else None,
                "name": it["name"],
                "qty": qty,
                "price": price,
                "discount": discount,
                "buying": int(it.get("buying", 0) or 0),
                "amount": qty * (price - discount),
                "out_of_stock": bool(it.get("out_of_stock")),
            }
        )
    return {
        "id": str(receipt["_id"]),
        "number": receipt["number"],
        "date": receipt["date"],
        "created_at": receipt.get("created_at"),
        "status": receipt.get("status", "paid"),
        "customer": customer,
        "items": items,
        "totals": receipt.get("totals", {}),
    }


# ── GET /receipts?date= ───────────────────────────────────────────────────────

@router.get("/receipts")
async def list_receipts(date: str | None = None, sid=Depends(current_shop_id)):
    day = parse_day(date).isoformat()
    cursor = db.receipts.find({"shop_id": sid, "date": day, "status": "paid"}).sort(
        [("created_at", -1), ("number", -1)]
    )
    return [receipt_out(r) async for r in cursor]


# ── GET /receipts/history ─────────────────────────────────────────────────────

@router.get("/receipts/history")
async def receipts_history(
    q: str | None = None,
    before: str | None = None,
    limit: int = 50,
    sid=Depends(current_shop_id),
):
    query: dict = {"shop_id": sid, "status": "paid"}
    if before:
        query["date"] = {"$lt": before}

    if q:
        # Tafuta kwa jina la mteja au namba ya risiti
        import re
        q_clean = re.escape(q.strip())
        query["$or"] = [
            {"customer.name": {"$regex": q_clean, "$options": "i"}},
            {"number": {"$regex": f"^{q_clean}"}},
        ]

    cursor = db.receipts.find(query).sort([("date", -1), ("number", -1)]).limit(limit + 1)
    receipts_list = [r async for r in cursor]

    has_more = len(receipts_list) > limit
    if has_more:
        receipts_list = receipts_list[:limit]

    # Panga kwa siku
    days_dict: dict[str, dict] = {}
    t = today()
    for r in receipts_list:
        d_str = r["date"]
        if d_str not in days_dict:
            d = date.fromisoformat(d_str)
            if d == t:
                label = f"LEO · {DAY_NAMES[d.weekday()].upper()} {d.day} {MONTH_SHORT[d.month - 1].upper()}"
            elif d == t - timedelta(days=1):
                label = f"JANA · {DAY_NAMES[d.weekday()].upper()} {d.day} {MONTH_SHORT[d.month - 1].upper()}"
            else:
                label = f"{DAY_NAMES[d.weekday()].upper()} {d.day} {MONTH_SHORT[d.month - 1].upper()}"
            days_dict[d_str] = {"date": d_str, "label": label, "total": 0, "receipts": []}
        paid = int((r.get("totals") or {}).get("paid", 0))
        days_dict[d_str]["total"] += paid
        days_dict[d_str]["receipts"].append(
            {
                "id": str(r["_id"]),
                "number": r["number"],
                "customer": {
                    "name": (r.get("customer") or {}).get("name", ""),
                    "phone": (r.get("customer") or {}).get("phone", ""),
                },
                "time": _fmt_time(r.get("created_at")),
                "paid": paid,
            }
        )

    days = sorted(days_dict.values(), key=lambda x: x["date"], reverse=True)
    next_before = receipts_list[-1]["date"] if has_more and receipts_list else None

    return {"days": days, "next_before": next_before}


# ── POST /receipts ────────────────────────────────────────────────────────────

async def _persist(sid, customer, items, day, session=None) -> dict:
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
            qty_after = await stock.take_stock(
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
            "created_at": now(),
            "status": "paid",
            "customer": customer,
            "items": [{k: v for k, v in item.items() if k != "qty_after"} for item in items],
            "totals": totals,
        }
        result = await db.receipts.insert_one(receipt, session=session)
        receipt["_id"] = result.inserted_id
        return receipt
    except HTTPException:
        await rollback()
        raise
    except Exception:
        await rollback()
        raise HTTPException(500, "Imeshindikana kuhifadhi risiti")


@router.post("/receipts", status_code=201)
async def create_receipt(body: ReceiptIn, request: Request, sid=Depends(current_shop_id)):
    customer = dict(body.customer.model_dump())
    customer.pop("_id", None)
    customer["name"] = str(customer.get("name") or "").strip()
    customer["phone"] = str(customer.get("phone") or "").strip()
    if not customer["name"]:
        raise HTTPException(400, "Andika jina la mteja")
    if not body.items:
        raise HTTPException(400, "Ongeza bidhaa angalau moja")

    items: list[dict] = []
    needed: dict[str, int] = {}
    variants: dict[str, dict] = {}

    for line in body.items:
        if int(line.qty) <= 0:
            raise HTTPException(400, "Idadi iwe kubwa kuliko 0")
        if int(line.price) <= 0:
            raise HTTPException(400, "Bei iwe kubwa kuliko 0")
        if int(line.discount) < 0 or int(line.discount) > int(line.price):
            raise HTTPException(400, "Punguzo si sahihi")

        if line.variant_id is None:
            # Bidhaa nje ya stock
            name = (line.name or "").strip()
            if not name:
                raise HTTPException(400, "Andika jina la bidhaa")
            items.append(
                {
                    "variant_id": None,
                    "product_id": None,
                    "name": name,
                    "qty": int(line.qty),
                    "price": int(line.price),
                    "discount": int(line.discount),
                    "buying": max(0, int(line.buying or 0)),
                    "out_of_stock": True,
                }
            )
        else:
            product, variant = await stock.find_variant(sid, line.variant_id)
            vid = str(variant["_id"])
            needed[vid] = needed.get(vid, 0) + int(line.qty)
            variants[vid] = {
                "product_id": product["_id"],
                "variant_id": variant["_id"],
                "name": variant["name"],
                "buying": int(variant.get("buying", 0)),
            }
            items.append(
                {
                    "product_id": product["_id"],
                    "variant_id": variant["_id"],
                    "name": variant["name"],
                    "qty": int(line.qty),
                    "price": int(line.price),
                    "discount": int(line.discount),
                    "buying": int(variant.get("buying", 0)),
                    "out_of_stock": False,
                }
            )

    # Hakikisha stock inatosha kwa zote kwanza
    for vid, qty in needed.items():
        current = await stock.variant_qty(sid, variants[vid]["product_id"], variants[vid]["variant_id"])
        if current < qty:
            raise HTTPException(400, f"{variants[vid]['name']}: zipo {current} tu")

    day = today_str()
    if await tx.supported():
        async with tx.transaction() as session:
            receipt = await _persist(sid, customer, items, day, session)
    else:
        receipt = await _persist(sid, customer, items, day, None)

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

    return receipt_out(receipt)


# ── GET /receipts/{id} ────────────────────────────────────────────────────────

@router.get("/receipts/{receipt_id}")
async def get_receipt(receipt_id: str, sid=Depends(current_shop_id)):
    rid = stock.oid(receipt_id, "Risiti")
    receipt = await db.receipts.find_one({"_id": rid, "shop_id": sid})
    if not receipt:
        raise HTTPException(404, "Risiti haipo")
    return receipt_out(receipt)


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
        {"$set": {"status": "cancelled", "cancelled_at": now()}},
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

    day = today_str()
    if await tx.supported():
        async with tx.transaction() as session:
            await _cancel(sid, receipt, rid, day, session)
    else:
        await _cancel(sid, receipt, rid, day, None)
    return {"ok": True}
