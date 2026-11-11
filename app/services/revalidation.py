"""Next.js on-demand revalidation helper."""
from __future__ import annotations

import logging
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def revalidate(paths: list[str]) -> None:
    """POST to the Next.js revalidation endpoint.  Errors are ignored."""
    if not settings.revalidate_secret:
        return

    internal_url = settings.frontend_url
    url = f"{internal_url}/api/revalidate"

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                url,
                json={"paths": paths},
                headers={"x-revalidate-secret": settings.revalidate_secret},
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Revalidation failed for %s: %s", paths, exc)
