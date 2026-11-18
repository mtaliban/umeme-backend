"""Ripoti za wiki, mwezi, mwaka na siku."""

from collections import defaultdict
from datetime import date, timedelta

from ..db import db
from ..tz import DAY_NAMES, DAY_SHORT, MONTH_NAMES, MONTH_SHORT, month_end, today


def _add(bucket: dict, key: str, name: str, qty: int, revenue: int, cost: int) -> None:
    item = bucket.setdefault(key, {"name": name, "qty": 0, "revenue": 0, "cost": 0})
    item["qty"] += int(qty)
    item["revenue"] += int(revenue)
    item["cost"] += int(cost)


def _stats(receipts: list[dict], sheets: list[dict]) -> tuple[dict, dict]:
    out = {"sales": 0, "capital": 0, "expenses": 0}
    items: dict[str, dict] = {}
    for r in receipts:
        totals = r.get("totals") or {}
        out["sales"] += int(totals.get("paid", 0))
        out["capital"] += int(totals.get("capital", 0))
        for it in r.get("items", []):
            qty = int(it["qty"])
            unit = int(it["price"]) - int(it.get("discount", 0) or 0)
            _add(items, str(it.get("variant_id") or it.get("name")), it["name"], qty, qty * unit, qty * int(it.get("buying", 0) or 0))
    for s in sheets:
        for line in s.get("lines", []):
            qty = int(line["qty"])
            _add(
                items,
                str(line.get("variant_id") or line.get("name")),
                line["name"],
                qty,
                qty * int(line["selling"]),
                qty * int(line.get("buying", 0) or 0),
            )
            out["sales"] += qty * int(line["selling"])
            out["capital"] += qty * int(line.get("buying", 0) or 0)
        out["expenses"] += sum(int(e.get("amount", 0) or 0) for e in s.get("expenses", []))
    return out, items


def _row_meta(period: str, anchor: date) -> list[dict]:
    """Safu za ripoti hadi leo tu."""
    t = today()
    rows: list[dict] = []
    if period == "week":
        start = anchor - timedelta(days=anchor.weekday())
        for i in range(7):
            d = start + timedelta(days=i)
            rows.append(
                {
                    "key": d.isoformat(),
                    "label": f"{DAY_NAMES[d.weekday()]} {d.day}",
                    "sub": f"{d.day} {MONTH_SHORT[d.month - 1]}",
                    "short": DAY_SHORT[d.weekday()],
                    "start": d,
                    "end": d,
                    "current": d == t,
                }
            )
    elif period == "month":
        spans = [(1, 7), (8, 14), (15, 21), (22, 28), (29, month_end(anchor.year, anchor.month).day)]
        for i, (a, b) in enumerate(spans, start=1):
            s = date(anchor.year, anchor.month, a)
            e = date(anchor.year, anchor.month, b)
            rows.append(
                {
                    "key": s.isoformat(),
                    "label": f"Wiki {i}",
                    "sub": f"{a} – {b}",
                    "short": f"W{i}",
                    "start": s,
                    "end": e,
                    "current": s <= t <= e,
                }
            )
    else:  # year
        last = t.month if anchor.year == t.year else 12
        for m in range(1, last + 1):
            s = date(anchor.year, m, 1)
            e = date(anchor.year, m, month_end(anchor.year, m).day)
            rows.append(
                {
                    "key": f"{anchor.year}-{m:02d}",
                    "label": MONTH_NAMES[m - 1],
                    "sub": str(anchor.year),
                    "short": MONTH_SHORT[m - 1],
                    "start": s,
                    "end": e,
                    "current": s <= t <= e,
                }
            )
    rows = [r for r in rows if r["start"] <= t]
    for r in rows:
        if r["end"] > t:
            r["end"] = t
    return rows


def _label(period: str, anchor: date, rows: list[dict]) -> str:
    if period == "week":
        start = rows[0]["start"] if rows else anchor - timedelta(days=anchor.weekday())
        end = start + timedelta(days=6)
        if start.month == end.month:
            return f"{start.day} – {end.day} {MONTH_NAMES[end.month - 1]} {end.year}"
        return (
            f"{start.day} {MONTH_NAMES[start.month - 1]} – "
            f"{end.day} {MONTH_NAMES[end.month - 1]} {end.year}"
        )
    if period == "month":
        return f"{MONTH_NAMES[anchor.month - 1]} {anchor.year}"
    if period == "year":
        return str(anchor.year)
    return f"{anchor.day} {MONTH_NAMES[anchor.month - 1]} {anchor.year}"


def _next_start(period: str, anchor: date, rows: list[dict]) -> date:
    if period == "week":
        first = rows[0]["start"] if rows else anchor - timedelta(days=anchor.weekday())
        return first + timedelta(days=7)
    if period == "month":
        first = rows[0]["start"] if rows else date(anchor.year, anchor.month, 1)
        if first.month == 12:
            return date(first.year + 1, 1, 1)
        return date(first.year, first.month + 1, 1)
    if period == "year":
        year = rows[0]["start"].year if rows else anchor.year
        return date(year + 1, 1, 1)
    return anchor + timedelta(days=1)


def _summary(stats: dict) -> dict:
    return {
        "sales": stats["sales"],
        "capital": stats["capital"],
        "expenses": stats["expenses"],
        "product_profit": stats["sales"] - stats["capital"],
        "net": stats["sales"] - stats["capital"] - stats["expenses"],
    }


async def _stock(sid) -> list[dict]:
    out = []
    async for p in db.products.find({"shop_id": sid}):
        for v in p.get("variants", []):
            out.append(
                {
                    "id": str(v["_id"]),
                    "name": v["name"],
                    "qty": int(v.get("qty", 0)),
                    "buying": int(v.get("buying", 0)),
                }
            )
    return out


async def build_report(sid, period: str, anchor: date) -> dict:
    rows_meta = _row_meta(period, anchor)
    by_receipt: dict[str, list[dict]] = defaultdict(list)
    by_sheet: dict[str, list[dict]] = defaultdict(list)
    start = end = None
    if rows_meta:
        start = rows_meta[0]["start"].isoformat()
        end = rows_meta[-1]["end"].isoformat()
        async for r in db.receipts.find(
            {"shop_id": sid, "status": "paid", "date": {"$gte": start, "$lte": end}}
        ):
            by_receipt[r["date"]].append(r)
        async for s in db.daily_sheets.find({"shop_id": sid, "date": {"$gte": start, "$lte": end}}):
            by_sheet[s["date"]].append(s)

    rows: list[dict] = []
    total = {"sales": 0, "capital": 0, "expenses": 0}
    all_receipts: list[dict] = []
    all_sheets: list[dict] = []
    for meta in rows_meta:
        r_list: list[dict] = []
        s_list: list[dict] = []
        d = meta["start"]
        while d <= meta["end"]:
            key = d.isoformat()
            r_list.extend(by_receipt.get(key, []))
            s_list.extend(by_sheet.get(key, []))
            d += timedelta(days=1)
        all_receipts.extend(r_list)
        all_sheets.extend(s_list)
        stats, items = _stats(r_list, s_list)
        best = max(items.values(), key=lambda x: x["revenue"] - x["cost"], default=None)
        rows.append(
            {
                "key": meta["key"],
                "label": meta["label"],
                "sub": meta["sub"],
                "short": meta["short"],
                "best_label": best["name"] if best else "",
                "sales": stats["sales"],
                "capital": stats["capital"],
                "expenses": stats["expenses"],
                "net": stats["sales"] - stats["capital"] - stats["expenses"],
                "current": meta["current"],
            }
        )
        for k in total:
            total[k] += stats[k]

    _, items = _stats(all_receipts, all_sheets)
    stock = await _stock(sid)
    sold = [
        {"id": k, "name": v["name"], "qty": v["qty"], "profit": v["revenue"] - v["cost"]}
        for k, v in items.items()
    ]
    sold.sort(key=lambda x: (-x["qty"], x["name"]))
    top = sold[:3]
    top_ids = {t["id"] for t in top}
    stock_profit = {k: v["revenue"] - v["cost"] for k, v in items.items()}
    low_pool = [
        {"id": s["id"], "name": s["name"], "qty": s["qty"], "profit": stock_profit.get(s["id"], 0)}
        for s in stock
        if s["id"] not in top_ids
    ]
    low_pool.sort(key=lambda x: (x["qty"], x["name"]))
    low = low_pool[:3]
    unsold = [
        {"name": s["name"], "qty": s["qty"]}
        for s in sorted(stock, key=lambda x: (-x["qty"], x["name"]))
        if s["qty"] > 0 and s["id"] not in items
    ][:5]

    capital_in_shop = sum(s["qty"] * s["buying"] for s in stock)

    purchases = 0
    if start and end:
        pipeline = [
            {
                "$match": {
                    "shop_id": sid,
                    "date": {"$gte": start, "$lte": end},
                    "reason": {"$in": ["new", "restock"]},
                    "change": {"$gt": 0},
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total": {"$sum": {"$multiply": ["$change", {"$ifNull": ["$buying", 0]}]}},
                }
            },
        ]
        async for doc in db.stock_movements.aggregate(pipeline):
            purchases = int(doc.get("total", 0) or 0)

    return {
        "period": period,
        "label": _label(period, anchor, rows_meta),
        "anchor": anchor.isoformat(),
        "has_next": _next_start(period, anchor, rows_meta) <= today(),
        "summary": _summary(total),
        "rows": rows,
        "top": [{"name": t["name"], "qty": t["qty"], "profit": t["profit"]} for t in top],
        "low": [{"name": t["name"], "qty": t["qty"], "profit": t["profit"]} for t in low],
        "unsold": unsold,
        "capital_in_shop": capital_in_shop,
        "purchases": purchases,
    }


async def build_day(sid, day: date) -> dict:
    receipts = [
        r
        async for r in db.receipts.find(
            {"shop_id": sid, "date": day.isoformat(), "status": "paid"}
        )
    ]
    sheet = await db.daily_sheets.find_one({"shop_id": sid, "date": day.isoformat()})
    stats, items = _stats(receipts, [sheet] if sheet else [])
    rows = [
        {
            "name": v["name"],
            "qty": v["qty"],
            "profit": v["revenue"] - v["cost"],
        }
        for v in items.values()
    ]
    rows.sort(key=lambda x: (-x["profit"], x["name"]))
    return {
        "date": day.isoformat(),
        "label": f"{DAY_NAMES[day.weekday()]}, {day.day} {MONTH_SHORT[day.month - 1]}",
        "items": rows,
        "summary": _summary(stats),
        "period": "day",
        "anchor": day.isoformat(),
        "has_next": day + timedelta(days=1) <= today(),
    }
