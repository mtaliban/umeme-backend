"""Image and PDF upload processing."""
from __future__ import annotations

import io
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, UploadFile
from PIL import Image as PilImage

from app.config import settings
from app.models.base import ImageField, ImageSizes, TranslatableStr

logger = logging.getLogger(__name__)

MEDIA_ROOT = Path("/media")

# Magic bytes for supported types
MAGIC = {
    "jpg": b"\xff\xd8\xff",
    "png": b"\x89PNG",
    "webp": b"RIFF",   # first 4 bytes; bytes 8-11 are "WEBP"
    "pdf": b"%PDF",
}

WIDTHS = {"sm": 480, "md": 960, "lg": 1600}


def _check_magic(data: bytes, allowed: list[str]) -> str:
    """Return the detected file type or raise HTTPException."""
    for fmt in allowed:
        magic = MAGIC[fmt]
        if data[: len(magic)] == magic:
            # Extra check for WebP: bytes 8-11 must be b"WEBP"
            if fmt == "webp" and data[8:12] != b"WEBP":
                continue
            return fmt
    raise HTTPException(
        status_code=400,
        detail=f"Unsupported file type. Allowed: {allowed}",
    )


async def save_upload(
    file: UploadFile,
    folder: str = "",
    alt: Optional[TranslatableStr] = None,
) -> ImageField:
    """Verify, convert to WebP at three sizes and store under /media/{year}/{month}/."""
    max_bytes = settings.max_upload_mb * 1024 * 1024
    data = await file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum {settings.max_upload_mb} MB.",
        )

    _check_magic(data, ["jpg", "png", "webp"])

    now = datetime.utcnow()
    year, month = now.strftime("%Y"), now.strftime("%m")
    base_folder = folder if folder else f"{year}/{month}"
    dest_dir = MEDIA_ROOT / base_folder
    dest_dir.mkdir(parents=True, exist_ok=True)

    stem = uuid.uuid4().hex
    urls: dict[str, str] = {}
    original_width = original_height = 0

    img = PilImage.open(io.BytesIO(data))
    img = img.convert("RGBA")
    original_width, original_height = img.size

    # Save each size
    for size_name, target_width in WIDTHS.items():
        if img.width > target_width:
            ratio = target_width / img.width
            new_height = int(img.height * ratio)
            resized = img.resize((target_width, new_height), PilImage.LANCZOS)
        else:
            resized = img.copy()

        # Convert to RGB for WebP (no alpha needed for most web use)
        rgb = PilImage.new("RGB", resized.size, (255, 255, 255))
        rgb.paste(resized, mask=resized.split()[3] if resized.mode == "RGBA" else None)

        fname = f"{stem}-{size_name}.webp"
        dest_path = dest_dir / fname
        rgb.save(str(dest_path), "WEBP", quality=85)
        urls[size_name] = f"/media/{base_folder}/{fname}"

    # Also save the "lg" as the canonical url
    canonical_url = urls["lg"]

    return ImageField(
        url=canonical_url,
        alt=alt or TranslatableStr(),
        width=min(original_width, WIDTHS["lg"]),
        height=original_height,
        sizes=ImageSizes(sm=urls["sm"], md=urls["md"], lg=urls["lg"]),
    )


async def save_pdf(file: UploadFile, folder: str = "documents") -> str:
    """Verify PDF magic bytes and store under /media/{folder}/{uuid}.pdf."""
    max_bytes = settings.max_upload_mb * 1024 * 1024
    data = await file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum {settings.max_upload_mb} MB.",
        )

    _check_magic(data, ["pdf"])

    dest_dir = MEDIA_ROOT / folder
    dest_dir.mkdir(parents=True, exist_ok=True)

    fname = f"{uuid.uuid4().hex}.pdf"
    dest_path = dest_dir / fname
    dest_path.write_bytes(data)
    return f"/media/{folder}/{fname}"


async def save_private_image(file: UploadFile) -> str:
    """Save form photo to private (non-public) location."""
    img_field = await save_upload(file, folder="private")
    return img_field.url


async def save_private_pdf(file: UploadFile) -> str:
    """Save form CV/attachment to private location."""
    return await save_pdf(file, folder="private")
