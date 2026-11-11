"""Misc models: FAQ, Office, Download, Settings."""
from __future__ import annotations

from typing import Optional, List

from beanie import Document
from pydantic import BaseModel
from pymongo import IndexModel, ASCENDING

from app.models.base import TranslatableStr, ImageField, SEOFields


class FAQ(Document):
    category: str = "general"   # general | electricity | water | training
    question: TranslatableStr = TranslatableStr()
    answer: TranslatableStr = TranslatableStr()
    sort: int = 0
    is_active: bool = True

    class Settings:
        name = "faqs"
        indexes = [
            IndexModel([("category", ASCENDING)]),
            IndexModel([("sort", ASCENDING)]),
        ]


class Office(Document):
    name: TranslatableStr = TranslatableStr()
    address: TranslatableStr = TranslatableStr()
    phone: str = ""
    email: str = ""
    hours: TranslatableStr = TranslatableStr()
    lat: Optional[float] = None
    lng: Optional[float] = None
    is_head_office: bool = False
    sort: int = 0

    class Settings:
        name = "offices"
        indexes = [IndexModel([("sort", ASCENDING)])]


class Download(Document):
    title: TranslatableStr = TranslatableStr()
    file: str = ""
    category: str = ""
    sort: int = 0

    class Settings:
        name = "downloads"
        indexes = [IndexModel([("sort", ASCENDING)])]


# ---- Site settings (single document) ----

class SocialLinks(BaseModel):
    facebook: str = ""
    instagram: str = ""
    x: str = ""
    linkedin: str = ""
    youtube: str = ""
    tiktok: str = ""


class HomeSection(BaseModel):
    key: str
    enabled: bool = True
    sort: int = 0


class CTABlock(BaseModel):
    title: TranslatableStr = TranslatableStr()
    text: TranslatableStr = TranslatableStr()
    button_label: TranslatableStr = TranslatableStr()
    button_url: str = ""


class SiteSettings(Document):
    company_name: str = ""
    slogan: TranslatableStr = TranslatableStr()
    logo: ImageField = ImageField()
    logo_dark: ImageField = ImageField()
    favicon: ImageField = ImageField()
    phones: List[str] = []
    emails: List[str] = []
    whatsapp_number: str = ""
    working_hours: TranslatableStr = TranslatableStr()
    address: TranslatableStr = TranslatableStr()
    social: SocialLinks = SocialLinks()
    footer_text: TranslatableStr = TranslatableStr()
    default_seo: SEOFields = SEOFields()
    google_analytics_id: str = ""
    notify_emails: List[str] = []
    home_sections: List[HomeSection] = []
    cta: CTABlock = CTABlock()

    class Settings:
        name = "settings"
