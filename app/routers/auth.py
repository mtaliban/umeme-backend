"""PIN login, logout na kubadilisha PIN."""

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request, Response

from ..auth import (
    check_attempts,
    client_key,
    create_token,
    current_shop_id,
    decode_token,
    hash_pin,
    note_attempt,
    reset_attempts,
    verify_pin,
)
from ..db import db
from ..schemas import PinChangeIn, PinIn
from ..tz import now

router = APIRouter(prefix="/auth", tags=["auth"])


def shop_out(shop: dict) -> dict:
    return {
        "id": str(shop["_id"]),
        "name": shop.get("name", ""),
        "phone": shop.get("phone", ""),
        "email": shop.get("email", ""),
    }


def _valid_pin(pin: str) -> bool:
    return isinstance(pin, str) and len(pin) == 4 and pin.isdigit()


@router.post("/pin")
async def login(body: PinIn, request: Request):
    key = client_key(request)
    check_attempts(key)
    shop = await db.shops.find_one({}, sort=[("created_at", 1)])
    if not shop or not verify_pin(body.pin, shop.get("pin_hash", "")):
        note_attempt(key)
        raise HTTPException(401, "PIN si sahihi")
    reset_attempts(key)
    return {"token": create_token(shop["_id"]), "shop": shop_out(shop)}


@router.post("/logout", status_code=204)
async def logout(request: Request):
    """204 bila body — app inatoka hata mtandao ukiwa umekatika.

    Kama simu imetuma kifaa chake (header `X-Device-Token` au body
    `{"fcm_token": "..."}`), kiondolewe kwenye orodha ya notifications.
    """
    scheme, _, raw = request.headers.get("authorization", "").partition(" ")
    token = raw.strip() if scheme.lower() == "bearer" else ""
    shop_id = None
    if token:
        sub = decode_token(token)
        try:
            shop_id = ObjectId(sub) if sub else None
        except Exception:
            shop_id = None

    device = (request.headers.get("x-device-token") or "").strip()
    if not device and request.headers.get("content-length") not in (None, "0"):
        try:
            body = await request.json()
        except Exception:
            body = None
        if isinstance(body, dict):
            device = str(body.get("fcm_token") or "").strip()

    if device and shop_id is not None:
        await db.devices.delete_many({"shop_id": shop_id, "fcm_token": device})
    return Response(status_code=204)


@router.put("/pin")
async def change_pin(body: PinChangeIn, request: Request, sid=Depends(current_shop_id)):
    shop = await db.shops.find_one({"_id": sid})
    if not shop:
        raise HTTPException(401, "Ingia tena")

    key = f"pin-change:{client_key(request)}"
    check_attempts(key)  # 5 makosa / dakika 10 → 429 "Subiri dakika 10"

    if not verify_pin(body.old_pin, shop.get("pin_hash", "")):
        note_attempt(key)
        # SI 401: 401 inamtoa mtumiaji nje ya app.
        raise HTTPException(400, "PIN ya sasa si sahihi")
    if not _valid_pin(body.new_pin):
        raise HTTPException(400, "PIN mpya iwe namba 4")
    if body.new_pin == body.old_pin or verify_pin(body.new_pin, shop.get("pin_hash", "")):
        raise HTTPException(400, "PIN mpya isiwe sawa na ya sasa")

    reset_attempts(key)
    await db.shops.update_one(
        {"_id": sid},
        {"$set": {"pin_hash": hash_pin(body.new_pin), "updated_at": now()}},
    )
    # Token iliyopo inaendelea kufanya kazi (JWT haibadilishwi).
    return {"ok": True}
