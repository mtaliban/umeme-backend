"""Inbox / form submission models."""
from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from beanie import Document
from pydantic import BaseModel
from pymongo import IndexModel, ASCENDING, DESCENDING


class InboxNote(BaseModel):
    text: str = ""
    by: str = ""
    at: Optional[datetime] = None


class ServiceRequest(Document):
    name: str = ""
    phone: str = ""
    email: str = ""
    organisation: str = ""
    service_id: str = ""
    region: str = ""
    district: str = ""
    address: str = ""
    description: str = ""
    contact_method: str = "phone"   # phone | whatsapp | email
    photo: str = ""                 # /media/private/...
    status: str = "new"             # new | contacted | quoted | won | lost
    notes: List[InboxNote] = []
    consent: bool = False
    ip: str = ""
    created_at: Optional[datetime] = None

    class Settings:
        name = "service_requests"
        indexes = [
            IndexModel([("status", ASCENDING)]),
            IndexModel([("created_at", DESCENDING)]),
        ]


class TrainingApplication(Document):
    name: str = ""
    phone: str = ""
    email: str = ""
    gender: str = ""
    region: str = ""
    education_level: str = ""
    programme_id: str = ""
    intake_id: str = ""
    cv: str = ""                    # /media/private/...
    status: str = "new"             # new | shortlisted | accepted | rejected
    notes: List[InboxNote] = []
    consent: bool = False
    ip: str = ""
    created_at: Optional[datetime] = None

    class Settings:
        name = "training_applications"
        indexes = [
            IndexModel([("status", ASCENDING)]),
            IndexModel([("created_at", DESCENDING)]),
        ]


class ContactMessage(Document):
    name: str = ""
    phone: str = ""
    email: str = ""
    subject: str = ""
    message: str = ""
    status: str = "new"   # new | read | replied
    notes: List[InboxNote] = []
    consent: bool = False
    ip: str = ""
    created_at: Optional[datetime] = None

    class Settings:
        name = "contact_messages"
        indexes = [
            IndexModel([("status", ASCENDING)]),
            IndexModel([("created_at", DESCENDING)]),
        ]
