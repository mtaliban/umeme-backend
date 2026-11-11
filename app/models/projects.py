"""Project model."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional, List

from beanie import Document
from pydantic import BaseModel
from pymongo import IndexModel, ASCENDING, DESCENDING

from app.models.base import TranslatableStr, ImageField, SEOFields


class BeforeAfterPair(BaseModel):
    before: ImageField = ImageField()
    after: ImageField = ImageField()
    caption: TranslatableStr = TranslatableStr()


class Project(Document):
    # Publishable fields
    status: str = "draft"
    sort: int = 0
    slug: str = ""
    slug_sw: str = ""
    seo: SEOFields = SEOFields()

    # Content
    category_id: Optional[str] = None
    title: TranslatableStr = TranslatableStr()
    client_name: str = ""
    location: str = ""
    region: str = ""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    value_tzs: Optional[int] = None
    hide_value: bool = False
    project_status: str = "ongoing"   # ongoing | completed
    summary: TranslatableStr = TranslatableStr()
    scope: TranslatableStr = TranslatableStr()
    outcome: TranslatableStr = TranslatableStr()
    cover: ImageField = ImageField()
    gallery: List[ImageField] = []
    before_after: List[BeforeAfterPair] = []
    video_url: str = ""
    is_featured: bool = False
    related_service_ids: List[str] = []

    # Audit
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None

    class Settings:
        name = "projects"
        indexes = [
            IndexModel([("slug", ASCENDING)], unique=True, sparse=True),
            IndexModel([("slug_sw", ASCENDING)], sparse=True),
            IndexModel([("status", ASCENDING)]),
            IndexModel([("sort", ASCENDING)]),
            IndexModel([("is_featured", ASCENDING)]),
            IndexModel([("category_id", ASCENDING)]),
            IndexModel([("created_at", DESCENDING)]),
        ]
