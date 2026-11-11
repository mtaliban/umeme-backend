"""Public API router — read-only, published content only."""
from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Query

from app.models.clients import Client, Testimonial
from app.models.content import Feature, HeroSlide, Stat, WorkStep
from app.models.gallery import GalleryAlbum
from app.models.misc import FAQ, Download, Office, SiteSettings
from app.models.pages import Page
from app.models.posts import Post
from app.models.projects import Project
from app.models.services import Service, ServiceCategory
from app.models.team import Certification, TeamMember
from app.models.training import TrainingIntake, TrainingProgramme, TrainingStep

router = APIRouter(prefix="/api/public", tags=["public"])

DEFAULT_LIMIT = 9
MAX_LIMIT = 100


def _stringify_ids(obj: Any) -> Any:
    """Recursively convert any non-string, non-primitive ID-like objects to strings."""
    if isinstance(obj, dict):
        return {k: _stringify_ids(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_stringify_ids(i) for i in obj]
    # Convert ObjectId or similar to string
    if hasattr(obj, '__class__') and obj.__class__.__name__ in ('ObjectId', 'PydanticObjectId'):
        return str(obj)
    return obj


def _doc_to_dict(doc: Any, lang: str = "en") -> dict:
    """Convert a Beanie document to a plain JSON-serialisable dict.

    TranslatableStr fields are kept as {en, sw} objects so the frontend
    can resolve the correct language client-side.
    """
    d = doc.model_dump(by_alias=True)
    # Ensure _id is a string
    if "_id" in d:
        d["_id"] = str(d["_id"]) if d["_id"] is not None else None
    # Also expose id for convenience
    if "_id" in d:
        d["id"] = d["_id"]
    # Recursively stringify any remaining ObjectId-like objects
    return _stringify_ids(d)


def _paginate(total: int, page: int, limit: int) -> dict:
    return {
        "total": total,
        "page": page,
        "pages": max(1, math.ceil(total / limit)),
    }


# ---- Settings ----

@router.get("/settings")
async def public_settings(lang: str = Query("en")) -> dict:
    s = await SiteSettings.find_one()
    if not s:
        return {}
    return _doc_to_dict(s, lang)


# ---- Home ----

@router.get("/home")
async def home(lang: str = Query("en")) -> dict:
    settings_doc = await SiteSettings.find_one()
    settings_dict = _doc_to_dict(settings_doc, lang) if settings_doc else {}

    hero_slides = [_doc_to_dict(s, lang) for s in await HeroSlide.find(HeroSlide.is_active == True).sort("sort").to_list()]
    stats = [_doc_to_dict(s, lang) for s in await Stat.find_all().sort("sort").to_list()]
    features = [_doc_to_dict(f, lang) for f in await Feature.find_all().sort("sort").to_list()]
    work_steps = [_doc_to_dict(w, lang) for w in await WorkStep.find_all().sort("sort").to_list()]
    service_categories = [_doc_to_dict(c, lang) for c in await ServiceCategory.find_all().sort("sort").to_list()]
    featured_services = [_doc_to_dict(s, lang) for s in await Service.find(
        Service.status == "published", Service.is_featured == True
    ).sort("sort").to_list()]
    featured_projects = [_doc_to_dict(p, lang) for p in await Project.find(
        Project.status == "published", Project.is_featured == True
    ).sort("sort").limit(6).to_list()]
    training_list = await TrainingProgramme.find(
        TrainingProgramme.status == "published"
    ).sort("sort").limit(3).to_list()
    training_highlight = _doc_to_dict(training_list[0], lang) if training_list else None
    clients = [_doc_to_dict(c, lang) for c in await Client.find(Client.is_featured == True).sort("sort").to_list()]
    testimonials = [_doc_to_dict(t, lang) for t in await Testimonial.find(Testimonial.is_active == True).sort("sort").to_list()]
    latest_posts = [_doc_to_dict(p, lang) for p in await Post.find(
        Post.status == "published", Post.is_featured == True
    ).sort("-published_at").limit(3).to_list()]
    about_page = await Page.find_one(Page.key == "about")
    about = _doc_to_dict(about_page, lang) if about_page else None

    return {
        "settings": settings_dict,
        "hero_slides": hero_slides,
        "stats": stats,
        "features": features,
        "work_steps": work_steps,
        "service_categories": service_categories,
        "featured_services": featured_services,
        "featured_projects": featured_projects,
        "training_highlight": training_highlight,
        "clients": clients,
        "testimonials": testimonials,
        "latest_posts": latest_posts,
        "about": about,
        "cta": settings_dict.get("cta"),
    }


# ---- Pages ----

@router.get("/pages/{key}")
async def get_page(key: str, lang: str = Query("en")) -> dict:
    page = await Page.find_one(Page.key == key)
    if not page:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Page '{key}' not found")
    return _doc_to_dict(page, lang)


# ---- Team & certs ----

@router.get("/team")
async def public_team(lang: str = Query("en")) -> list:
    members = await TeamMember.find(TeamMember.is_active == True).sort("sort").to_list()
    return [_doc_to_dict(m, lang) for m in members]


@router.get("/certifications")
async def public_certifications(lang: str = Query("en")) -> list:
    certs = await Certification.find_all().sort("sort").to_list()
    return [_doc_to_dict(c, lang) for c in certs]


# ---- Offices & downloads ----

@router.get("/offices")
async def public_offices(lang: str = Query("en")) -> list:
    offices = await Office.find_all().sort("sort").to_list()
    return [_doc_to_dict(o, lang) for o in offices]


@router.get("/downloads")
async def public_downloads(lang: str = Query("en")) -> list:
    downloads = await Download.find_all().sort("sort").to_list()
    return [_doc_to_dict(d, lang) for d in downloads]


# ---- Service categories & services ----

@router.get("/service-categories")
async def public_service_categories(lang: str = Query("en")) -> list:
    cats = await ServiceCategory.find_all().sort("sort").to_list()
    return [_doc_to_dict(c, lang) for c in cats]


@router.get("/services")
async def public_services(
    category: Optional[str] = Query(None),
    lang: str = Query("en"),
) -> list:
    query = [Service.status == "published"]
    if category:
        query.append(Service.category_id == category)
    items = await Service.find(*query).sort("sort").to_list()
    return [_doc_to_dict(i, lang) for i in items]


@router.get("/services/{slug}")
async def public_service(slug: str, lang: str = Query("en")) -> dict:
    from fastapi import HTTPException
    item = await Service.find_one(
        Service.status == "published",
        {"$or": [{"slug": slug}, {"slug_sw": slug}]},
    )
    if not item:
        raise HTTPException(status_code=404, detail="Service not found")
    return _doc_to_dict(item, lang)


# ---- Projects ----

@router.get("/projects")
async def public_projects(
    category: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    year: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    lang: str = Query("en"),
) -> dict:
    query: list = [Project.status == "published"]
    if category:
        query.append(Project.category_id == category)
    if status_filter:
        query.append(Project.project_status == status_filter)
    if year:
        query.append({"start_date": {"$gte": f"{year}-01-01", "$lte": f"{year}-12-31"}})

    total = await Project.find(*query).count()
    items = await Project.find(*query).sort("-created_at").skip((page - 1) * limit).limit(limit).to_list()
    return {
        "items": [_doc_to_dict(i, lang) for i in items],
        **_paginate(total, page, limit),
    }


@router.get("/projects/{slug}")
async def public_project(slug: str, lang: str = Query("en")) -> dict:
    from fastapi import HTTPException
    item = await Project.find_one(
        Project.status == "published",
        {"$or": [{"slug": slug}, {"slug_sw": slug}]},
    )
    if not item:
        raise HTTPException(status_code=404, detail="Project not found")
    return _doc_to_dict(item, lang)


# ---- Training ----

@router.get("/training")
async def public_training(lang: str = Query("en")) -> list:
    items = await TrainingProgramme.find(TrainingProgramme.status == "published").sort("sort").to_list()
    return [_doc_to_dict(i, lang) for i in items]


@router.get("/training-steps")
async def public_training_steps(lang: str = Query("en")) -> list:
    items = await TrainingStep.find_all().sort("number").to_list()
    return [_doc_to_dict(i, lang) for i in items]


@router.get("/intakes")
async def public_intakes(lang: str = Query("en")) -> list:
    items = await TrainingIntake.find(TrainingIntake.status == "open").sort("start_date").to_list()
    return [_doc_to_dict(i, lang) for i in items]


@router.get("/training/{slug}")
async def public_training_detail(slug: str, lang: str = Query("en")) -> dict:
    from fastapi import HTTPException
    item = await TrainingProgramme.find_one(
        TrainingProgramme.status == "published",
        {"$or": [{"slug": slug}, {"slug_sw": slug}]},
    )
    if not item:
        raise HTTPException(status_code=404, detail="Training programme not found")
    # Also attach intakes
    result = _doc_to_dict(item, lang)
    intakes = await TrainingIntake.find(TrainingIntake.programme_id == str(item.id)).sort("start_date").to_list()
    result["intakes"] = [_doc_to_dict(i, lang) for i in intakes]
    return result


# ---- Clients & testimonials ----

@router.get("/clients")
async def public_clients(lang: str = Query("en")) -> list:
    items = await Client.find_all().sort("sort").to_list()
    return [_doc_to_dict(i, lang) for i in items]


@router.get("/testimonials")
async def public_testimonials(lang: str = Query("en")) -> list:
    items = await Testimonial.find(Testimonial.is_active == True).sort("sort").to_list()
    return [_doc_to_dict(i, lang) for i in items]


# ---- Posts ----

@router.get("/posts")
async def public_posts(
    category: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    lang: str = Query("en"),
) -> dict:
    query: list = [Post.status == "published"]
    if category:
        query.append(Post.category == category)
    if q:
        query.append({"$or": [
            {"title.en": {"$regex": q, "$options": "i"}},
            {"title.sw": {"$regex": q, "$options": "i"}},
            {"excerpt.en": {"$regex": q, "$options": "i"}},
        ]})
    total = await Post.find(*query).count()
    items = await Post.find(*query).sort("-published_at").skip((page - 1) * limit).limit(limit).to_list()
    return {
        "items": [_doc_to_dict(i, lang) for i in items],
        **_paginate(total, page, limit),
    }


@router.get("/posts/{slug}")
async def public_post(slug: str, lang: str = Query("en")) -> dict:
    from fastapi import HTTPException
    item = await Post.find_one(
        Post.status == "published",
        {"$or": [{"slug": slug}, {"slug_sw": slug}]},
    )
    if not item:
        raise HTTPException(status_code=404, detail="Post not found")
    return _doc_to_dict(item, lang)


# ---- Gallery ----

@router.get("/gallery")
async def public_gallery(
    category: Optional[str] = Query(None),
    lang: str = Query("en"),
) -> list:
    query: list = [GalleryAlbum.status == "published"]
    if category:
        query.append(GalleryAlbum.category == category)
    items = await GalleryAlbum.find(*query).sort("sort").to_list()
    return [_doc_to_dict(i, lang) for i in items]


@router.get("/gallery/{slug}")
async def public_gallery_album(slug: str, lang: str = Query("en")) -> dict:
    from fastapi import HTTPException
    item = await GalleryAlbum.find_one(
        GalleryAlbum.status == "published",
        {"$or": [{"slug": slug}, {"slug_sw": slug}]},
    )
    if not item:
        raise HTTPException(status_code=404, detail="Gallery album not found")
    return _doc_to_dict(item, lang)


# ---- FAQs ----

@router.get("/faqs")
async def public_faqs(
    category: Optional[str] = Query(None),
    lang: str = Query("en"),
) -> list:
    query: list = [FAQ.is_active == True]
    if category:
        query.append(FAQ.category == category)
    items = await FAQ.find(*query).sort("sort").to_list()
    return [_doc_to_dict(i, lang) for i in items]


# ---- Sitemap ----

@router.get("/sitemap")
async def public_sitemap() -> list:
    """Return all published slugs (both languages) with updated_at."""
    result = []

    async def _add(collection_name: str, model: Any, slug_field: str = "slug") -> None:
        docs = await model.find(model.status == "published").to_list()
        for doc in docs:
            result.append({
                "collection": collection_name,
                "slug_en": getattr(doc, "slug", ""),
                "slug_sw": getattr(doc, "slug_sw", "") or getattr(doc, "slug", ""),
                "updated_at": doc.updated_at.isoformat() if getattr(doc, "updated_at", None) else None,
            })

    await _add("services", Service)
    await _add("projects", Project)
    await _add("training", TrainingProgramme)
    await _add("posts", Post)
    await _add("gallery", GalleryAlbum)
    return result
