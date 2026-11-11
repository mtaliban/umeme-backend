"""Home-page content models: HeroSlide, Stat, Feature, WorkStep."""
from __future__ import annotations

from typing import Optional

from beanie import Document
from pymongo import IndexModel, ASCENDING

from app.models.base import TranslatableStr, ImageField


class HeroSlide(Document):
    image: ImageField = ImageField()
    headline: TranslatableStr = TranslatableStr()
    text: TranslatableStr = TranslatableStr()
    button1_label: TranslatableStr = TranslatableStr()
    button1_url: str = ""
    button2_label: TranslatableStr = TranslatableStr()
    button2_url: str = ""
    sort: int = 0
    is_active: bool = True

    class Settings:
        name = "hero_slides"
        indexes = [IndexModel([("sort", ASCENDING)])]


class Stat(Document):
    label: TranslatableStr = TranslatableStr()
    number: int = 0
    suffix: str = ""
    icon: str = ""
    sort: int = 0

    class Settings:
        name = "stats"
        indexes = [IndexModel([("sort", ASCENDING)])]


class Feature(Document):
    """Why Choose Us item."""
    title: TranslatableStr = TranslatableStr()
    text: TranslatableStr = TranslatableStr()
    icon: str = ""
    sort: int = 0

    class Settings:
        name = "features"
        indexes = [IndexModel([("sort", ASCENDING)])]


class WorkStep(Document):
    """How We Work step."""
    title: TranslatableStr = TranslatableStr()
    text: TranslatableStr = TranslatableStr()
    icon: str = ""
    sort: int = 0

    class Settings:
        name = "work_steps"
        indexes = [IndexModel([("sort", ASCENDING)])]
