"""Vifaa vya FCM."""

from fastapi import APIRouter, Depends, Response

from ..auth import current_shop_id
from ..db import db
from ..schemas import DeviceIn
from ..tz import now

router = APIRouter(tags=["devices"])


@router.post("/devices")
async def add_device(body: DeviceIn, sid=Depends(current_shop_id)):
    token = body.fcm_token.strip()
    if not token:
        return {"ok": False}
    await db.devices.update_one(
        {"fcm_token": token},
        {
            "$set": {
                "shop_id": sid,
                "fcm_token": token,
                "platform": body.platform,
                "updated_at": now(),
            }
        },
        upsert=True,
    )
    return {"ok": True}


@router.delete("/devices/{token}", status_code=204)
async def remove_device(token: str, sid=Depends(current_shop_id)):
    await db.devices.delete_many({"shop_id": sid, "fcm_token": token})
    return Response(status_code=204)
