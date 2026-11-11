"""Activity log document model."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from beanie import Document
from pymongo import IndexModel, ASCENDING, DESCENDING


class Activity(Document):
    user_id: str
    user_name: str
    action: str   # create | update | delete | publish | unpublish | login
    collection: str
    item_id: Optional[str] = None
    item_label: Optional[str] = None
    at: datetime

    class Settings:
        name = "activity_log"
        indexes = [
            IndexModel([("at", DESCENDING)]),
            IndexModel([("user_id", ASCENDING)]),
        ]
