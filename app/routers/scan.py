"""Picha ya daftari → mauzo ya siku (sehemu 3)."""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from ..auth import current_shop_id
from ..config import settings
from ..services import notebook
from ..services import summary as summary_service
from ..tz import parse_day, today
from .daily import create_expense, create_line, daily_payload

router = APIRouter(tags=["scan"])

ALLOWED_TYPES = {"image/jpeg", "image/jpg", "image/pjpeg", "image/png"}


async def _scan_seen(sid, day_str: str, key: str) -> bool:
    """Picha ile ile (client_id ile) isiingize mara mbili."""
    doc = await summary_service.sheet(sid, day_str)
    if not doc:
        return False
    rows = list(doc.get("lines") or []) + list(doc.get("expenses") or [])
    return any(row.get("scan_id") == key for row in rows)


@router.post("/daily/{date}/scan")
async def scan_day(
    date: str,
    image: UploadFile | None = File(None),
    client_id: str | None = Form(None),
    sid=Depends(current_shop_id),
):
    day = parse_day(date)
    if day > today():
        raise HTTPException(400, "Huwezi kuandika siku ijayo")
    day_str = day.isoformat()

    key = (client_id or "").strip()[:32] or None
    if key and await _scan_seen(sid, day_str, key):
        return await daily_payload(sid, day_str)

    doc = await summary_service.sheet(sid, day_str)
    if doc and doc.get("saved_at"):
        raise HTTPException(409, "Siku imehifadhiwa — bonyeza Hariri kwanza")

    if image is None:
        raise HTTPException(422, "Picha si sahihi")
    if (image.content_type or "").lower() not in ALLOWED_TYPES:
        raise HTTPException(422, "Picha si sahihi")

    data = await image.read()
    if not data or len(data) > settings.scan_max_mb * 1024 * 1024:
        raise HTTPException(422, "Picha si sahihi")

    # Punguza picha (hadi 1600 px, JPEG 85) kabla ya kuituma kwa AI.
    shrunk = notebook.shrink_image(data)

    stock = await notebook.stock_names(sid)
    raw = await notebook.read_notebook(shrunk, [item["name"] for item in stock])
    cleaned = notebook.normalize(raw, stock)

    if not cleaned["lines"] and not cleaned["expenses"]:
        # AI haikusoma chochote halali — hakuna kinachoingizwa.
        raise HTTPException(422, "Haikusomeka — piga picha tena")

    # Misingi ile ile ya kuongeza mauzo/gharama (kodi moja na ya mkono).
    for line in cleaned["lines"]:
        try:
            await create_line(
                sid,
                day_str,
                qty=line["qty"],
                selling=line["selling"],
                buying=line["buying"],
                name=line["name"],
                variant_id=line["variant_id"],
                scan_id=key,
            )
        except HTTPException:
            if not line["variant_id"]:
                raise
            # Aina ilifutwa katikati — ingia kama bidhaa isiyo kwenye orodha.
            await create_line(
                sid,
                day_str,
                qty=line["qty"],
                selling=line["selling"],
                buying=line["buying"],
                name=line["name"],
                variant_id=None,
                scan_id=key,
            )

    for expense in cleaned["expenses"]:
        await create_expense(
            sid,
            day_str,
            name=expense["name"],
            amount=expense["amount"],
            scan_id=key,
        )

    return await daily_payload(sid, day_str)
