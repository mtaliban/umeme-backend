"""Page document model."""
from __future__ import annotations

from typing import Optional, List

from beanie import Document
from pydantic import BaseModel
from pymongo import IndexModel, ASCENDING

from app.models.base import TranslatableStr, ImageField, SEOFields


class PageValue(BaseModel):
    """A value item on the About page."""
    title: TranslatableStr = TranslatableStr()
    text: TranslatableStr = TranslatableStr()
    icon: str = ""


class Page(Document):
    key: str  # about | privacy | services | projects | training | clients | news | gallery | faq | contact
    title: TranslatableStr = TranslatableStr()
    intro: TranslatableStr = TranslatableStr()
    body: TranslatableStr = TranslatableStr()      # HTML
    banner: ImageField = ImageField()
    seo: SEOFields = SEOFields()

    # About-specific fields
    vision: TranslatableStr = TranslatableStr()
    mission: TranslatableStr = TranslatableStr()
    values: List[PageValue] = []
    hse_statement: TranslatableStr = TranslatableStr()
    story_image: ImageField = ImageField()
    profile_pdf: str = ""

    class Settings:
        name = "pages"
        indexes = [IndexModel([("key", ASCENDING)], unique=True)]
