"""Authentication endpoints."""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr

from app.models.activity import Activity
from app.models.user import User
from app.security.jwt import create_token, set_cookie, clear_cookie
from app.security.passwords import hash_password, verify_password, MIN_PASSWORD_LENGTH
from app.security.permissions import get_current_user
from app.security.rate_limit import limiter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])

LOCKOUT_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


class LoginRequest(BaseModel):
    email: str
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


async def _log_activity(user: User, action: str) -> None:
    now = datetime.now(timezone.utc)
    await Activity(
        user_id=str(user.id),
        user_name=user.name,
        action=action,
        collection="users",
        item_id=str(user.id),
        item_label=user.email,
        at=now,
    ).insert()


@router.post("/login")
@limiter.limit("10/minute")
async def login(
    request: Request,
    body: LoginRequest,
    response: Response,
) -> dict:
    now = datetime.now(timezone.utc)
    user = await User.find_one(User.email == body.email)

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    # Check lockout
    if user.locked_until and user.locked_until > now:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Account locked until {user.locked_until.isoformat()}",
        )

    if not verify_password(body.password, user.password_hash):
        user.failed_logins = (user.failed_logins or 0) + 1
        if user.failed_logins >= LOCKOUT_ATTEMPTS:
            user.locked_until = now + timedelta(minutes=LOCKOUT_MINUTES)
            user.failed_logins = 0
        await user.save()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    # Successful login
    user.failed_logins = 0
    user.locked_until = None
    user.last_login = now
    await user.save()

    token = create_token(str(user.id), user.role)
    set_cookie(response, token)

    await _log_activity(user, "login")
    return {"ok": True}


@router.post("/logout")
async def logout(response: Response) -> dict:
    clear_cookie(response)
    return {"ok": True}


@router.get("/me")
async def me(user: User = Depends(get_current_user)) -> dict:
    return {
        "id": str(user.id),
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
        "last_login": user.last_login.isoformat() if user.last_login else None,
    }


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    user: User = Depends(get_current_user),
) -> dict:
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    if len(body.new_password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"New password must be at least {MIN_PASSWORD_LENGTH} characters",
        )
    user.password_hash = hash_password(body.new_password)
    user.updated_at = datetime.now(timezone.utc)
    await user.save()
    return {"ok": True}
