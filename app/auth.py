"""PIN, JWT na kikomo cha majaribio."""

from datetime import datetime, timedelta

import jwt
from bson import ObjectId
from fastapi import HTTPException, Request
from fastapi.security.utils import get_authorization_scheme_param
from passlib.context import CryptContext

from .config import settings
from .db import db
from .tz import now

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

MAX_ATTEMPTS = 5
WINDOW = timedelta(minutes=10)
_attempts: dict[str, list[datetime]] = {}


def hash_pin(pin: str) -> str:
    return _pwd.hash(pin)


def verify_pin(pin: str, pin_hash: str) -> bool:
    try:
        return _pwd.verify(pin, pin_hash or "")
    except Exception:
        return False


def client_key(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host
    return "default"


def _recent(key: str) -> list[datetime]:
    cutoff = now() - WINDOW
    items = [t for t in _attempts.get(key, []) if t >= cutoff]
    if items:
        _attempts[key] = items
    else:
        _attempts.pop(key, None)
    return items


def check_attempts(key: str) -> None:
    if len(_recent(key)) >= MAX_ATTEMPTS:
        raise HTTPException(429, "Subiri dakika 10")


def note_attempt(key: str) -> None:
    _attempts.setdefault(key, []).append(now())


def reset_attempts(key: str | None = None) -> None:
    if key is None:
        _attempts.clear()
    else:
        _attempts.pop(key, None)


def create_token(shop_id) -> str:
    payload = {"sub": str(shop_id), "exp": now() + timedelta(days=settings.jwt_days)}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> str | None:
    try:
        data = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    sub = data.get("sub")
    return str(sub) if sub else None


async def current_shop_id(request: Request) -> ObjectId:
    """Dependency: duka la token, au 401 'Ingia tena'."""
    scheme, token = get_authorization_scheme_param(request.headers.get("authorization", ""))
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(401, "Ingia tena")
    sub = decode_token(token)
    if not sub:
        raise HTTPException(401, "Ingia tena")
    try:
        sid = ObjectId(sub)
    except Exception:
        raise HTTPException(401, "Ingia tena")
    if not await db.shops.find_one({"_id": sid}, {"_id": 1}):
        raise HTTPException(401, "Ingia tena")
    return sid
