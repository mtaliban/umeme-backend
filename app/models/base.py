"""Shared Pydantic types used by all models."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TranslatableStr(BaseModel):
    en: str = ""
    sw: str = ""

    def resolve(self, lang: str = "en") -> str:
        """Return the requested language, falling back to English."""
        if lang == "sw":
            return self.sw if self.sw else self.en
        return self.en


class ImageSizes(BaseModel):
    sm: str = ""
    md: str = ""
    lg: str = ""


class ImageField(BaseModel):
    url: str = ""
    alt: TranslatableStr = TranslatableStr()
    width: int = 0
    height: int = 0
    sizes: ImageSizes = ImageSizes()


class SEOFields(BaseModel):
    meta_title: TranslatableStr = TranslatableStr()
    meta_description: TranslatableStr = TranslatableStr()
    share_image: Optional[ImageField] = None


class CommonFieldsMixin(BaseModel):
    """Fields present on every content document."""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None


class PublishableMixin(CommonFieldsMixin):
    """Extra fields on publishable content documents."""
    status: str = "draft"          # "draft" | "published"
    sort: int = 0
    slug: str = ""
    slug_sw: str = ""
    seo: SEOFields = SEOFields()
