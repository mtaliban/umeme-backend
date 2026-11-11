"""FastAPI dependencies for authentication and role-based access control."""
from __future__ import annotations

from typing import Callable

from fastapi import Depends, HTTPException, Request, status

from app.models.user import User
from app.security.jwt import get_token_from_request, verify_token

ROLES = ["super_admin", "editor", "writer", "inbox_officer"]
ROLE_RANK = {r: i for i, r in enumerate(ROLES)}


async def get_current_user(request: Request) -> User:
    """Read the JWT cookie, verify it, and return the User document."""
    token = get_token_from_request(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    user_id = payload.get("sub")
    user = await User.get(user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or deactivated",
        )
    return user


def require_role(*roles: str) -> Callable:
    """Return a FastAPI dependency that checks the user has one of *roles*."""
    async def _check(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' is not allowed. Required: {list(roles)}",
            )
        return user
    return _check


def require_min_role(min_role: str) -> Callable:
    """Return a dependency that checks user role rank >= min_role rank."""
    min_rank = ROLE_RANK[min_role]

    async def _check(user: User = Depends(get_current_user)) -> User:
        if ROLE_RANK.get(user.role, 999) > min_rank:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions",
            )
        return user
    return _check


# Convenience pre-built dependencies
require_super_admin = require_role("super_admin")
require_editor_or_above = require_role("super_admin", "editor")
require_writer_or_above = require_role("super_admin", "editor", "writer")
require_inbox_or_above = require_role("super_admin", "editor", "inbox_officer")
require_any_role = require_role("super_admin", "editor", "writer", "inbox_officer")
