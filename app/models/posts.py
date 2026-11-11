"""News/post model."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from beanie import Document
from pymongo import IndexModel, ASCENDING, DESCENDING

from app.models.base import TranslatableStr, ImageField, SEOFields


class Post(Document):
    # Publishable fields
    status: str = "draft"
    sort: int = 0
    slug: str = ""
    slug_sw: str = ""
    seo: SEOFields = SEOFields()

    # Content
    category: str = "news"    # news | announcement | event | tender
    title: TranslatableStr = TranslatableStr()
    cover: ImageField = ImageField()
    excerpt: TranslatableStr = TranslatableStr()
    body: TranslatableStr = TranslatableStr()
    published_at: Optional[datetime] = None
    is_featured: bool = False

    # Audit
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None

    class Settings:
        name = "posts"
        indexes = [
            IndexModel([("slug", ASCENDING)], unique=True, sparse=True),
            IndexModel([("slug_sw", ASCENDING)], sparse=True),
            IndexModel([("status", ASCENDING)]),
            IndexModel([("sort", ASCENDING)]),
            IndexModel([("is_featured", ASCENDING)]),
            IndexModel([("category", ASCENDING)]),
            IndexModel([("published_at", DESCENDING)]),
        ]
