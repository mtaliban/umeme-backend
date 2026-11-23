"""Ripoti (P1–P4) — JSON kamili ya UMMU-RIPOTI (Siku · Wiki · Mwezi · Mwaka)."""

from collections import defaultdict
from datetime import date, timedelta

from ..db import db
from ..tz import DAY_NAMES, DAY_SHORT, MONTH_NAMES, MONTH_SHORT, month_end, today
from .summary import line_buying, variant_buying

# Risiti zisizofutwa (status au cancelled)
LIVE_RECEIPT = {"status": {"$ne": "cancelled"}, "cancelled": {"$ne": True}}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _iso(d: date) -> str:
    return d.isoformat()


def _week_start(d: date) -> date:
    """Jumapili ndio mwanzo wa wiki."""
    return d - timedelta(days=(d.weekday() + 1) % 7)


async def _rows(sid, start: str, end: str) -> tuple[list[tuple], dict[str, int]]:
    """Mistari yote ya mauzo kati ya tarehe (pamoja) + gharama kwa siku."""
    out: list[tuple] = []
    expenses: dict[str, int] = defaultdict(int)

    async for sheet in db.daily_sheets.find(
        {"shop_id": sid, "date": {"$gte": start, "$lte": end}}
    ):
        day = sheet["date"]
        fallback = await variant_buying(sid, sheet.get("lines", []))
        for line in sheet.get("lines", []):
            vid = line.get("variant_id")
            out.append(
                (
                    day,
                    line["name"],
                    str(vid) if vid else None,
                    int(line["qty"]),
                    int(line["selling"]),
                    line_buying(line, fallback),
                )
            )
        expenses[day] += sum(int(e.get("amount", 0) or 0) for e in sheet.get("expenses", []))

    async for receipt in db.receipts.find(
        {"shop_id": sid, "date": {"$gte": start, "$lte": end}, **LIVE_RECEIPT}
    ):
        day = receipt["date"]
        for item in receipt.get("items", []):
            vid = item.get("variant_id")
            out.append(
                (
                    day,
                    item["name"],
                    str(vid) if vid else None,
                    int(item["qty"]),
                    int(item["price"]) - int(item.get("discount", 0) or 0),
                    int(item.get("buying", 0) or 0),
                )
            )

    return out, dict(expenses)


def _summary(rows: list[tuple], expenses: int) -> dict:
    sales = sum(qty * selling for _, _, _, qty, selling, _ in rows)
    capital = sum(qty * buying for _, _, _, qty, _, buying in rows)
    return {
        "sales": sales,
        "capital": capital,
        "expenses": int(expenses),
        "product_profit": sales - capital,
        "net": sales - capital - int(expenses),
    }


def _by_name(rows: list[tuple]) -> list[dict]:
    """Bidhaa zinaunganishwa kwa jina; qty kubwa kwanza (zikilingana: sales)."""
    bucket: dict[str, dict] = {}
    for _, name, _, qty, selling, buying in rows:
        item = bucket.setdefault(name, {"name": name, "qty": 0, "sales": 0, "capital": 0})
        item["qty"] += qty
        item["sales"] += qty * selling
        item["capital"] += qty * buying
    for item in bucket.values():
        item["profit"] = item["sales"] - item["capital"]
    return sorted(bucket.values(), key=lambda p: (-p["qty"], -p["sales"]))


async def _has_data_before(sid, day: date) -> bool:
    before = {"$lt": _iso(day)}
    if await db.daily_sheets.find_one({"shop_id": sid, "date": before}, {"_id": 1}):
        return True
    if await db.receipts.find_one({"shop_id": sid, "date": before, **LIVE_RECEIPT}, {"_id": 1}):
        return True
    return False


async def _unsold(sid, rows: list[tuple]) -> list[dict]:
    """Aina za stock zisizouzwa hata moja kwenye kipindi (capital kubwa kwanza)."""
    sold_ids = {vid for _, _, vid, _, _, _ in rows if vid}
    sold_names = {name.lower() for _, name, _, _, _, _ in rows}
    out: list[dict] = []
    async for product in db.products.find({"shop_id": sid}):
        for variant in product.get("variants", []):
            if str(variant["_id"]) in sold_ids or variant["name"].lower() in sold_names:
                continue
            qty = max(int(variant.get("qty", 0) or 0), 0)
            out.append(
                {
                    "name": variant["name"],
                    "qty": qty,
                    "capital": qty * int(variant.get("buying", 0) or 0),
                }
            )
    out.sort(key=lambda v: (-v["capital"], v["name"]))
    return out[:20]


def _brief(item: dict) -> dict:
    return {"name": item["name"], "qty": item["qty"], "profit": item["profit"]}


def _expenses_between(expenses: dict[str, int], start: str, end: str) -> int:
    return sum(v for k, v in expenses.items() if start <= k <= end)


# ── P1: DayReport ─────────────────────────────────────────────────────────────

async def build_day(sid, day: date) -> dict:
    day_str = _iso(day)
    rows, expenses = await _rows(sid, day_str, day_str)
    products = _by_name(rows)
    summary = _summary(rows, expenses.get(day_str, 0))

    return {
        "period": "day",
        "date": day_str,
        "label": f"{DAY_NAMES[day.weekday()]}, {day.day} {MONTH_SHORT[day.month - 1]} {day.year}",
        "short_label": f"{DAY_NAMES[day.weekday()]}, {day.day} {MONTH_SHORT[day.month - 1]}",
        "has_prev": await _has_data_before(sid, day),
        "has_next": day < today(),
        "summary": summary,
        "products": [
            {
                "name": p["name"],
                "qty": p["qty"],
                "sales": p["sales"],
                "capital": p["capital"],
                "profit": p["profit"],
            }
            for p in products
        ],
        "totals": {
            "qty": sum(p["qty"] for p in products),
            "sales": summary["sales"],
            "profit": summary["product_profit"],
        },
    }


# ── P2–P4: PeriodReport ──────────────────────────────────────────────────────

def _chunks(period: str, anchor: date) -> tuple[date, date, list[tuple], str, str]:
    if period == "week":
        start = _week_start(anchor)
        end = start + timedelta(days=6)
        chunks = [
            (start + timedelta(days=i), DAY_SHORT[(start + timedelta(days=i)).weekday()],
             start + timedelta(days=i), start + timedelta(days=i))
            for i in range(7)
        ]
        if start.month == end.month:
            label = f"{start.day} – {end.day} {MONTH_NAMES[end.month - 1]} {end.year}"
            short = f"{start.day} – {end.day} {MONTH_SHORT[end.month - 1]} {end.year}"
        else:
            label = (
                f"{start.day} {MONTH_NAMES[start.month - 1]} – "
                f"{end.day} {MONTH_NAMES[end.month - 1]} {end.year}"
            )
            short = (
                f"{start.day} {MONTH_SHORT[start.month - 1]} – "
                f"{end.day} {MONTH_SHORT[end.month - 1]} {end.year}"
            )
        return start, end, chunks, label, short

    if period == "month":
        start = anchor.replace(day=1)
        end = month_end(anchor.year, anchor.month)
        chunks = []
        cursor = start
        while cursor <= end:
            chunk_end = min(_week_start(cursor) + timedelta(days=6), end)
            label = f"{cursor.day}–{chunk_end.day}" if cursor != chunk_end else f"{cursor.day}"
            chunks.append((cursor, label, cursor, chunk_end))
            cursor = chunk_end + timedelta(days=1)
        label = f"{MONTH_NAMES[start.month - 1]} {start.year}"
        return start, end, chunks, label, label

    start = date(anchor.year, 1, 1)
    end = date(anchor.year, 12, 31)
    chunks = [
        (date(anchor.year, m, 1), MONTH_SHORT[m - 1], date(anchor.year, m, 1), month_end(anchor.year, m))
        for m in range(1, 13)
    ]
    return start, end, chunks, str(anchor.year), str(anchor.year)


async def build_report(sid, period: str, anchor: date) -> dict:
    start, end, chunks, label, short = _chunks(period, anchor)
    start_str, end_str = _iso(start), _iso(end)
    rows, expenses = await _rows(sid, start_str, end_str)
    now = today()

    bars: list[dict] = []
    for key, chunk_label, chunk_start, chunk_end in chunks:
        if chunk_start > now:
            bars.append({"key": _iso(key), "label": chunk_label, "net": None})
            continue
        a, b = _iso(chunk_start), _iso(chunk_end)
        part = [r for r in rows if a <= r[0] <= b]
        bars.append(
            {
                "key": _iso(key),
                "label": chunk_label,
                "net": _summary(part, _expenses_between(expenses, a, b))["net"],
            }
        )

    products = _by_name(rows)
    top = [_brief(p) for p in products[:5]]
    low = [_brief(p) for p in sorted(products[5:], key=lambda p: (p["qty"], p["sales"]))[:3]]
    summary = _summary(rows, sum(expenses.values()))
    summary["net"] = sum(bar["net"] for bar in bars if bar["net"] is not None)

    return {
        "period": period,
        "start": start_str,
        "end": end_str,
        "label": label,
        "short_label": short,
        "has_prev": await _has_data_before(sid, start),
        "has_next": end < now,
        "summary": summary,
        "bars": bars,
        "top": top,
        "low": low,
        "unsold": await _unsold(sid, rows),
    }
