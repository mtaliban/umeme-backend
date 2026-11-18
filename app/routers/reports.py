"""Ripoti: wiki, mwezi, mwaka na siku."""

from fastapi import APIRouter, Depends

from ..auth import current_shop_id
from ..services import reports as reports_service
from ..tz import parse_day

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/week")
async def report_week(date: str | None = None, sid=Depends(current_shop_id)):
    return await reports_service.build_report(sid, "week", parse_day(date))


@router.get("/month")
async def report_month(date: str | None = None, sid=Depends(current_shop_id)):
    return await reports_service.build_report(sid, "month", parse_day(date))


@router.get("/year")
async def report_year(date: str | None = None, sid=Depends(current_shop_id)):
    return await reports_service.build_report(sid, "year", parse_day(date))


@router.get("/day/{date}")
async def report_day(date: str, sid=Depends(current_shop_id)):
    return await reports_service.build_day(sid, parse_day(date))
