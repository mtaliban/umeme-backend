"""Majina ya gharama yaliyotumika."""

from datetime import timedelta

from fastapi import APIRouter, Depends

from ..auth import current_shop_id
from ..db import db
from ..tz import today

COMMON_EXPENSES = [
    "Usafirishaji",
    "Bando",
    "Umeme",
    "Maji",
    "Kodi",
    "Chakula",
    "Mafuta",
    "Ukarabati",
    "Mshahara",
    "Vifaa",
]

router = APIRouter(tags=["expenses"])


@router.get("/expenses/names")
async def expense_names(sid=Depends(current_shop_id)):
    since = (today() - timedelta(days=60)).isoformat()
    pipeline = [
        {"$match": {"shop_id": sid, "date": {"$gte": since}}},
        {"$unwind": "$expenses"},
        {"$group": {"_id": "$expenses.name", "n": {"$sum": 1}}},
        {"$sort": {"n": -1, "_id": 1}},
        {"$limit": 10},
    ]
    recent: list[str] = []
    async for doc in db.daily_sheets.aggregate(pipeline):
        name = str(doc.get("_id") or "").strip()
        if name and name not in recent:
            recent.append(name)
    return recent + [name for name in COMMON_EXPENSES if name not in recent]
