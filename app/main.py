"""UMMU AYMAN OUTFITS — API ya daftari la duka."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    if not errors:
        return JSONResponse(status_code=422, content={"detail": "Ombi halipo sahihi"})
    error = errors[0]
    field = ".".join(str(x) for x in error.get("loc", [])[1:])
    message = error.get("msg", "Ombi halipo sahihi")
    detail = f"{field}: {message}" if field else message
    return JSONResponse(status_code=422, content={"detail": detail})


@app.get("/health", tags=["health"])
async def health():
    return {"ok": True}


@app.get("/api/health", tags=["health"], include_in_schema=False)
async def api_health():
    """Alias kwa healthcheck ya docker-compose (Caddy inaondoa /api)."""
    return {"ok": True}


for module in (auth, me, devices, home, products, variants, daily, expenses, receipts, reports):
    app.include_router(module.router)
