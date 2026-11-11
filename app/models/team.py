"""Team member and certification models."""
from __future__ import annotations

from typing import Optional

from beanie import Document
from pymongo import IndexModel, ASCENDING

from app.models.base import TranslatableStr, ImageField


class TeamMember(Document):
    name: str = ""
    position: TranslatableStr = TranslatableStr()
    bio: TranslatableStr = TranslatableStr()
    photo: ImageField = ImageField()
    sort: int = 0
    is_active: bool = True

    class Settings:
        name = "team_members"
        indexes = [IndexModel([("sort", ASCENDING)])]


class Certification(Document):
    name: TranslatableStr = TranslatableStr()
    issuer: str = ""
    number: str = ""
    logo: ImageField = ImageField()
    pdf: str = ""
    sort: int = 0

    class Settings:
        name = "certifications"
        indexes = [IndexModel([("sort", ASCENDING)])]
