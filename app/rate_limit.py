"""Simple per-IP rate limiting for chat endpoint (Phase 7)."""

from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

_hits: dict[str, list[float]] = defaultdict(list)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """In-memory sliding-window rate limit for ``POST /api/chat``."""

    def __init__(
        self,
        app,
        *,
        limit: int = 30,
        window_seconds: int = 60,
        path_prefix: str = "/api/chat",
    ) -> None:
        super().__init__(app)
        self.limit = limit
        self.window_seconds = window_seconds
        self.path_prefix = path_prefix

    def _client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    def _is_rate_limited(self, ip: str) -> bool:
        now = time.time()
        cutoff = now - self.window_seconds
        timestamps = [ts for ts in _hits[ip] if ts > cutoff]
        if len(timestamps) >= self.limit:
            return True
        timestamps.append(now)
        _hits[ip] = timestamps
        return False

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.method == "POST" and request.url.path.startswith(self.path_prefix):
            if self._is_rate_limited(self._client_ip(request)):
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Please try again shortly."},
                )
        return await call_next(request)


def reset_rate_limit_state() -> None:
    """Clear in-memory counters (for tests)."""
    _hits.clear()
