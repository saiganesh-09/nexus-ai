"""Per-user rate limiting middleware (sliding window, in-memory).

Per-process limiter — correct for single-instance deployments; swap the
backend for Redis in multi-instance setups (noted in docs)."""

import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import get_settings

_hits: dict[str, deque[float]] = defaultdict(deque)


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        if settings.environment == "test" or request.url.path == "/api/v1/health":
            return await call_next(request)

        # Prefer user id from Authorization token subject when present;
        # fall back to client IP for unauthenticated endpoints.
        key = request.client.host if request.client else "unknown"
        auth = request.headers.get("authorization", "")
        if auth.startswith("Bearer "):
            # Cheap subject extraction without full validation (auth dep
            # still enforces validity downstream).
            try:
                import jwt
                payload = jwt.decode(
                    auth[7:], settings.secret_key,
                    algorithms=[settings.algorithm],
                    options={"verify_exp": False},
                )
                key = f"user:{payload.get('sub', key)}"
            except Exception:
                pass

        now = time.time()
        window = settings.rate_limit_window_seconds
        q = _hits[key]
        while q and q[0] <= now - window:
            q.popleft()
        if len(q) >= settings.rate_limit_requests:
            return JSONResponse(
                status_code=429,
                content={"error": {"code": "rate_limited",
                                   "message": "Too many requests — slow down.",
                                   "details": {"limit": settings.rate_limit_requests,
                                               "window_seconds": window}}},
            )
        q.append(now)
        return await call_next(request)
