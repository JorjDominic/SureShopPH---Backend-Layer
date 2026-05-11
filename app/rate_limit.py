"""Simple in-memory token-bucket rate limiter.

Single-process only — for production multi-worker use, swap for Redis.
Keyed by (user_id or client IP). Used as a FastAPI dependency.
"""
from __future__ import annotations
import time
from collections import defaultdict
from threading import Lock
from typing import Dict, Tuple

from fastapi import HTTPException, Request, status


class _Bucket:
    __slots__ = ("tokens", "updated_at")

    def __init__(self, tokens: float, updated_at: float):
        self.tokens = tokens
        self.updated_at = updated_at


class TokenBucketLimiter:
    def __init__(self, rate_per_minute: int, burst: int | None = None):
        self.rate = rate_per_minute / 60.0  # tokens per second
        self.capacity = burst if burst is not None else rate_per_minute
        self._buckets: Dict[str, _Bucket] = defaultdict(
            lambda: _Bucket(self.capacity, time.monotonic())
        )
        self._lock = Lock()

    def allow(self, key: str) -> Tuple[bool, float]:
        now = time.monotonic()
        with self._lock:
            b = self._buckets[key]
            elapsed = now - b.updated_at
            b.tokens = min(self.capacity, b.tokens + elapsed * self.rate)
            b.updated_at = now
            if b.tokens >= 1.0:
                b.tokens -= 1.0
                return True, 0.0
            wait = (1.0 - b.tokens) / self.rate if self.rate > 0 else 60.0
            return False, wait


# Pre-configured limiters
_analyze_limiter = TokenBucketLimiter(rate_per_minute=60, burst=20)
_url_limiter = TokenBucketLimiter(rate_per_minute=120, burst=30)
_admin_limiter = TokenBucketLimiter(rate_per_minute=120, burst=30)


def _client_key(request: Request, user_id: str | None = None) -> str:
    if user_id:
        return f"u:{user_id}"
    fwd = request.headers.get("x-forwarded-for", "")
    ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown")
    return f"ip:{ip}"


def _check(limiter: TokenBucketLimiter, request: Request, user: dict | None) -> None:
    key = _client_key(request, (user or {}).get("id"))
    ok, wait = limiter.allow(key)
    if not ok:
        try:
            from app.main import metrics_inc
            metrics_inc("rate_limited")
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Retry in ~{wait:.1f}s.",
            headers={"Retry-After": str(max(1, int(wait)))},
        )


def rate_limit_analyze(request: Request) -> None:
    _check(_analyze_limiter, request, None)


def rate_limit_analyze_user(request: Request, user_id: str) -> None:
    _check(_analyze_limiter, request, {"id": user_id})


def rate_limit_url(request: Request) -> None:
    _check(_url_limiter, request, None)


def rate_limit_admin(request: Request) -> None:
    _check(_admin_limiter, request, None)
