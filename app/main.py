import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import settings
from app.db import init_db, get_db_status
from app.security.rate_limit import limiter
from app.services.bootstrap import ensure_super_admin

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await ensure_super_admin()
    yield


app = FastAPI(
    title="Company Website API",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# ---- Rate limiting middleware ----
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ---- CORS ----
origins = [settings.site_url]
if "localhost" in settings.site_url or "127.0.0.1" in settings.site_url:
    origins += [
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1",
        "http://127.0.0.1:3000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Routers ----
from app.routers.auth import router as auth_router
from app.routers.forms import router as forms_router
from app.routers.public.router import router as public_router
from app.routers.admin.router import router as admin_router

app.include_router(auth_router)
app.include_router(forms_router)
app.include_router(public_router)
app.include_router(admin_router)


@app.get("/api/health", tags=["system"])
async def health():
    db_ok = await get_db_status()
    return {"status": "ok", "db": "ok" if db_ok else "error"}
