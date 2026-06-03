"""In-memory sliding-window rate limiter for the FastAPI endpoint.

Zero external dependencies — uses ``time.monotonic`` and a plain dict.
Cleans stale entries lazily per request so no background thread needed.

Usage::

    from api.rate_limiter import RateLimitMiddleware

    app.add_middleware(RateLimitMiddleware, max_requests=10, window_seconds=60)
"""

from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

_MAX_REQUESTS = 10
_WINDOW_SECONDS = 60


class RateLimitExceeded(Exception):
    """Raised when a client exceeds the allowed request rate."""


class SlidingWindowRateLimiter:
    """Track request timestamps per client key and reject if over threshold."""

    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._clients: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        timestamps = self._clients[key]

        # prune outdated entries (lazy)
        self._clients[key] = [t for t in timestamps if t > cutoff]

        if len(self._clients[key]) >= self.max_requests:
            return False

        self._clients[key].append(now)
        return True


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware that rate-limits ``POST /api/analyze`` by client IP.

    Set ``max_requests`` and ``window_seconds`` at construction time::

        app.add_middleware(
            RateLimitMiddleware,
            max_requests=10,
            window_seconds=60,
        )
    """

    def __init__(
        self,
        app: ASGIApp,
        max_requests: int = _MAX_REQUESTS,
        window_seconds: int = _WINDOW_SECONDS,
    ) -> None:
        super().__init__(app)
        self._limiter = SlidingWindowRateLimiter(max_requests, window_seconds)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.method == "POST" and request.url.path == "/api/analyze":
            client_ip = request.client.host if request.client else "unknown"
            if not self._limiter.is_allowed(client_ip):
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Demasiadas solicitudes. Intenta de nuevo en unos segundos.",
                        "detail": (
                            f"Límite de {self._limiter.max_requests} "
                            f"solicitudes por {self._limiter.window_seconds} "
                            f"segundos excedido."
                        ),
                    },
                    headers={"Retry-After": str(self._limiter.window_seconds)},
                )
        return await call_next(request)
