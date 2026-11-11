"""Super Admin bootstrap — creates the first user if none exist."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.config import settings
from app.models.user import User
from app.security.passwords import hash_password, MIN_PASSWORD_LENGTH

logger = logging.getLogger(__name__)


async def ensure_super_admin() -> None:
    """If no users exist in the DB, create a Super Admin from settings."""
    count = await User.count()
    if count > 0:
        return

    password = settings.admin_password
    if len(password) < MIN_PASSWORD_LENGTH:
        logger.error(
            "ADMIN_PASSWORD is shorter than %d characters. "
            "Super Admin will NOT be created.",
            MIN_PASSWORD_LENGTH,
        )
        return

    now = datetime.now(timezone.utc)
    user = User(
        name="Super Admin",
        email=settings.admin_email,
        password_hash=hash_password(password),
        role="super_admin",
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    await user.insert()
    logger.info("Super Admin created: %s", settings.admin_email)
