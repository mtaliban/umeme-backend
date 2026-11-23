"""Hesabu za siku: muhtasari, vilivyouzwa, mistari ya risiti."""

from ..db import db
from ..tz import TZ

# Risiti zisizofutwa (spec: cancelled != true)
LIVE = {"status": {"$ne": "cancelled"}, "cancelled": {"$ne": True}}


def _add(bucket: dict, key: str, name: str, qty: int, revenue: int, cost: int) -> None:
    item = bucket.setdefault(key, {"name": name, "qty": 0, "revenue": 0, "cost": 0})
    item["qty"] += int(qty)
    item["revenue"] += int(revenue)
    item["cost"] += int(cost)


async def variant_buying(sid, lines: list[dict]) -> dict:
    """Buying ya sasa ya variants kwa mistari isiyo na `buying` (data za zamani)."""
    missing = [
        line["variant_id"]
        for line in lines
        if line.get("buying") is None and not line.get("out_of_stock") and line.get("variant_id")
    ]
    if not missing:
        return {}
    found: dict = {}
    async for product in db.products.find({"shop_id": sid, "variants._id": {"$in": missing}}):
        for variant in product.get("variants", []):
            if variant["_id"] in missing:
                found[variant["_id"]] = int(variant.get("buying", 0) or 0)
    return found


def line_buying(line: dict, fallback: dict | None = None) -> int:
    """Buying ya mstari (snapshot); mistari ya zamani hurudi kwenye variants.buying."""
    buying = line.get("buying")
    if buying is None:
        buying = (fallback or {}).get(line.get("variant_id"), 0)
    return int(buying or 0)


async def paid_receipts(sid, day: str) -> list[dict]:
    cursor = db.receipts.find({"shop_id": sid, "date": day, **LIVE}).sort("number", 1)
    return [r async for r in cursor]


async def sheet(sid, day: str) -> dict | None:
    return await db.daily_sheets.find_one({"shop_id": sid, "date": day})


async def day_summary(sid, day: str) -> dict:
    sales = capital = expenses = 0
    async for r in db.receipts.find({"shop_id": sid, "date": day, **LIVE}, {"totals": 1}):
        totals = r.get("totals") or {}
        sales += int(totals.get("paid", 0))
        capital += int(totals.get("capital", 0))
    doc = await sheet(sid, day)
    if doc:
        fallback = await variant_buying(sid, doc.get("lines", []))
        for line in doc.get("lines", []):
            sales += int(line["qty"]) * int(line["selling"])
            capital += int(line["qty"]) * line_buying(line, fallback)
        expenses = sum(int(e.get("amount", 0) or 0) for e in doc.get("expenses", []))
    return {
        "sales": sales,
        "capital": capital,
        "expenses": expenses,
        "product_profit": sales - capital,
        "net": sales - capital - expenses,
    }


async def day_items(sid, day: str) -> int:
    """Jumla ya idadi ya bidhaa zote za siku (risiti + daftari)."""
    qty = 0
    async for r in db.receipts.find({"shop_id": sid, "date": day, **LIVE}):
        for it in r.get("items", []):
            qty += int(it["qty"])
    doc = await sheet(sid, day)
    if doc:
        for line in doc.get("lines", []):
            qty += int(line["qty"])
    return qty


async def sold_items(sid, day: str) -> list[dict]:
    """Vilivyouzwa leo kwa jina: risiti + mstari wa daftari."""
    bucket: dict[str, dict] = {}
    async for r in db.receipts.find({"shop_id": sid, "date": day, **LIVE}):
        for it in r.get("items", []):
            qty = int(it["qty"])
            unit = int(it["price"]) - int(it.get("discount", 0) or 0)
            _add(bucket, it["name"], it["name"], qty, qty * unit, qty * int(it.get("buying", 0) or 0))
    doc = await sheet(sid, day)
    if doc:
        fallback = await variant_buying(sid, doc.get("lines", []))
        for line in doc.get("lines", []):
            qty = int(line["qty"])
            _add(
                bucket,
                line["name"],
                line["name"],
                qty,
                qty * int(line["selling"]),
                qty * line_buying(line, fallback),
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


async def sold_items_home(sid, day: str) -> list[dict]:
    """Vilivyouzwa kwa home: jina, qty, selling, sales, capital, profit — sorted qty desc."""
    bucket: dict[str, dict] = {}
    async for r in db.receipts.find({"shop_id": sid, "date": day, **LIVE}):
        for it in r.get("items", []):
            qty = int(it["qty"])
            unit = int(it["price"]) - int(it.get("discount", 0) or 0)
            cost = qty * int(it.get("buying", 0) or 0)
            item = bucket.setdefault(it["name"], {"name": it["name"], "qty": 0, "revenue": 0, "cost": 0})
            item["qty"] += qty
            item["revenue"] += qty * unit
            item["cost"] += cost
    doc = await sheet(sid, day)
    if doc:
        fallback = await variant_buying(sid, doc.get("lines", []))
        for line in doc.get("lines", []):
            qty = int(line["qty"])
            rev = qty * int(line["selling"])
            cost = qty * line_buying(line, fallback)
            item = bucket.setdefault(line["name"], {"name": line["name"], "qty": 0, "revenue": 0, "cost": 0})
            item["qty"] += qty
            item["revenue"] += rev
            item["cost"] += cost
    out = []
    for item in bucket.values():
        qty = item["qty"]
        out.append(
            {
                "name": item["name"],
                "qty": qty,
                "selling": item["revenue"] // qty if qty else 0,
                "sales": item["revenue"],
                "capital": item["cost"],
                "profit": item["revenue"] - item["cost"],
            }
        )
    out.sort(key=lambda x: (-x["qty"], -x["sales"]))
    return out


async def sold_variants(sid, day: str) -> dict[str, dict]:
    """vilivyouzwa leo kwa variant_id: qty na faida."""
    bucket: dict[str, dict] = {}
    async for r in db.receipts.find({"shop_id": sid, "date": day, **LIVE}):
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
        fallback = await variant_buying(sid, doc.get("lines", []))
        for line in doc.get("lines", []):
            qty = int(line["qty"])
            key = str(line.get("variant_id") or "")
            item = bucket.setdefault(key, {"qty": 0, "profit": 0})
            item["qty"] += qty
            item["profit"] += qty * (int(line["selling"]) - line_buying(line, fallback))
    return bucket


async def receipt_lines(sid, day: str) -> list[dict]:
    lines = []
    for r in await paid_receipts(sid, day):
        for index, it in enumerate(r.get("items", [])):
            qty = int(it["qty"])
            price = int(it["price"])
            discount = int(it.get("discount", 0) or 0)
            vid = it.get("variant_id")
            pid = it.get("product_id")
            lines.append(
                {
                    "id": f"rc_{r['number']}_{index}",
                    "receipt_id": str(r["_id"]),
                    "receipt_no": r["number"],
                    "number": r["number"],
                    "variant_id": str(vid) if vid else None,
                    "product_id": str(pid) if pid else None,
                    "name": it["name"],
                    "qty": qty,
                    "price": price,
                    "discount": discount,
                    "selling": price - discount,
                    "buying": int(it.get("buying", 0) or 0),
                    "stock_taken": int(it.get("stock_taken", 0) or 0),
                    "amount": qty * (price - discount),
                    "out_of_stock": bool(it.get("out_of_stock")),
                }
            )
    return lines


def sheet_out(doc: dict | None, buying_by_variant: dict | None = None) -> dict:
    if not doc:
        return {"date": None, "lines": [], "expenses": [], "saved_at": None, "updated_at": None}
    buying_by_variant = buying_by_variant or {}
    lines = []
    for line in doc.get("lines", []):
        vid = line.get("variant_id")
        pid = line.get("product_id")
        # Mistari ya zamani isiyo na buying: snapshot ya variants.buying ya sasa.
        lines.append(
            {
                "id": line.get("id", ""),
                "variant_id": str(vid) if vid else None,
                "product_id": str(pid) if pid else None,
                "name": line["name"],
                "qty": int(line["qty"]),
                "selling": int(line["selling"]),
                "buying": line_buying(line, buying_by_variant),
                "stock_selling": int(line.get("stock_selling", line["selling"]) or 0),
                "stock_taken": int(
                    line.get("stock_taken", 0 if line.get("out_of_stock") else line["qty"]) or 0
                ),
                "out_of_stock": bool(line.get("out_of_stock")),
            }
        )
    expenses = []
    for e in doc.get("expenses") or []:
        exp = dict(e)
        exp.pop("_id", None)
        exp.pop("created_at", None)
        if "id" not in exp:
            exp["id"] = ""
        expenses.append(exp)
    return {
        "date": doc.get("date"),
        "lines": lines,
        "expenses": expenses,
        "saved_at": doc.get("saved_at"),
        "updated_at": doc.get("updated_at"),
    }


def _fmt_time(dt, tz) -> str:
    if not dt:
        return ""
    try:
        return dt.astimezone(tz).strftime("%H:%M")
    except Exception:
        return ""


async def last_day_with_data(sid) -> str | None:
    """Siku ya mwisho yenye data yoyote (lines, risiti, au gharama) — haitegemei saved_at."""
    from ..tz import today_str
    t = today_str()
    d1 = await db.daily_sheets.find_one(
        {"shop_id": sid, "date": {"$lte": t},
         "$or": [{"lines.0": {"$exists": True}}, {"expenses.0": {"$exists": True}}]},
        sort=[("date", -1)],
        projection={"date": 1},
    )
    d2 = await db.receipts.find_one(
        {"shop_id": sid, "date": {"$lte": t}, **LIVE},
        sort=[("date", -1)],
        projection={"date": 1},
    )
    days = [x["date"] for x in (d1, d2) if x]
    return max(days) if days else None
