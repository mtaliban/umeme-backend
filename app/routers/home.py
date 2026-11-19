"""Nyumbani: siku ya mwisho iliyohifadhiwa."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends

from ..auth import current_shop_id
from ..db import db
from ..services import summary as summary_service
from ..tz import DAY_NAMES, MONTH_SHORT, TZ, today

router = APIRouter(tags=["home"])


def _day_label(d: date) -> str:
    return f"{DAY_NAMES[d.weekday()]}, {d.day} {MONTH_SHORT[d.month - 1]}"


def _banner_label(d: date) -> str:
    t = today()
    if d == t:
        return "MAUZO YA LEO (YAMEHIFADHIWA)"
    if d == t - timedelta(days=1):
        return "MAUZO YA JANA"
    return f"MAUZO YA {DAY_NAMES[d.weekday()].upper()} {d.day} {MONTH_SHORT[d.month - 1].upper()}"


@router.get("/home")
async def home(sid=Depends(current_shop_id)):
    last_sheet = await summary_service.last_saved_day(sid)
    if not last_sheet:
        return {"day": None}

    day_str = last_sheet["date"]
    d = date.fromisoformat(day_str)

    summary = await summary_service.day_summary(sid, day_str)
    top = await summary_service.sold_items_home(sid, day_str)

    # Gharama — orodha rahisi
    expenses = [
        {"name": e["name"], "amount": int(e.get("amount", 0))}
        for e in (last_sheet.get("expenses") or [])
    ]

    # Risiti za siku hiyo
    receipts = []
    async for r in db.receipts.find(
        {"shop_id": sid, "date": day_str, "status": "paid"},
        {"_id": 1, "number": 1, "customer": 1, "created_at": 1, "totals": 1},
    ).sort("number", -1):
        receipts.append(
            {
                "id": str(r["_id"]),
                "number": r["number"],
                "customer": {"name": (r.get("customer") or {}).get("name", "")},
                "time": _fmt_time(r.get("created_at")),
                "paid": int((r.get("totals") or {}).get("paid", 0)),
            }
        )

    return {
        "day": day_str,
        "label": _banner_label(d),
        "day_label": _day_label(d),
        "summary": summary,
        "top": top,
        "expenses": expenses,
        "receipts": receipts,
    }


def _fmt_time(dt) -> str:
    if not dt:
        return ""
    try:
        return dt.astimezone(TZ).strftime("%H:%M")
    except Exception:
        return ""
