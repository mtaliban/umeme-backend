"""Tarehe na saa — Africa/Dar_es_Salaam (UTC+3)."""

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from .config import settings

TZ = ZoneInfo(settings.tz_name)

DAY_NAMES = [
    "Jumatatu",
    "Jumanne",
    "Jumatano",
    "Alhamisi",
    "Ijumaa",
    "Jumamosi",
    "Jumapili",
]
DAY_SHORT = ["Jtt", "Jne", "Jtn", "Alh", "Iju", "Jmo", "Jpi"]

MONTH_NAMES = [
    "Januari",
    "Februari",
    "Machi",
    "Aprili",
    "Mei",
    "Juni",
    "Julai",
    "Agosti",
    "Septemba",
    "Oktoba",
    "Novemba",
    "Desemba",
]
MONTH_SHORT = ["Jan", "Feb", "Mac", "Apr", "Mei", "Jun", "Jul", "Ago", "Sep", "Okt", "Nov", "Des"]


def now() -> datetime:
    """Sasa kwa UTC (inahifadhiwa hivi kwenye MongoDB)."""
    return datetime.now(timezone.utc)


def local_now() -> datetime:
    return datetime.now(TZ)


def today() -> date:
    return local_now().date()


def today_str() -> str:
    return today().isoformat()


def day_start(d: date) -> datetime:
    return datetime.combine(d, datetime.min.time(), tzinfo=TZ)


def parse_day(value: str | None) -> date:
    if not value:
        return today()
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        raise HTTPException(400, "Tarehe si sahihi: tumia YYYY-MM-DD")


def month_end(year: int, month: int) -> date:
    if month == 12:
        nxt = date(year + 1, 1, 1)
    else:
        nxt = date(year, month + 1, 1)
    return nxt - timedelta(days=1)
