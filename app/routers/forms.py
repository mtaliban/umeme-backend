"""Visitor form submission endpoints."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Request, UploadFile, status
from pydantic import BaseModel

from app.config import settings
from app.models.inbox import ContactMessage, ServiceRequest, TrainingApplication
from app.security.rate_limit import limiter
from app.services.email import send_notification
from app.services.images import save_upload
from app.services.images import save_pdf as _save_pdf

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/forms", tags=["forms"])

PHONE_RE = re.compile(r"^(\+2557|07|2557|\+2556|06|2556)\d{8}$")


def _normalize_phone(raw: str) -> str:
    """Normalize Tanzanian phone numbers to +255XXXXXXXXX."""
    digits = re.sub(r"\s+|-", "", raw)
    if digits.startswith("07") or digits.startswith("06"):
        return "+255" + digits[1:]
    if digits.startswith("2557") or digits.startswith("2556"):
        return "+" + digits
    return digits  # already normalized or unknown format


def _validate_phone(raw: str) -> str:
    normalized = _normalize_phone(raw)
    if not re.match(r"^\+255[67]\d{8}$", normalized):
        raise HTTPException(
            status_code=422,
            detail="Invalid Tanzanian phone number. Use formats like 07XXXXXXXX or +2557XXXXXXXX",
        )
    return normalized


async def _verify_recaptcha(token: str) -> None:
    if not settings.recaptcha_secret:
        return
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                "https://www.google.com/recaptcha/api/siteverify",
                data={"secret": settings.recaptcha_secret, "response": token},
            )
            data = resp.json()
            if not data.get("success"):
                raise HTTPException(status_code=400, detail="reCAPTCHA verification failed")
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("reCAPTCHA check failed: %s", exc)


def _get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/service-request")
@limiter.limit("5/minute;20/day")
async def submit_service_request(
    request: Request,
    background_tasks: BackgroundTasks,
    name: str = Form(...),
    phone: str = Form(...),
    email: str = Form(""),
    organisation: str = Form(""),
    service_id: str = Form(""),
    region: str = Form(...),
    district: str = Form(""),
    address: str = Form(""),
    description: str = Form(...),
    contact_method: str = Form("phone"),
    consent: bool = Form(...),
    website: str = Form(""),          # honeypot
    recaptcha_token: str = Form(""),
    photo: Optional[UploadFile] = File(None),
) -> dict:
    if website:
        return {"ok": True}  # silently reject honeypot
    if not consent:
        raise HTTPException(status_code=422, detail="Consent is required")
    await _verify_recaptcha(recaptcha_token)

    phone = _validate_phone(phone)
    photo_url = ""
    if photo and photo.filename:
        img = await save_upload(photo, folder="private")
        photo_url = img.url

    doc = ServiceRequest(
        name=name,
        phone=phone,
        email=email,
        organisation=organisation,
        service_id=service_id,
        region=region,
        district=district,
        address=address,
        description=description,
        contact_method=contact_method,
        photo=photo_url,
        consent=consent,
        ip=_get_client_ip(request),
        created_at=datetime.now(timezone.utc),
    )
    await doc.insert()

    background_tasks.add_task(
        send_notification,
        f"New Service Request from {name}",
        f"Name: {name}\nPhone: {phone}\nEmail: {email}\nRegion: {region}\nDescription: {description}",
    )
    return {"ok": True}


@router.post("/training-application")
@limiter.limit("5/minute;20/day")
async def submit_training_application(
    request: Request,
    background_tasks: BackgroundTasks,
    name: str = Form(...),
    phone: str = Form(...),
    email: str = Form(""),
    gender: str = Form(""),
    region: str = Form(""),
    education_level: str = Form(""),
    programme_id: str = Form(...),
    intake_id: str = Form(""),
    consent: bool = Form(...),
    website: str = Form(""),          # honeypot
    recaptcha_token: str = Form(""),
    cv: Optional[UploadFile] = File(None),
) -> dict:
    if website:
        return {"ok": True}
    if not consent:
        raise HTTPException(status_code=422, detail="Consent is required")
    await _verify_recaptcha(recaptcha_token)

    phone = _validate_phone(phone)
    cv_url = ""
    if cv and cv.filename:
        cv_url = await _save_pdf(cv, folder="private")

    doc = TrainingApplication(
        name=name,
        phone=phone,
        email=email,
        gender=gender,
        region=region,
        education_level=education_level,
        programme_id=programme_id,
        intake_id=intake_id,
        cv=cv_url,
        consent=consent,
        ip=_get_client_ip(request),
        created_at=datetime.now(timezone.utc),
    )
    await doc.insert()

    background_tasks.add_task(
        send_notification,
        f"New Training Application from {name}",
        f"Name: {name}\nPhone: {phone}\nEmail: {email}\nProgramme ID: {programme_id}",
    )
    return {"ok": True}


class ContactForm(BaseModel):
    name: str
    phone: str
    email: str = ""
    subject: str
    message: str
    consent: bool
    website: str = ""       # honeypot
    recaptcha_token: str = ""


@router.post("/contact")
@limiter.limit("5/minute;20/day")
async def submit_contact(
    request: Request,
    background_tasks: BackgroundTasks,
    body: ContactForm,
) -> dict:
    if body.website:
        return {"ok": True}
    if not body.consent:
        raise HTTPException(status_code=422, detail="Consent is required")
    await _verify_recaptcha(body.recaptcha_token)

    phone = _validate_phone(body.phone)

    doc = ContactMessage(
        name=body.name,
        phone=phone,
        email=body.email,
        subject=body.subject,
        message=body.message,
        consent=body.consent,
        ip=_get_client_ip(request),
        created_at=datetime.now(timezone.utc),
    )
    await doc.insert()

    background_tasks.add_task(
        send_notification,
        f"New Contact Message from {body.name}: {body.subject}",
        f"Name: {body.name}\nPhone: {phone}\nEmail: {body.email}\nMessage: {body.message}",
    )
    return {"ok": True}
