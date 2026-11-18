"""Firebase Cloud Messaging (FCM)."""

import logging
from pathlib import Path

from starlette.concurrency import run_in_threadpool

from ..config import settings
from ..db import db
from ..tz import now

logger = logging.getLogger("ummu.notify")

try:  # firebase-admin ni hiari — app inaendelea bila credentials
    import firebase_admin
    from firebase_admin import credentials, messaging
except Exception:  # pragma: no cover
    firebase_admin = None
    credentials = None
    messaging = None

_ready = False


def init_firebase() -> bool:
    global _ready
    if firebase_admin is None:
        logger.warning("firebase-admin haipo — notifications zimezimwa")
        _ready = False
        return False
    raw = (settings.firebase_credentials or "").strip()
    if not raw:
        logger.info("FIREBASE_CREDENTIALS haijawekwa — notifications zimezimwa")
        _ready = False
        return False
    path = Path(raw)
    if not path.exists():
        logger.warning("FIREBASE_CREDENTIALS haipo (%s) — notifications zimezimwa", path)
        _ready = False
        return False
    try:
        if not firebase_admin._apps:
            firebase_admin.initialize_app(credentials.Certificate(str(path)))
        _ready = True
    except Exception:  # pragma: no cover
        logger.exception("Imeshindikana kuanzisha Firebase")
        _ready = False
    return _ready


async def send(sid, type_: str, title: str, body: str, data: dict | None = None, exclude: str | None = None) -> bool:
    tokens = [d["fcm_token"] async for d in db.devices.find({"shop_id": sid})]
    if exclude:
        tokens = [t for t in tokens if t != exclude]
    tokens = [t for t in dict.fromkeys(tokens) if t]
    ok = False
    if tokens and _ready:
        try:
            message = messaging.MulticastMessage(
                tokens=tokens,
                notification=messaging.Notification(title=title, body=body),
                data={"type": type_, **{k: str(v) for k, v in (data or {}).items()}},
                android=messaging.AndroidConfig(priority="high"),
            )
            res = await run_in_threadpool(messaging.send_each_for_multicast, message)
            dead = []
            for token, resp in zip(tokens, res.responses):
                if resp.success:
                    continue
                exc = resp.exception
                name = type(exc).__name__ if exc is not None else ""
                if name in {"UnregisteredError", "SenderIdMismatchError", "InvalidArgumentError"}:
                    dead.append(token)
            if dead:
                await db.devices.delete_many({"fcm_token": {"$in": dead}})
            ok = True
        except Exception:  # pragma: no cover
            logger.exception("Kutuma notification kumeshindikana")
    await db.notifications_log.insert_one(
        {
            "shop_id": sid,
            "type": type_,
            "title": title,
            "body": body,
            "data": data or {},
            "sent_at": now(),
            "ok": ok,
        }
    )
    return ok
