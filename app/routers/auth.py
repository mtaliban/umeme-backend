"""PIN login, logout na kubadilisha PIN."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from ..auth import (
    check_attempts,
    client_key,
    create_token,
    current_shop_id,
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
async def logout():
    return Response(status_code=204)


@router.put("/pin")
async def change_pin(body: PinChangeIn, sid=Depends(current_shop_id)):
    shop = await db.shops.find_one({"_id": sid})
    if not shop:
        raise HTTPException(401, "Ingia tena")
    if not verify_pin(body.old_pin, shop.get("pin_hash", "")):
        raise HTTPException(400, "PIN ya zamani si sahihi")
    if not _valid_pin(body.new_pin):
        raise HTTPException(400, "PIN iwe tarakimu 4")
    await db.shops.update_one(
        {"_id": sid},
        {"$set": {"pin_hash": hash_pin(body.new_pin), "updated_at": now()}},
    )
    return {"ok": True}
