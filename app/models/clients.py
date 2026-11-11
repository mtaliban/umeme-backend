"""Client and testimonial models."""
from __future__ import annotations

from typing import Optional

from beanie import Document
from pymongo import IndexModel, ASCENDING

from app.models.base import TranslatableStr, ImageField


class Client(Document):
    name: str = ""
    logo: ImageField = ImageField()
    type: str = "private"   # government | private | ngo
    url: str = ""
    is_featured: bool = False
    sort: int = 0

    class Settings:
        name = "clients"
        indexes = [
            IndexModel([("sort", ASCENDING)]),
            IndexModel([("is_featured", ASCENDING)]),
        ]


class Testimonial(Document):
    name: str = ""
    position: TranslatableStr = TranslatableStr()
    organisation: str = ""
    photo: ImageField = ImageField()
    quote: TranslatableStr = TranslatableStr()
    rating: int = 5    # 1-5
    sort: int = 0
    is_active: bool = True

    class Settings:
        name = "testimonials"
        indexes = [IndexModel([("sort", ASCENDING)])]
