"""Training programme, intake and step models."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from beanie import Document
from pymongo import IndexModel, ASCENDING, DESCENDING

from app.models.base import TranslatableStr, ImageField, SEOFields


class TrainingProgramme(Document):
    # Publishable fields
    status: str = "draft"
    sort: int = 0
    slug: str = ""
    slug_sw: str = ""
    seo: SEOFields = SEOFields()

    # Content
    title: TranslatableStr = TranslatableStr()
    cover: ImageField = ImageField()
    summary: TranslatableStr = TranslatableStr()
    audience: TranslatableStr = TranslatableStr()
    requirements: TranslatableStr = TranslatableStr()
    outline: TranslatableStr = TranslatableStr()
    duration: TranslatableStr = TranslatableStr()
    mode: str = "classroom"    # classroom | field | online | blended
    fee_tzs: int = 0           # 0 = free
    certificate: TranslatableStr = TranslatableStr()
    venue: TranslatableStr = TranslatableStr()
    is_open: bool = True

    # Audit
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None

    class Settings:
        name = "training_programmes"
        indexes = [
            IndexModel([("slug", ASCENDING)], unique=True, sparse=True),
            IndexModel([("slug_sw", ASCENDING)], sparse=True),
            IndexModel([("status", ASCENDING)]),
            IndexModel([("sort", ASCENDING)]),
        ]


class TrainingIntake(Document):
    programme_id: str = ""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    venue: TranslatableStr = TranslatableStr()
    seats: int = 0
    status: str = "open"   # open | closed | full
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Settings:
        name = "training_intakes"
        indexes = [
            IndexModel([("programme_id", ASCENDING)]),
            IndexModel([("start_date", ASCENDING)]),
        ]


class TrainingStep(Document):
    number: int = 0
    title: TranslatableStr = TranslatableStr()
    text: TranslatableStr = TranslatableStr()
    icon: str = ""

    class Settings:
        name = "training_steps"
        indexes = [IndexModel([("number", ASCENDING)])]
