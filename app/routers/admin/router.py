"""Admin API router — all endpoints require authentication and role checks.

IMPORTANT: Specific literal routes (settings, uploads, dashboard, inbox, users,
activity, preview) are registered BEFORE the generic /{collection} catch-all so
that FastAPI path resolution works correctly.
"""
from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Any, Optional

import nh3
from fastapi import (
    APIRouter, Depends, File, HTTPException, Query, Request,
    UploadFile, status
)
from fastapi.responses import StreamingResponse

from app.models.activity import Activity
from app.models.clients import Client, Testimonial
from app.models.content import Feature, HeroSlide, Stat, WorkStep
from app.models.gallery import GalleryAlbum
from app.models.inbox import ContactMessage, InboxNote, ServiceRequest, TrainingApplication
from app.models.misc import FAQ, Download, Office, SiteSettings
from app.models.pages import Page
from app.models.posts import Post
from app.models.projects import Project
from app.models.services import Service, ServiceCategory
from app.models.team import Certification, TeamMember
from app.models.training import TrainingIntake, TrainingProgramme, TrainingStep
from app.models.user import User
from app.security.passwords import hash_password, MIN_PASSWORD_LENGTH
from app.security.permissions import (
    require_editor_or_above,
    require_super_admin,
    require_writer_or_above,
    require_any_role,
    require_inbox_or_above,
)
from app.services.export import export_to_xlsx
from app.services.images import save_pdf, save_upload
from app.services.revalidation import revalidate
from app.services.slugs import generate_slug
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["admin"])

DEFAULT_LIMIT = 20
MAX_LIMIT = 100

# ---------------------------------------------------------------------------
# CSRF check helper
# ---------------------------------------------------------------------------

def _check_csrf(request: Request) -> None:
    """Reject mutating requests whose Origin doesn't match SITE_URL."""
    origin = request.headers.get("origin", "")
    if not origin:
        return  # Allow server-to-server and curl in dev
    allowed = [settings.site_url]
    # Also allow localhost in development
    if any(h in settings.site_url for h in ["localhost", "127.0.0.1"]):
        allowed += [
            "http://localhost", "http://127.0.0.1",
            "http://localhost:3000", "http://localhost:8000",
        ]
    if not any(origin.startswith(a) for a in allowed):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"CSRF check failed: origin '{origin}' not allowed",
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _doc_to_dict(doc: Any) -> dict:
    d = doc.model_dump()
    if "_id" in d:
        d["id"] = str(d.pop("_id"))
    elif "id" in d and not isinstance(d["id"], str):
        d["id"] = str(d["id"])
    return d


def _paginate(total: int, page: int, limit: int) -> dict:
    return {
        "total": total,
        "page": page,
        "pages": max(1, math.ceil(total / limit)),
    }


async def _log(
    user: User, action: str, collection: str,
    item_id: str = "", item_label: str = "",
) -> None:
    await Activity(
        user_id=str(user.id),
        user_name=user.name,
        action=action,
        collection=collection,
        item_id=item_id,
        item_label=item_label,
        at=datetime.now(timezone.utc),
    ).insert()


def _sanitize_html(data: dict) -> dict:
    """Recursively sanitize string values with nh3."""
    result = {}
    for k, v in data.items():
        if isinstance(v, str):
            result[k] = nh3.clean(v)
        elif isinstance(v, dict):
            result[k] = _sanitize_html(v)
        elif isinstance(v, list):
            result[k] = [
                _sanitize_html(item) if isinstance(item, dict) else
                (nh3.clean(item) if isinstance(item, str) else item)
                for item in v
            ]
        else:
            result[k] = v
    return result


def _get_label(doc: Any) -> str:
    """Extract a human-readable label from a document."""
    for attr in ("title", "name", "question", "key"):
        val = getattr(doc, attr, None)
        if val is None:
            continue
        if hasattr(val, "en"):
            return val.en or getattr(val, "sw", "") or ""
        if isinstance(val, str):
            return val
    return str(getattr(doc, "id", ""))


# ---------------------------------------------------------------------------
# Registry — maps URL collection name → (ModelClass, min_write_role, min_publish_role)
# ---------------------------------------------------------------------------

COLLECTION_REGISTRY: dict[str, tuple[Any, str, str]] = {
    "hero-slides":          (HeroSlide,          "writer",  "editor"),
    "stats":                (Stat,               "writer",  "editor"),
    "features":             (Feature,            "writer",  "editor"),
    "work-steps":           (WorkStep,           "writer",  "editor"),
    "pages":                (Page,               "writer",  "editor"),
    "team-members":         (TeamMember,         "writer",  "editor"),
    "certifications":       (Certification,      "writer",  "editor"),
    "service-categories":   (ServiceCategory,    "editor",  "editor"),
    "services":             (Service,            "writer",  "editor"),
    "projects":             (Project,            "writer",  "editor"),
    "training-programmes":  (TrainingProgramme,  "writer",  "editor"),
    "training-intakes":     (TrainingIntake,     "writer",  "editor"),
    "training-steps":       (TrainingStep,       "writer",  "editor"),
    "clients":              (Client,             "writer",  "editor"),
    "testimonials":         (Testimonial,        "writer",  "editor"),
    "posts":                (Post,               "writer",  "editor"),
    "gallery-albums":       (GalleryAlbum,       "writer",  "editor"),
    "faqs":                 (FAQ,                "writer",  "editor"),
    "offices":              (Office,             "writer",  "editor"),
    "downloads":            (Download,           "writer",  "editor"),
}

ROLE_RANK = {"super_admin": 0, "editor": 1, "writer": 2, "inbox_officer": 3}


def _check_role(user: User, min_role: str) -> None:
    if ROLE_RANK.get(user.role, 99) > ROLE_RANK.get(min_role, 99):
        raise HTTPException(status_code=403, detail="Insufficient permissions")


# ===========================================================================
# SPECIFIC ROUTES (must come BEFORE the /{collection} catch-all)
# ===========================================================================

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

@router.get("/settings")
async def admin_get_settings(user: User = Depends(require_super_admin)) -> dict:
    s = await SiteSettings.find_one()
    return _doc_to_dict(s) if s else {}


@router.put("/settings")
async def admin_update_settings(
    request: Request,
    user: User = Depends(require_super_admin),
) -> dict:
    _check_csrf(request)
    body = await request.json()
    body = _sanitize_html(body)

    s = await SiteSettings.find_one()
    if not s:
        s = SiteSettings(**body)
        await s.insert()
    else:
        for k, v in body.items():
            if hasattr(s, k):
                setattr(s, k, v)
        await s.save()

    await revalidate(["/"])
    return _doc_to_dict(s)


# ---------------------------------------------------------------------------
# File uploads
# ---------------------------------------------------------------------------

@router.post("/uploads")
async def admin_upload(
    request: Request,
    user: User = Depends(require_writer_or_above),
    file: UploadFile = File(...),
) -> dict:
    _check_csrf(request)
    ct = (file.content_type or "").lower()
    if "pdf" in ct:
        url = await save_pdf(file)
        return {"type": "pdf", "url": url}
    else:
        img = await save_upload(file)
        return {"type": "image", **img.model_dump()}


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@router.get("/dashboard")
async def admin_dashboard(user: User = Depends(require_any_role)) -> dict:
    sr_count = await ServiceRequest.find(ServiceRequest.status == "new").count()
    ta_count = await TrainingApplication.find(TrainingApplication.status == "new").count()
    cm_count = await ContactMessage.find(ContactMessage.status == "new").count()

    sr_latest = await ServiceRequest.find_all().sort("-created_at").limit(5).to_list()
    ta_latest = await TrainingApplication.find_all().sort("-created_at").limit(5).to_list()
    cm_latest = await ContactMessage.find_all().sort("-created_at").limit(5).to_list()

    return {
        "counts": {
            "service_requests": sr_count,
            "training_applications": ta_count,
            "contact_messages": cm_count,
        },
        "latest_service_requests": [_doc_to_dict(i) for i in sr_latest],
        "latest_training_applications": [_doc_to_dict(i) for i in ta_latest],
        "latest_contact_messages": [_doc_to_dict(i) for i in cm_latest],
    }


# ---------------------------------------------------------------------------
# Inbox
# ---------------------------------------------------------------------------

INBOX_MODELS: dict[str, Any] = {
    "service-requests":       ServiceRequest,
    "training-applications":  TrainingApplication,
    "contact-messages":       ContactMessage,
}

INBOX_EXPORT_COLUMNS: dict[str, list[str]] = {
    "service-requests":      ["name", "phone", "email", "region", "district", "description", "status", "created_at"],
    "training-applications": ["name", "phone", "email", "gender", "region", "programme_id", "status", "created_at"],
    "contact-messages":      ["name", "phone", "email", "subject", "message", "status", "created_at"],
}


@router.get("/inbox/{inbox_type}/export")
async def inbox_export(
    inbox_type: str,
    status_filter: Optional[str] = Query(None, alias="status"),
    user: User = Depends(require_inbox_or_above),
) -> StreamingResponse:
    if inbox_type not in INBOX_MODELS:
        raise HTTPException(status_code=404, detail=f"Unknown inbox type: {inbox_type}")
    model_class = INBOX_MODELS[inbox_type]
    query: list = []
    if status_filter:
        query.append({"status": status_filter})
    items = await model_class.find(*query).sort("-created_at").to_list()
    columns = INBOX_EXPORT_COLUMNS.get(inbox_type, [])
    rows = [_doc_to_dict(i) for i in items]
    buf = export_to_xlsx(rows, columns)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{inbox_type}.xlsx"'},
    )


@router.get("/inbox/{inbox_type}/{id}")
async def inbox_get_one(
    inbox_type: str,
    id: str,
    user: User = Depends(require_inbox_or_above),
) -> dict:
    if inbox_type not in INBOX_MODELS:
        raise HTTPException(status_code=404, detail=f"Unknown inbox type: {inbox_type}")
    model_class = INBOX_MODELS[inbox_type]
    doc = await model_class.get(id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return _doc_to_dict(doc)


@router.get("/inbox/{inbox_type}")
async def inbox_list(
    inbox_type: str,
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    user: User = Depends(require_inbox_or_above),
) -> dict:
    if inbox_type not in INBOX_MODELS:
        raise HTTPException(status_code=404, detail=f"Unknown inbox type: {inbox_type}")
    model_class = INBOX_MODELS[inbox_type]
    query: list = []
    if status_filter:
        query.append({"status": status_filter})
    total = await model_class.find(*query).count()
    items = (
        await model_class.find(*query)
        .sort("-created_at")
        .skip((page - 1) * limit)
        .limit(limit)
        .to_list()
    )
    return {
        "items": [_doc_to_dict(i) for i in items],
        **_paginate(total, page, limit),
    }


@router.patch("/inbox/{inbox_type}/{id}")
async def inbox_patch(
    inbox_type: str,
    id: str,
    request: Request,
    user: User = Depends(require_inbox_or_above),
) -> dict:
    _check_csrf(request)
    if inbox_type not in INBOX_MODELS:
        raise HTTPException(status_code=404, detail=f"Unknown inbox type: {inbox_type}")
    model_class = INBOX_MODELS[inbox_type]
    doc = await model_class.get(id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    body = await request.json()
    if "status" in body:
        doc.status = body["status"]
    if "note" in body and body["note"]:
        note = InboxNote(
            text=body["note"],
            by=user.name,
            at=datetime.now(timezone.utc),
        )
        doc.notes.append(note)
    await doc.save()
    return _doc_to_dict(doc)


# ---------------------------------------------------------------------------
# Users (super_admin only)
# ---------------------------------------------------------------------------

@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    user: User = Depends(require_super_admin),
) -> dict:
    total = await User.count()
    items = (
        await User.find_all()
        .sort("name")
        .skip((page - 1) * limit)
        .limit(limit)
        .to_list()
    )
    return {
        "items": [_safe_user(u) for u in items],
        **_paginate(total, page, limit),
    }


@router.post("/users")
async def create_user(
    request: Request,
    user: User = Depends(require_super_admin),
) -> dict:
    _check_csrf(request)
    body = await request.json()
    if len(body.get("password", "")) < MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Password must be at least {MIN_PASSWORD_LENGTH} characters",
        )
    existing = await User.find_one(User.email == body["email"])
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    now = datetime.now(timezone.utc)
    new_user = User(
        name=body["name"],
        email=body["email"],
        password_hash=hash_password(body["password"]),
        role=body.get("role", "writer"),
        is_active=body.get("is_active", True),
        created_at=now,
        updated_at=now,
    )
    await new_user.insert()
    await _log(user, "create", "users", str(new_user.id), new_user.email)
    return _safe_user(new_user)


@router.put("/users/{id}")
async def update_user(
    id: str,
    request: Request,
    user: User = Depends(require_super_admin),
) -> dict:
    _check_csrf(request)
    target = await User.get(id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    body = await request.json()

    # Cannot demote last super_admin
    if target.role == "super_admin" and body.get("role") != "super_admin":
        count = await User.find(User.role == "super_admin").count()
        if count <= 1:
            raise HTTPException(status_code=400, detail="Cannot demote the last super_admin")

    if "name" in body:
        target.name = body["name"]
    if "role" in body:
        target.role = body["role"]
    if "is_active" in body:
        target.is_active = body["is_active"]
    if "password" in body and body["password"]:
        if len(body["password"]) < MIN_PASSWORD_LENGTH:
            raise HTTPException(
                status_code=400,
                detail=f"Password must be at least {MIN_PASSWORD_LENGTH} characters",
            )
        target.password_hash = hash_password(body["password"])
    target.updated_at = datetime.now(timezone.utc)
    await target.save()
    await _log(user, "update", "users", str(target.id), target.email)
    return _safe_user(target)


@router.delete("/users/{id}")
async def delete_user(
    id: str,
    request: Request,
    user: User = Depends(require_super_admin),
) -> dict:
    _check_csrf(request)
    target = await User.get(id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if str(target.id) == str(user.id):
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    if target.role == "super_admin":
        count = await User.find(User.role == "super_admin").count()
        if count <= 1:
            raise HTTPException(status_code=400, detail="Cannot delete the last super_admin")

    await target.delete()
    await _log(user, "delete", "users", id, target.email)
    return {"ok": True}


def _safe_user(u: User) -> dict:
    return {
        "id": str(u.id),
        "name": u.name,
        "email": u.email,
        "role": u.role,
        "is_active": u.is_active,
        "last_login": u.last_login.isoformat() if u.last_login else None,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }


# ---------------------------------------------------------------------------
# Activity log
# ---------------------------------------------------------------------------

@router.get("/activity")
async def activity_log(
    page: int = Query(1, ge=1),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    user: User = Depends(require_editor_or_above),
) -> dict:
    total = await Activity.count()
    items = (
        await Activity.find_all()
        .sort("-at")
        .skip((page - 1) * limit)
        .limit(limit)
        .to_list()
    )
    return {
        "items": [_doc_to_dict(i) for i in items],
        **_paginate(total, page, limit),
    }


# ---------------------------------------------------------------------------
# Preview
# ---------------------------------------------------------------------------

@router.get("/preview/{collection}/{id}")
async def preview_one(
    collection: str,
    id: str,
    lang: str = Query("en"),
    user: User = Depends(require_writer_or_above),
) -> dict:
    if collection not in COLLECTION_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Unknown collection: {collection}")
    model_class, _, _ = COLLECTION_REGISTRY[collection]
    doc = await model_class.get(id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    from app.routers.public.router import _doc_to_dict as public_to_dict
    return public_to_dict(doc, lang)


# ===========================================================================
# GENERIC CRUD (catch-all — must come AFTER all specific routes above)
# ===========================================================================

@router.get("/{collection}")
async def list_collection(
    collection: str,
    q: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    user: User = Depends(require_any_role),
) -> dict:
    if collection not in COLLECTION_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Unknown collection: {collection}")
    model_class, _, _ = COLLECTION_REGISTRY[collection]
    query: list = []
    if status_filter and hasattr(model_class, "status"):
        query.append({"status": status_filter})
    if q:
        query.append({"$or": [
            {"title.en": {"$regex": q, "$options": "i"}},
            {"title.sw": {"$regex": q, "$options": "i"}},
            {"name": {"$regex": q, "$options": "i"}},
        ]})
    total = await model_class.find(*query).count()
    items = (
        await model_class.find(*query)
        .sort("-created_at")
        .skip((page - 1) * limit)
        .limit(limit)
        .to_list()
    )
    return {
        "items": [_doc_to_dict(i) for i in items],
        **_paginate(total, page, limit),
    }


@router.get("/{collection}/{id}")
async def get_one(
    collection: str,
    id: str,
    user: User = Depends(require_any_role),
) -> dict:
    if collection not in COLLECTION_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Unknown collection: {collection}")
    model_class, _, _ = COLLECTION_REGISTRY[collection]
    doc = await model_class.get(id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return _doc_to_dict(doc)


@router.post("/{collection}")
async def create_one(
    collection: str,
    request: Request,
    user: User = Depends(require_any_role),
) -> dict:
    _check_csrf(request)
    if collection not in COLLECTION_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Unknown collection: {collection}")
    model_class, min_write, _ = COLLECTION_REGISTRY[collection]
    _check_role(user, min_write)

    body = await request.json()
    body = _sanitize_html(body)

    now = datetime.now(timezone.utc)
    body.setdefault("created_at", now)
    body.setdefault("updated_at", now)
    body["created_by"] = str(user.id)
    body["updated_by"] = str(user.id)

    # Generate slug if applicable
    if hasattr(model_class, "slug"):
        en_title = (
            body.get("title", {}).get("en", "")
            if isinstance(body.get("title"), dict)
            else body.get("name", "")
        )
        if en_title and not body.get("slug"):
            body["slug"] = generate_slug(en_title)
        sw_title = (
            body.get("title", {}).get("sw", "")
            if isinstance(body.get("title"), dict)
            else ""
        )
        if sw_title and not body.get("slug_sw"):
            body["slug_sw"] = generate_slug(sw_title)

    doc = model_class(**body)
    await doc.insert()

    await _log(user, "create", collection, str(doc.id), _get_label(doc))
    await revalidate([f"/{collection}"])
    return _doc_to_dict(doc)


@router.put("/{collection}/{id}")
async def update_one(
    collection: str,
    id: str,
    request: Request,
    user: User = Depends(require_any_role),
) -> dict:
    _check_csrf(request)
    if collection not in COLLECTION_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Unknown collection: {collection}")
    model_class, min_write, _ = COLLECTION_REGISTRY[collection]
    _check_role(user, min_write)

    doc = await model_class.get(id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    body = await request.json()
    body = _sanitize_html(body)

    now = datetime.now(timezone.utc)
    body["updated_at"] = now
    body["updated_by"] = str(user.id)

    # Regenerate slug if title changed and no explicit slug provided
    if hasattr(model_class, "slug") and not body.get("slug"):
        en_title = (
            body.get("title", {}).get("en", "")
            if isinstance(body.get("title"), dict)
            else ""
        )
        if en_title:
            body["slug"] = generate_slug(en_title)

    for k, v in body.items():
        if hasattr(doc, k):
            setattr(doc, k, v)
    await doc.save()

    await _log(user, "update", collection, str(doc.id), _get_label(doc))
    await revalidate([f"/{collection}/{getattr(doc, 'slug', id)}"])
    return _doc_to_dict(doc)


@router.delete("/{collection}/{id}")
async def delete_one(
    collection: str,
    id: str,
    request: Request,
    user: User = Depends(require_editor_or_above),
) -> dict:
    _check_csrf(request)
    if collection not in COLLECTION_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Unknown collection: {collection}")
    model_class, _, _ = COLLECTION_REGISTRY[collection]

    doc = await model_class.get(id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    label = _get_label(doc)
    await doc.delete()

    await _log(user, "delete", collection, id, label)
    await revalidate([f"/{collection}"])
    return {"ok": True}


@router.post("/{collection}/{id}/publish")
async def publish_one(
    collection: str,
    id: str,
    request: Request,
    user: User = Depends(require_editor_or_above),
) -> dict:
    _check_csrf(request)
    if collection not in COLLECTION_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Unknown collection: {collection}")
    model_class, _, min_pub = COLLECTION_REGISTRY[collection]
    _check_role(user, min_pub)

    doc = await model_class.get(id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not hasattr(doc, "status"):
        raise HTTPException(status_code=400, detail="This collection is not publishable")

    doc.status = "published"
    doc.updated_at = datetime.now(timezone.utc)
    doc.updated_by = str(user.id)
    await doc.save()

    await _log(user, "publish", collection, str(doc.id), _get_label(doc))
    await revalidate([f"/{collection}/{getattr(doc, 'slug', id)}"])
    return _doc_to_dict(doc)


@router.post("/{collection}/{id}/unpublish")
async def unpublish_one(
    collection: str,
    id: str,
    request: Request,
    user: User = Depends(require_editor_or_above),
) -> dict:
    _check_csrf(request)
    if collection not in COLLECTION_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Unknown collection: {collection}")
    model_class, _, _ = COLLECTION_REGISTRY[collection]

    doc = await model_class.get(id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not hasattr(doc, "status"):
        raise HTTPException(status_code=400, detail="This collection is not publishable")

    doc.status = "draft"
    doc.updated_at = datetime.now(timezone.utc)
    doc.updated_by = str(user.id)
    await doc.save()

    await _log(user, "unpublish", collection, str(doc.id), _get_label(doc))
    await revalidate([f"/{collection}/{getattr(doc, 'slug', id)}"])
    return _doc_to_dict(doc)


@router.post("/{collection}/reorder")
async def reorder_collection(
    collection: str,
    request: Request,
    user: User = Depends(require_writer_or_above),
) -> dict:
    _check_csrf(request)
    if collection not in COLLECTION_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Unknown collection: {collection}")
    model_class, min_write, _ = COLLECTION_REGISTRY[collection]
    _check_role(user, min_write)

    body = await request.json()
    ids = body if isinstance(body, list) else body.get("ids", [])
    for idx, doc_id in enumerate(ids):
        doc = await model_class.get(doc_id)
        if doc and hasattr(doc, "sort"):
            doc.sort = idx
            await doc.save()
    return {"ok": True}
