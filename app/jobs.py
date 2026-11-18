"""Kazi za muda: kumbusho la kufunga siku na ripoti ya wiki."""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .config import settings
from .db import db
from .services import notify, reports
from .tz import TZ, today

scheduler = AsyncIOScheduler(timezone=TZ)


def _clock(value: str, default: tuple[int, int]) -> tuple[int, int]:
    try:
        hour, minute = str(value).strip().split(":")
        return int(hour), int(minute)
    except Exception:
        return default


def _weekly_time(default: tuple[int, int]) -> tuple[int, int]:
    parts = str(settings.weekly_report_time).strip().split()
    if len(parts) == 2:
        return _clock(parts[1], default)
    return default


async def remind_close_day() -> None:
    day = today().isoformat()
    async for shop in db.shops.find({}, {"_id": 1}):
        sid = shop["_id"]
        if await db.daily_sheets.find_one({"shop_id": sid, "date": day}, {"_id": 1}):
            continue
        await notify.send(
            sid,
            "close_day",
            "Funga hesabu ya leo",
            "Andika mauzo ya leo na gharama",
        )


async def weekly_report() -> None:
    for shop in [s async for s in db.shops.find({}, {"_id": 1})]:
        sid = shop["_id"]
        report = await reports.build_report(sid, "week", today())
        await notify.send(
            sid,
            "weekly_report",
            "Ripoti ya wiki",
            f"Faida halisi wiki hii: {report['summary']['net']}",
        )


def start() -> None:
    hour, minute = _clock(settings.close_day_reminder, (21, 0))
    scheduler.add_job(
        remind_close_day,
        CronTrigger(hour=hour, minute=minute, timezone=TZ),
        id="close_day",
        replace_existing=True,
    )
    hour, minute = _weekly_time((21, 30))
    scheduler.add_job(
        weekly_report,
        CronTrigger(day_of_week="sun", hour=hour, minute=minute, timezone=TZ),
        id="weekly_report",
        replace_existing=True,
    )
    if not scheduler.running:
        scheduler.start()


def stop() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
