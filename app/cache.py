"""In-memory caches: scan results (deep) and URL-check results.

Keyed by content hash. Single-process; swap for Redis to scale horizontally.
"""
from __future__ import annotations
import hashlib
import json
import time
from collections import OrderedDict
from threading import Lock
from typing import Any, Dict, Optional, Tuple


class _LRUTTL:
    def __init__(self, max_items: int, ttl_seconds: int):
        self._items: "OrderedDict[str, Tuple[float, Any]]" = OrderedDict()
        self._max = max_items
        self._ttl = ttl_seconds
        self._lock = Lock()

    def get(self, key: str) -> Optional[Any]:
        now = time.monotonic()
        with self._lock:
            entry = self._items.get(key)
            if entry is None:
                return None
            ts, value = entry
            if now - ts > self._ttl:
                self._items.pop(key, None)
                return None
            self._items.move_to_end(key)
            return value

    def set(self, key: str, value: Any) -> None:
        now = time.monotonic()
        with self._lock:
            if key in self._items:
                self._items.move_to_end(key)
            self._items[key] = (now, value)
            while len(self._items) > self._max:
                self._items.popitem(last=False)


# 5 minutes TTL, 1024 entries
_scan_cache = _LRUTTL(max_items=1024, ttl_seconds=300)
# 30 minutes TTL for URL safety
_url_cache = _LRUTTL(max_items=2048, ttl_seconds=1800)
# Idempotency: 24h, request-id keyed
_idem_cache = _LRUTTL(max_items=4096, ttl_seconds=86400)


def _stable_dump(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, default=str, ensure_ascii=False)


def hash_payload(payload: Dict[str, Any]) -> str:
    return hashlib.sha256(_stable_dump(payload).encode("utf-8")).hexdigest()


def _bump(key: str) -> None:
    try:
        from app.main import metrics_inc
        metrics_inc(key)
    except Exception:
        pass


def get_scan(key: str) -> Optional[Dict[str, Any]]:
    v = _scan_cache.get(key)
    _bump("scans_cached_hits" if v is not None else "scans_cached_misses")
    return v


def set_scan(key: str, value: Dict[str, Any]) -> None:
    _scan_cache.set(key, value)


def get_url(url: str) -> Optional[Dict[str, Any]]:
    return _url_cache.get(url.lower().strip())


def set_url(url: str, value: Dict[str, Any]) -> None:
    _url_cache.set(url.lower().strip(), value)


def get_idempotent(key: str) -> Optional[Dict[str, Any]]:
    return _idem_cache.get(key)


def set_idempotent(key: str, value: Dict[str, Any]) -> None:
    _idem_cache.set(key, value)
