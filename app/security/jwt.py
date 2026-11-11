"""JWT creation, verification and httpOnly cookie helpers."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Response, Request
from fastapi.responses import JSONResponse

from app.config import settings

COOKIE_NAME = "access_token"
TOKEN_EXPIRY_HOURS = 8
ALGORITHM = "HS256"


def create_token(user_id: str, role: str) -> str:
    """Create a signed JWT for the given user."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "role": role,
        "iat": now,
        "exp": now + timedelta(hours=TOKEN_EXPIRY_HOURS),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def verify_token(token: str) -> Optional[dict]:
    """Verify and decode *token*. Returns the payload dict or None on failure."""
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None


def _is_secure() -> bool:
    return settings.site_url.startswith("https://")


def set_cookie(response: Response, token: str) -> None:
    """Attach the JWT as an httpOnly cookie to *response*."""
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=_is_secure(),
        max_age=TOKEN_EXPIRY_HOURS * 3600,
        path="/",
    )


def clear_cookie(response: Response) -> None:
    """Remove the auth cookie from *response*."""
    response.delete_cookie(
        key=COOKIE_NAME,
        httponly=True,
        samesite="lax",
        secure=_is_secure(),
        path="/",
    )


def get_token_from_request(request: Request) -> Optional[str]:
    """Extract the JWT string from the request's cookies."""
    return request.cookies.get(COOKIE_NAME)
