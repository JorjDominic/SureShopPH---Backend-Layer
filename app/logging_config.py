"""Structured logging setup with request correlation IDs."""
from __future__ import annotations
import logging
import sys
import uuid
from contextvars import ContextVar

_request_id: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id.get()
        return True


def get_request_id() -> str:
    return _request_id.get()


def set_request_id(value: str | None = None) -> str:
    rid = value or uuid.uuid4().hex[:12]
    _request_id.set(rid)
    return rid


def setup_logging(level: int = logging.INFO) -> None:
    root = logging.getLogger()
    if getattr(root, "_sureshop_configured", False):
        return
    root.setLevel(level)
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s"
        )
    )
    handler.addFilter(RequestIdFilter())
    root.addHandler(handler)
    root._sureshop_configured = True  # type: ignore[attr-defined]


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
