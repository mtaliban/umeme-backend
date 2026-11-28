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


async def _expense_entries(sid, start: str, end: str) -> list[tuple[str, str, int]]:
    """Gharama zote za kipindi kwa mpangilio zilivyoandikwa: (date, name, amount)."""
    entries: list[tuple[str, str, int]] = []
    async for sheet in db.daily_sheets.find(
        {"shop_id": sid, "date": {"$gte": start, "$lte": end}}
    ).sort("date", 1):
        for expense in sheet.get("expenses") or []:
            entries.append(
                (
                    sheet["date"],
                    str(expense.get("name") or "").strip(),
                    int(expense.get("amount", 0) or 0),
                )
            )
    return entries


def _expense_groups(entries: list[tuple[str, str, int]]) -> list[dict]:
    """Gharama zilizounganishwa kwa jina — kiasi kikubwa kwanza.

    Majina yalinganishwe bila herufi kubwa/ndogo na nafasi za pembeni; jina
    linalotumika ni lile la kwanza lililoonekana. Gharama isiyo na jina ni
    "Gharama".
    """
    bucket: dict[str, dict] = {}
    for _, name, amount in entries:
        label = (name or "").strip()
        key = label.lower()
        if not key:
            label, key = "Gharama", "gharama"
        item = bucket.get(key)
        if item is None:
            bucket[key] = {"name": label, "count": 1, "amount": int(amount)}
        else:
            item["count"] += 1
            item["amount"] += int(amount)
    return sorted(bucket.values(), key=lambda g: (-g["amount"], g["name"].lower()))


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
    entries = await _expense_entries(sid, day_str, day_str)

    return {
        "period": "day",
        "date": day_str,
        "label": f"{DAY_NAMES[day.weekday()]}, {day.day} {MONTH_SHORT[day.month - 1]} {day.year}",
        "short_label": f"{DAY_NAMES[day.weekday()]}, {day.day} {MONTH_SHORT[day.month - 1]}",
        "has_prev": await _has_data_before(sid, day),
        "has_next": day < today(),
        "summary": summary,
        # Gharama za siku kwa mpangilio zilivyoandikwa.
        "expenses": [
            {"name": name or "Gharama", "amount": amount} for _, name, amount in entries
        ],
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

def _chunks(period: str, anchor: date) -> tuple[date, date, list[dict], str, str]:
    """Vipindi vidogo vya ripoti: key, name, label, start, end."""
    if period == "week":
        start = _week_start(anchor)
        end = start + timedelta(days=6)
        chunks = []
        for i in range(7):
            d = start + timedelta(days=i)
            chunks.append(
                {
                    "key": _iso(d),
                    "name": f"{DAY_NAMES[d.weekday()]} {d.day}",
                    "label": DAY_SHORT[d.weekday()],
                    "start": d,
                    "end": d,
                }
            )
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
        chunks: list[dict] = []
        cursor = start
        while cursor <= end:
            chunk_end = min(_week_start(cursor) + timedelta(days=6), end)
            label = f"{cursor.day}–{chunk_end.day}" if cursor != chunk_end else f"{cursor.day}"
            if cursor == chunk_end:
                name = f"{cursor.day} {MONTH_SHORT[chunk_end.month - 1]}"
            else:
                name = (
                    f"{cursor.day} – {chunk_end.day} {MONTH_SHORT[chunk_end.month - 1]}"
                )
            chunks.append(
                {
                    "key": _iso(cursor),
                    "name": name,
                    "label": label,
                    "start": cursor,
                    "end": chunk_end,
                }
            )
            cursor = chunk_end + timedelta(days=1)
        label = f"{MONTH_NAMES[start.month - 1]} {start.year}"
        return start, end, chunks, label, label

    start = date(anchor.year, 1, 1)
    end = date(anchor.year, 12, 31)
    chunks = [
        {
            "key": _iso(date(anchor.year, m, 1)),
            "name": MONTH_NAMES[m - 1],
            "label": MONTH_SHORT[m - 1],
            "start": date(anchor.year, m, 1),
            "end": month_end(anchor.year, m),
        }
        for m in range(1, 13)
    ]
    return start, end, chunks, str(anchor.year), str(anchor.year)


async def build_report(sid, period: str, anchor: date) -> dict:
    start, end, chunks, label, short = _chunks(period, anchor)
    start_str, end_str = _iso(start), _iso(end)
    rows, expenses = await _rows(sid, start_str, end_str)
    entries = await _expense_entries(sid, start_str, end_str)
    now = today()

    bars: list[dict] = []
    for chunk in chunks:
        if chunk["start"] > now:
            # Kipindi ambacho hakijafika: zote null (app inaandika "—").
            bars.append(
                {
                    "key": chunk["key"],
                    "label": chunk["label"],
                    "name": chunk["name"],
                    "sales": None,
                    "capital": None,
                    "expenses": None,
                    "net": None,
                }
            )
            continue
        a, b = _iso(chunk["start"]), _iso(chunk["end"])
        part = [r for r in rows if a <= r[0] <= b]
        # Kipindi kilichopita bila mauzo: 0 (si null).
        part_summary = _summary(part, _expenses_between(expenses, a, b))
        bars.append(
            {
                "key": chunk["key"],
                "label": chunk["label"],
                "name": chunk["name"],
                "sales": part_summary["sales"],
                "capital": part_summary["capital"],
                "expenses": part_summary["expenses"],
                "net": part_summary["net"],
            }
        )

    products = _by_name(rows)
    top = [_brief(p) for p in products[:5]]
    low = [_brief(p) for p in sorted(products[5:], key=lambda p: (p["qty"], p["sales"]))[:3]]

    # Hesabu zilingane daima (4.5): bars = summary, na bidhaa = sales - capital.
    summary = {
        "sales": sum(bar["sales"] or 0 for bar in bars),
        "capital": sum(bar["capital"] or 0 for bar in bars),
        "expenses": sum(bar["expenses"] or 0 for bar in bars),
    }
    summary["product_profit"] = summary["sales"] - summary["capital"]
    summary["net"] = summary["sales"] - summary["capital"] - summary["expenses"]

    report = {
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
    if period == "week":
        report["expense_list"] = [
            {"date": day, "name": name or "Gharama", "amount": amount}
            for day, name, amount in entries
        ]
    else:
        report["expense_groups"] = _expense_groups(entries)
    return report
