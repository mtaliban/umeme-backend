"""Middleware ya utendaji (sehemu 7.1 na 7.2).

* JSON inapunguzwa kwa gzip (middleware moja tu — Caddy haifanyi gzip tena).
* Kila jibu lina header `X-Time-Ms`; ombi likizidi 800 ms liandikwe kwenye log.
"""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("ummu.timing")

SLOW_REQUEST_MS = 800


class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        started = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started) * 1000
        response.headers["X-Time-Ms"] = str(int(elapsed_ms))
        if elapsed_ms > SLOW_REQUEST_MS:
            logger.warning(
                "Ombi la pole: %s %s — %d ms",
                request.method,
                request.url.path,
                int(elapsed_ms),
            )
        return response
