"""Hesabu za siku: muhtasari, vilivyouzwa, mistari ya risiti."""

from collections import defaultdict

from ..db import db


def _add(bucket: dict, key: str, name: str, qty: int, revenue: int, cost: int) -> None:
    item = bucket.setdefault(key, {"name": name, "qty": 0, "revenue": 0, "cost": 0})
    item["qty"] += int(qty)
    item["revenue"] += int(revenue)
    item["cost"] += int(cost)


async def paid_receipts(sid, day: str) -> list[dict]:
    cursor = db.receipts.find({"shop_id": sid, "date": day, "status": "paid"}).sort("number", 1)
    return [r async for r in cursor]


async def sheet(sid, day: str) -> dict | None:
    return await db.daily_sheets.find_one({"shop_id": sid, "date": day})


async def day_summary(sid, day: str) -> dict:
    sales = capital = expenses = 0
    async for r in db.receipts.find({"shop_id": sid, "date": day, "status": "paid"}, {"totals": 1}):
        totals = r.get("totals") or {}
        sales += int(totals.get("paid", 0))
        capital += int(totals.get("capital", 0))
    doc = await sheet(sid, day)
    if doc:
        for line in doc.get("lines", []):
            sales += int(line["qty"]) * int(line["selling"])
            capital += int(line["qty"]) * int(line.get("buying", 0))
        expenses = sum(int(e.get("amount", 0) or 0) for e in doc.get("expenses", []))
    return {
        "sales": sales,
        "capital": capital,
        "expenses": expenses,
        "product_profit": sales - capital,
        "net": sales - capital - expenses,
    }


async def sold_items(sid, day: str) -> list[dict]:
    """Vilivyouzwa leo kwa jina: risiti + mstari wa daftari."""
    bucket: dict[str, dict] = {}
    async for r in db.receipts.find({"shop_id": sid, "date": day, "status": "paid"}):
        for it in r.get("items", []):
            qty = int(it["qty"])
            unit = int(it["price"]) - int(it.get("discount", 0) or 0)
            _add(bucket, it["name"], it["name"], qty, qty * unit, qty * int(it.get("buying", 0) or 0))
    doc = await sheet(sid, day)
    if doc:
        for line in doc.get("lines", []):
            qty = int(line["qty"])
            _add(
                bucket,
                line["name"],
                line["name"],
                qty,
                qty * int(line["selling"]),
                qty * int(line.get("buying", 0) or 0),
            )
    out = []
    for item in bucket.values():
        qty = item["qty"]
        out.append(
            {
                "name": item["name"],
                "qty": qty,
                "buying": item["cost"] // qty if qty else 0,
                "selling": item["revenue"] // qty if qty else 0,
                "profit": item["revenue"] - item["cost"],
            }
        )
    out.sort(key=lambda x: (-x["profit"], x["name"]))
    return out


async def sold_variants(sid, day: str) -> dict[str, dict]:
    """vilivyouzwa leo kwa variant_id: qty na faida."""
    bucket: dict[str, dict] = {}
    async for r in db.receipts.find({"shop_id": sid, "date": day, "status": "paid"}):
        for it in r.get("items", []):
            qty = int(it["qty"])
            unit = int(it["price"]) - int(it.get("discount", 0) or 0)
            buying = int(it.get("buying", 0) or 0)
            key = str(it.get("variant_id") or "")
            item = bucket.setdefault(key, {"qty": 0, "profit": 0})
            item["qty"] += qty
            item["profit"] += qty * (unit - buying)
    doc = await sheet(sid, day)
    if doc:
        for line in doc.get("lines", []):
            qty = int(line["qty"])
            key = str(line.get("variant_id") or "")
            item = bucket.setdefault(key, {"qty": 0, "profit": 0})
            item["qty"] += qty
            item["profit"] += qty * (int(line["selling"]) - int(line.get("buying", 0) or 0))
    return bucket


async def receipt_lines(sid, day: str) -> list[dict]:
    lines = []
    for r in await paid_receipts(sid, day):
        for it in r.get("items", []):
            qty = int(it["qty"])
            price = int(it["price"])
            discount = int(it.get("discount", 0) or 0)
            lines.append(
                {
                    "receipt_id": str(r["_id"]),
                    "receipt_no": r["number"],
                    "number": r["number"],
                    "variant_id": str(it["variant_id"]),
                    "product_id": str(it["product_id"]),
                    "name": it["name"],
                    "qty": qty,
                    "price": price,
                    "discount": discount,
                    "selling": price - discount,
                    "buying": int(it.get("buying", 0) or 0),
                    "amount": qty * (price - discount),
                }
            )
    return lines


def sheet_out(doc: dict | None) -> dict:
    if not doc:
        return {"date": None, "lines": [], "expenses": [], "saved_at": None, "updated_at": None}
    lines = []
    for line in doc.get("lines", []):
        lines.append(
            {
                "variant_id": str(line["variant_id"]),
                "product_id": str(line["product_id"]),
                "name": line["name"],
                "qty": int(line["qty"]),
                "selling": int(line["selling"]),
                "buying": int(line.get("buying", 0) or 0),
                "stock_selling": int(line.get("stock_selling", line["selling"]) or 0),
            }
        )
    return {
        "date": doc.get("date"),
        "lines": lines,
        "expenses": list(doc.get("expenses") or []),
        "saved_at": doc.get("saved_at"),
        "updated_at": doc.get("updated_at"),
    }
