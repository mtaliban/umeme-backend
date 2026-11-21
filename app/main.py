"""UMMU AYMAN OUTFITS — API ya daftari la duka."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer

from . import jobs
from .db import create_indexes, db
from .routers import (
    auth,
    daily,
    devices,
    expenses,
    home,
    me,
    products,
    receipts,
    reports,
    stock,
    test_reset,
    variants,
)
from .services import notify

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ummu")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_indexes()
    notify.init_firebase()
    try:
        jobs.start()
    except Exception:  # pragma: no cover
        logger.exception("Scheduler haijaanza")
    yield
    jobs.stop()
    db.client.close()


app = FastAPI(title="UMMU AYMAN OUTFITS", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Majina ya field → ujumbe wa Kiswahili wa spec (R1 za kila ukurasa).
FIELD_MESSAGES = {
    "qty": "Jaza idadi",
    "add_qty": "Jaza idadi",
    "selling": "Jaza bei",
    "price": "Jaza bei",
    "buying": "Jaza buying",
    "amount": "Jaza kiasi",
    "discount": "Punguzo si sahihi",
    "name": "Jaza jina",
}


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """Kila kosa la muundo wa ombi lirudi `{"detail": "<Kiswahili>"}` (si list)."""
    errors = exc.errors()
    logger.info("Ombi halipo sahihi: %s", errors)
    if not errors:
        return JSONResponse(status_code=422, content={"detail": "Ombi halipo sahihi"})
    loc = [str(x) for x in errors[0].get("loc", []) if x != "body"]
    field = loc[-1] if loc else ""
    detail = FIELD_MESSAGES.get(field, "Ombi halipo sahihi")
    return JSONResponse(status_code=422, content={"detail": detail})


@app.get("/health", tags=["health"])
async def health():
    return {"ok": True}


@app.get("/api/health", tags=["health"], include_in_schema=False)
async def api_health():
    """Alias kwa healthcheck ya docker-compose (Caddy inaondoa /api)."""
    return {"ok": True}


for module in (
    auth,
    me,
    devices,
    home,
    products,
    stock,
    variants,
    daily,
    expenses,
    receipts,
    reports,
    test_reset,
):
    app.include_router(module.router)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
    )
    schema.setdefault("components", {}).setdefault("securitySchemes", {})["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }
    for path in schema.get("paths", {}).values():
        for operation in path.values():
            if isinstance(operation, dict):
                operation.setdefault("security", [{"BearerAuth": []}])
    # /auth/pin na /health hazihitaji token
    for path_key in ("/auth/pin", "/health", "/api/health"):
        if path_key in schema.get("paths", {}):
            for operation in schema["paths"][path_key].values():
                if isinstance(operation, dict):
                    operation["security"] = []
    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi
