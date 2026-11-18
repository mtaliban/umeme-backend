"""Taarifa za duka."""

from fastapi import APIRouter, Depends, HTTPException

from ..auth import current_shop_id
from ..db import db

router = APIRouter(tags=["me"])


@router.get("/me")
async def me(sid=Depends(current_shop_id)):
    shop = await db.shops.find_one({"_id": sid})
    if not shop:
        raise HTTPException(401, "Ingia tena")
    return {
        "id": str(shop["_id"]),
        "name": shop.get("name", ""),
        "phone": shop.get("phone", ""),
        "email": shop.get("email", ""),
    }
