"""Nyumbani: siku ya mwisho yenye data."""

from fastapi import APIRouter, Depends

from ..auth import current_shop_id
from ..db import db
from ..services import summary as summary_service

router = APIRouter(tags=["home"])


@router.get("/home")
async def home(sid=Depends(current_shop_id)):
    day = await summary_service.last_day_with_data(sid)
    if day is None:
        return {"day": None, "summary": None, "top": [], "expenses": []}

    summary = await summary_service.day_summary(sid, day)
    top = await summary_service.sold_items_home(sid, day)

    sheet = await db.daily_sheets.find_one({"shop_id": sid, "date": day}) or {}
    expenses = [
        {"name": e["name"], "amount": int(e.get("amount", 0))}
        for e in (sheet.get("expenses") or [])
    ]

    return {
        "day": day,
        "summary": summary,
        "top": top,
        "expenses": expenses,
    }
