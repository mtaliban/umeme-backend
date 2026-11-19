"""Ripoti za wiki, mwezi, mwaka na siku."""

from collections import defaultdict
from datetime import date, timedelta

from ..db import db
from ..tz import DAY_NAMES, DAY_SHORT, MONTH_NAMES, MONTH_SHORT, TZ, month_end, today


# ── Helpers ───────────────────────────────────────────────────────────────────

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
            cost = qty * int(it.get("buying", 0) or 0)
            key = str(it.get("variant_id") or it.get("name", ""))
            _add(items, key, it["name"], qty, qty * unit, cost)
    for s in sheets:
        for line in s.get("lines", []):
            qty = int(line["qty"])
            rev = qty * int(line["selling"])
            cost = qty * int(line.get("buying", 0) or 0)
            key = str(line.get("variant_id") or line.get("name", ""))
            _add(items, key, line["name"], qty, rev, cost)
            out["sales"] += rev
            out["capital"] += cost
        out["expenses"] += sum(int(e.get("amount", 0) or 0) for e in s.get("expenses", []))
    return out, items


def _summary(stats: dict) -> dict:
    return {
        "sales": stats["sales"],
        "capital": stats["capital"],
        "expenses": stats["expenses"],
        "product_profit": stats["sales"] - stats["capital"],
        "net": stats["sales"] - stats["capital"] - stats["expenses"],
    }


def _top_low(items: dict, n: int = 3) -> tuple[list, list]:
    sold = sorted(items.values(), key=lambda x: (-x["qty"], x["name"]))
    top_raw = sold[:n]
    top_keys = {id(t) for t in top_raw}
    low_pool = [s for s in sold if id(s) not in top_keys]
    low_raw = sorted(low_pool, key=lambda x: (x["qty"], x["name"]))[:n]

    def _fmt(v: dict) -> dict:
        return {
            "name": v["name"],
            "qty": v["qty"],
            "sales": v["revenue"],
            "capital": v["cost"],
            "profit": v["revenue"] - v["cost"],
        }

    return [_fmt(t) for t in top_raw], [_fmt(t) for t in low_raw]


def _expenses_grouped(sheets: list[dict]) -> list[dict]:
    bucket: dict[str, int] = {}
    for s in sheets:
        for e in s.get("expenses", []):
            name = str(e.get("name", "") or "").strip()
            if name:
                bucket[name] = bucket.get(name, 0) + int(e.get("amount", 0) or 0)
    return [{"name": k, "amount": v} for k, v in sorted(bucket.items())]


async def _capital_in_shop(sid) -> int:
    total = 0
    async for p in db.products.find({"shop_id": sid}):
        for v in p.get("variants", []):
            total += int(v.get("qty", 0)) * int(v.get("buying", 0))
    return total


async def _purchases(sid, start: str, end: str) -> int:
    pipeline = [
        {
            "$match": {
                "shop_id": sid,
                "date": {"$gte": start, "$lte": end},
                "reason": {"$in": ["new", "restock"]},
                "change": {"$gt": 0},
            }
        },
        {"$group": {"_id": None, "total": {"$sum": {"$multiply": ["$change", {"$ifNull": ["$buying", 0]}]}}}},
    ]
    async for doc in db.stock_movements.aggregate(pipeline):
        return int(doc.get("total", 0) or 0)
    return 0


async def _unsold(sid, items: dict) -> list[dict]:
    out = []
    async for p in db.products.find({"shop_id": sid}):
        for v in p.get("variants", []):
            key = str(v["_id"])
            if key not in items and int(v.get("qty", 0)) > 0:
                out.append({"name": v["name"], "qty": int(v.get("qty", 0))})
    out.sort(key=lambda x: (-x["qty"], x["name"]))
    return out[:5]


def _fmt_time(dt) -> str:
    if not dt:
        return ""
    try:
        return dt.astimezone(TZ).strftime("%H:%M")
    except Exception:
        return ""


# ── Week rows (Jumatatu–Jumapili) ─────────────────────────────────────────────

def _week_days(anchor: date) -> list[dict]:
    t = today()
    start = anchor - timedelta(days=anchor.weekday())
    days = []
    for i in range(7):
        d = start + timedelta(days=i)
        if d > t:
            break
        days.append({"key": d.isoformat(), "label": DAY_SHORT[d.weekday()], "date": d})
    return days


# ── Month: calendar weeks cut by month boundaries ────────────────────────────

def _month_weeks(anchor: date) -> list[dict]:
    """Wiki za mwezi kwa tarehe halisi za Jumatatu–Jumapili zilizokatwa na mipaka ya mwezi."""
    t = today()
    year, month = anchor.year, anchor.month
    first = date(year, month, 1)
    last = month_end(year, month)

    weeks = []
    # Anza Jumatatu ya wiki ya kwanza
    cur = first - timedelta(days=first.weekday())
    week_num = 0
    while cur <= last:
        w_start = max(cur, first)
        w_end = min(cur + timedelta(days=6), last)
        if w_end >= first and w_start <= t:
            actual_end = min(w_end, t)
            week_num += 1
            weeks.append(
                {
                    "key": w_start.isoformat(),
                    "start": w_start,
                    "end": actual_end,
                    "full_end": w_end,
                    "week_num": week_num,
                    "current": w_start <= t <= w_end,
                }
            )
        cur += timedelta(days=7)
    return weeks


# ── Year rows (Jan–current) ───────────────────────────────────────────────────

def _year_months(anchor: date) -> list[dict]:
    t = today()
    last = t.month if anchor.year == t.year else 12
    months = []
    for m in range(1, last + 1):
        s = date(anchor.year, m, 1)
        e = min(date(anchor.year, m, month_end(anchor.year, m).day), t)
        months.append(
            {
                "key": f"{anchor.year}-{m:02d}",
                "label": MONTH_SHORT[m - 1],
                "start": s,
                "end": e,
                "current": s <= t <= date(anchor.year, m, month_end(anchor.year, m).day),
                "net_null": False,
            }
        )
    # Miezi ijayo ya mwaka huo inaonekana na net: null
    if anchor.year == t.year:
        for m in range(t.month + 1, 13):
            s = date(anchor.year, m, 1)
            months.append(
                {
                    "key": f"{anchor.year}-{m:02d}",
                    "label": MONTH_SHORT[m - 1],
                    "start": s,
                    "end": s,
                    "current": False,
                    "net_null": True,
                }
            )
    return months


# ── Period label ──────────────────────────────────────────────────────────────

def _period_label(period: str, anchor: date) -> str:
    if period == "week":
        start = anchor - timedelta(days=anchor.weekday())
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
    return f"{DAY_NAMES[anchor.weekday()]}, {anchor.day} {MONTH_NAMES[anchor.month - 1]} {anchor.year}"


# ── has_prev / has_next ───────────────────────────────────────────────────────

def _has_next(period: str, anchor: date) -> bool:
    t = today()
    if period == "week":
        start = anchor - timedelta(days=anchor.weekday())
        return start + timedelta(days=7) <= t
    if period == "month":
        nxt = date(anchor.year + 1 if anchor.month == 12 else anchor.year, (anchor.month % 12) + 1, 1)
        return nxt <= t
    if period == "year":
        return date(anchor.year + 1, 1, 1) <= t
    return anchor + timedelta(days=1) <= t


def _period_start_end(period: str, anchor: date) -> tuple[date, date]:
    t = today()
    if period == "week":
        start = anchor - timedelta(days=anchor.weekday())
        end = start + timedelta(days=6)
        return start, end
    if period == "month":
        start = date(anchor.year, anchor.month, 1)
        end = month_end(anchor.year, anchor.month)
        return start, end
    if period == "year":
        return date(anchor.year, 1, 1), date(anchor.year, 12, 31)
    return anchor, anchor


# ── build_report ──────────────────────────────────────────────────────────────

async def build_report(sid, period: str, anchor: date) -> dict:
    t = today()
    p_start, p_end = _period_start_end(period, anchor)
    fetch_start = p_start.isoformat()
    fetch_end = min(p_end, t).isoformat()

    by_receipt: dict[str, list[dict]] = defaultdict(list)
    by_sheet: dict[str, list[dict]] = defaultdict(list)

    async for r in db.receipts.find(
        {"shop_id": sid, "status": "paid", "date": {"$gte": fetch_start, "$lte": fetch_end}}
    ):
        by_receipt[r["date"]].append(r)
    async for s in db.daily_sheets.find(
        {"shop_id": sid, "date": {"$gte": fetch_start, "$lte": fetch_end}}
    ):
        by_sheet[s["date"]].append(s)

    all_receipts: list[dict] = [r for rs in by_receipt.values() for r in rs]
    all_sheets: list[dict] = [s for ss in by_sheet.values() for s in ss]

    total = {"sales": 0, "capital": 0, "expenses": 0}
    bars: list[dict] = []
    weeks_out: list[dict] = []

    if period == "week":
        for meta in _week_days(anchor):
            d = meta["date"]
            key = d.isoformat()
            r_list = by_receipt.get(key, [])
            s_list = by_sheet.get(key, [])
            stats, _ = _stats(r_list, s_list)
            net = stats["sales"] - stats["capital"] - stats["expenses"]
            # Wiki: siku zenye biashara tu
            if stats["sales"] > 0 or stats["expenses"] > 0:
                bars.append({"key": key, "label": meta["label"], "net": net})
            for k in total:
                total[k] += stats[k]

    elif period == "month":
        for meta in _month_weeks(anchor):
            w_start = meta["start"]
            w_end = meta["end"]
            r_list: list[dict] = []
            s_list: list[dict] = []
            d = w_start
            while d <= w_end:
                r_list.extend(by_receipt.get(d.isoformat(), []))
                s_list.extend(by_sheet.get(d.isoformat(), []))
                d += timedelta(days=1)
            stats, _ = _stats(r_list, s_list)
            net = stats["sales"] - stats["capital"] - stats["expenses"]
            for k in total:
                total[k] += stats[k]

            w_num = meta["week_num"]
            is_current = meta["current"]
            full_end = meta["full_end"]
            if is_current and full_end > t:
                sub = "Wiki hii · inaendelea"
            else:
                sub = f"Wiki {w_num}"

            full_start = meta["start"]
            full_end_str = meta["full_end"]
            if full_start.month == full_end_str.month:
                range_label = f"{full_start.day} – {full_end_str.day} {MONTH_SHORT[full_start.month - 1]}"
            else:
                range_label = (
                    f"{full_start.day} {MONTH_SHORT[full_start.month - 1]} – "
                    f"{full_end_str.day} {MONTH_SHORT[full_end_str.month - 1]}"
                )
            bar = {"key": meta["key"], "label": f"W{w_num}", "net": net}
            bars.append(bar)
            weeks_out.append(
                {
                    "start": full_start.isoformat(),
                    "end": full_end_str.isoformat(),
                    "label": range_label,
                    "sub": sub,
                    "net": net,
                }
            )
        # Mpya kwanza
        weeks_out = list(reversed(weeks_out))

    else:  # year
        for meta in _year_months(anchor):
            if meta["net_null"]:
                bars.append({"key": meta["key"], "label": meta["label"], "net": None})
                continue
            w_start = meta["start"]
            w_end = meta["end"]
            r_list = []
            s_list = []
            d = w_start
            while d <= w_end:
                r_list.extend(by_receipt.get(d.isoformat(), []))
                s_list.extend(by_sheet.get(d.isoformat(), []))
                d += timedelta(days=1)
            stats, _ = _stats(r_list, s_list)
            net = stats["sales"] - stats["capital"] - stats["expenses"]
            for k in total:
                total[k] += stats[k]
            bars.append({"key": meta["key"], "label": meta["label"], "net": net})

    _, items = _stats(all_receipts, all_sheets)
    top, low = _top_low(items)
    unsold = await _unsold(sid, items)
    cap = await _capital_in_shop(sid)
    purch = await _purchases(sid, fetch_start, fetch_end)
    exp_grouped = _expenses_grouped(all_sheets)

    return {
        "period": period,
        "label": _period_label(period, anchor),
        "start": p_start.isoformat(),
        "end": p_end.isoformat(),
        "has_prev": True,
        "has_next": _has_next(period, anchor),
        "summary": _summary(total),
        "bars": bars,
        "top": top,
        "low": low,
        "expenses": exp_grouped,
        "receipts": [],
        "weeks": weeks_out,
        "unsold": unsold,
        "capital_in_shop": cap,
        "purchases": purch,
    }


# ── build_day ─────────────────────────────────────────────────────────────────

async def build_day(sid, day: date) -> dict:
    day_str = day.isoformat()
    receipts_docs = [
        r
        async for r in db.receipts.find(
            {"shop_id": sid, "date": day_str, "status": "paid"}
        ).sort("number", 1)
    ]
    sheet = await db.daily_sheets.find_one({"shop_id": sid, "date": day_str})
    stats, items = _stats(receipts_docs, [sheet] if sheet else [])
    top, _ = _top_low(items, n=len(items))

    receipts_out = []
    for r in receipts_docs:
        receipts_out.append(
            {
                "id": str(r["_id"]),
                "number": r["number"],
                "customer": {"name": (r.get("customer") or {}).get("name", "")},
                "time": _fmt_time(r.get("created_at")),
                "paid": int((r.get("totals") or {}).get("paid", 0)),
            }
        )

    exp_grouped = _expenses_grouped([sheet] if sheet else [])

    return {
        "period": "day",
        "label": f"{DAY_NAMES[day.weekday()]}, {day.day} {MONTH_SHORT[day.month - 1]}",
        "start": day_str,
        "end": day_str,
        "has_prev": True,
        "has_next": day + timedelta(days=1) <= today(),
        "summary": _summary(stats),
        "bars": [],
        "top": top,
        "low": [],
        "expenses": exp_grouped,
        "receipts": receipts_out,
        "weeks": [],
        "unsold": [],
        "capital_in_shop": 0,
        "purchases": 0,
    }
