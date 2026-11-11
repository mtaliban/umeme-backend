"""Service category and service models."""
from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from beanie import Document
from pydantic import BaseModel
from pymongo import IndexModel, ASCENDING

from app.models.base import TranslatableStr, ImageField, SEOFields, CommonFieldsMixin


class ServiceCategory(Document):
    name: TranslatableStr = TranslatableStr()
    slug: str = ""
    icon: str = ""
    colour: str = ""
    sort: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Settings:
        name = "service_categories"
        indexes = [
            IndexModel([("slug", ASCENDING)], unique=True),
            IndexModel([("sort", ASCENDING)]),
        ]


class ServiceFAQ(BaseModel):
    q: TranslatableStr = TranslatableStr()
    a: TranslatableStr = TranslatableStr()


class Service(Document):
    # Publishable fields
    status: str = "draft"
    sort: int = 0
    slug: str = ""
    slug_sw: str = ""
    seo: SEOFields = SEOFields()

    # Content
    category_id: Optional[str] = None
    title: TranslatableStr = TranslatableStr()
    icon: str = ""
    cover: ImageField = ImageField()
    summary: TranslatableStr = TranslatableStr()
    body: TranslatableStr = TranslatableStr()
    included: List[TranslatableStr] = []
    gallery: List[ImageField] = []
    faqs: List[ServiceFAQ] = []
    is_featured: bool = False

    # Audit
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None

    class Settings:
        name = "services"
        indexes = [
            IndexModel([("slug", ASCENDING)], unique=True, sparse=True),
            IndexModel([("slug_sw", ASCENDING)], sparse=True),
            IndexModel([("status", ASCENDING)]),
            IndexModel([("sort", ASCENDING)]),
            IndexModel([("is_featured", ASCENDING)]),
            IndexModel([("category_id", ASCENDING)]),
        ]
