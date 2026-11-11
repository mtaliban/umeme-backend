"""User document model."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from beanie import Document
from pydantic import Field
from pymongo import IndexModel, ASCENDING


class User(Document):
    name: str
    email: str
    password_hash: str
    role: str = "writer"  # super_admin | editor | writer | inbox_officer
    is_active: bool = True
    failed_logins: int = 0
    locked_until: Optional[datetime] = None
    last_login: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Settings:
        name = "users"
        indexes = [
            IndexModel([("email", ASCENDING)], unique=True),
        ]
