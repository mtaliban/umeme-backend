"""Gallery album model."""
from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from beanie import Document
from pydantic import BaseModel
from pymongo import IndexModel, ASCENDING

from app.models.base import TranslatableStr, ImageField, SEOFields


class GalleryItem(BaseModel):
    type: str = "photo"   # photo | video
    image: ImageField = ImageField()
    video_url: str = ""
    caption: TranslatableStr = TranslatableStr()


class GalleryAlbum(Document):
    # Publishable fields
    status: str = "draft"
    sort: int = 0
    slug: str = ""
    slug_sw: str = ""
    seo: SEOFields = SEOFields()

    # Content
    title: TranslatableStr = TranslatableStr()
    category: str = "projects"   # projects | training | events | team
    cover: ImageField = ImageField()
    items: List[GalleryItem] = []

    # Audit
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None

    class Settings:
        name = "gallery_albums"
        indexes = [
            IndexModel([("slug", ASCENDING)], unique=True, sparse=True),
            IndexModel([("slug_sw", ASCENDING)], sparse=True),
            IndexModel([("status", ASCENDING)]),
            IndexModel([("sort", ASCENDING)]),
            IndexModel([("category", ASCENDING)]),
        ]
