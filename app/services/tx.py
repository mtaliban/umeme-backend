"""Transactions: zinapatikana kwenye replica set / Atlas pekee."""

from contextlib import asynccontextmanager

from ..db import db

_supported: bool | None = None


async def supported() -> bool:
    """Je, deployment inaunga mkono transactions?"""
    global _supported
    if _supported is None:
        try:
            info = await db.client.admin.command("hello")
            _supported = bool(info.get("setName") or info.get("msg") == "isdbgrid")
        except Exception:
            _supported = False
    return _supported


@asynccontextmanager
async def transaction():
    """Session yenye transaction — commit ikifanikiwa, abort ikiwa na kosa."""
    session = await db.client.start_session()
    try:
        async with session.start_transaction():
            yield session
    finally:
        await session.end_session()


def reset_cache() -> None:
    global _supported
    _supported = None
