"""Risiti: kuandika, kuona na kufuta."""

from fastapi import APIRouter, Depends, HTTPException, Request
from pymongo import ReturnDocument

from ..auth import current_shop_id
from ..db import db
from ..schemas import ReceiptIn
from ..services import notify, stock, tx
from ..tz import now, parse_day, today_str

router = APIRouter(tags=["receipts"])


def receipt_out(receipt: dict) -> dict:
    customer = {"name": "", "phone": ""}
    customer.update(
        {k: v for k, v in (receipt.get("customer") or {}).items() if k != "_id"}
    )
    items = []
    for it in receipt.get("items", []):
        qty = int(it["qty"])
        price = int(it["price"])
        discount = int(it.get("discount", 0) or 0)
        items.append(
            {
                "variant_id": str(it["variant_id"]),
                "product_id": str(it["product_id"]),
                "name": it["name"],
                "qty": qty,
                "price": price,
                "discount": discount,
                "buying": int(it.get("buying", 0) or 0),
                "amount": qty * (price - discount),
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


@router.get("/receipts")
async def list_receipts(date: str | None = None, sid=Depends(current_shop_id)):
    day = parse_day(date).isoformat()
    cursor = db.receipts.find({"shop_id": sid, "date": day, "status": "paid"}).sort(
        [("created_at", -1), ("number", -1)]
    )
    return [receipt_out(r) async for r in cursor]


async def _persist(sid, customer, items, day, session=None) -> dict:
    """Punguza stock, chukua namba, hifadhi risiti."""
    applied: list[tuple] = []
    seq_taken = False

    async def rollback() -> None:
        if session is not None:
            return  # transaction itajifuta yenyewe
        for pid, vid, qty, name, buying in reversed(applied):
            try:
                await stock.return_stock(
                    sid, pid, vid, qty, name, buying, "receipt_cancel", None, day
                )
            except HTTPException:
                continue
        if seq_taken:
            await db.shops.update_one({"_id": sid}, {"$inc": {"receipt_seq": -1}})

    try:
        for item in items:
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
            applied.append(
                (item["product_id"], item["variant_id"], item["qty"], item["name"], item["buying"])
            )
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
            }
        )

    # Hakikisha stock inatosha kwa yote kwanza — hakuna kinachobadilika.
    for vid, qty in needed.items():
        current = await stock.variant_qty(
            sid, variants[vid]["product_id"], variants[vid]["variant_id"]
        )
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
        await stock.check_stock(sid, item["name"], int(item.get("qty_after", 0)))

    return receipt_out(receipt)


@router.get("/receipts/{receipt_id}")
async def get_receipt(receipt_id: str, sid=Depends(current_shop_id)):
    rid = stock.oid(receipt_id, "Risiti")
    receipt = await db.receipts.find_one({"_id": rid, "shop_id": sid})
    if not receipt:
        raise HTTPException(404, "Risiti haipo")
    return receipt_out(receipt)


async def _cancel(sid, receipt, rid, day, session=None) -> None:
    for item in receipt.get("items", []):
        qty = int(item.get("qty", 0))
        if qty <= 0:
            continue
        exists = await db.products.find_one(
            {"_id": item["product_id"], "shop_id": sid}, {"_id": 1}, session=session
        )
        if not exists:
            continue
        await stock.return_stock(
            sid,
            item["product_id"],
            item["variant_id"],
            qty,
            item["name"],
            item.get("buying", 0),
            "receipt_cancel",
            rid,
            day,
            session=session,
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
