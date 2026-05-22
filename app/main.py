"""SureShopPH FastAPI entry point."""
from __future__ import annotations
import logging
import time
from contextlib import asynccontextmanager
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import (
    APP_NAME, APP_VERSION,
    CORS_ALLOW_ORIGINS, CORS_ALLOW_ORIGIN_REGEX,
    MAX_REQUEST_BYTES, LOG_LEVEL,
    validate_env,
)
from app.logging_config import setup_logging, set_request_id, get_logger
from app.routers import listing, comments, deep, url_check, scans, reports, admin, auth, training

setup_logging(getattr(logging, LOG_LEVEL, logging.INFO))
log = get_logger("sureshop.main")


# ---------- Lightweight metrics counters (single-process) ----------
_metrics = {
    "requests_total": 0,
    "requests_failed": 0,
    "scans_cached_hits": 0,
    "scans_cached_misses": 0,
    "rate_limited": 0,
}


def metrics_inc(key: str, by: int = 1) -> None:
    if key in _metrics:
        _metrics[key] += by


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Refuse to start when required env is missing rather than failing on
    # the first request with a cryptic DB/JWT error.
    validate_env()
    log.info("Starting %s %s", APP_NAME, APP_VERSION)
    log.info("CORS allowed origins: %s", CORS_ALLOW_ORIGINS)
    # Preload NLP model so first user does not pay the load cost
    try:
        from app.services import nlp_engine
        nlp_engine._try_load()  # type: ignore[attr-defined]
        log.info("NLP engine ready (calamanCy loaded=%s)", nlp_engine._nlp is not None)  # type: ignore[attr-defined]
    except Exception as e:
        log.warning("NLP preload failed: %s", e.__class__.__name__)
    # Preload classifier
    try:
        from app.services import ml_classifier
        ml_classifier._try_load_model()  # type: ignore[attr-defined]
        log.info("Fake-review classifier loaded=%s", ml_classifier.is_model_loaded())
    except Exception as e:
        log.warning("Classifier preload failed: %s", e.__class__.__name__)
    yield
    log.info("Shutting down %s", APP_NAME)


app = FastAPI(title=APP_NAME, version=APP_VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_origin_regex=CORS_ALLOW_ORIGIN_REGEX,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-ID"],
    allow_private_network=True,
)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next: Callable):
    """Attach correlation ID, enforce body size, time the request."""
    rid = set_request_id(request.headers.get("x-request-id"))
    start = time.perf_counter()
    metrics_inc("requests_total")

    # Enforce request body size on writes
    if request.method in ("POST", "PATCH", "PUT"):
        cl = request.headers.get("content-length")
        if cl and cl.isdigit() and int(cl) > MAX_REQUEST_BYTES:
            metrics_inc("requests_failed")
            return JSONResponse(
                status_code=413,
                content={"detail": f"Request body exceeds {MAX_REQUEST_BYTES} bytes"},
                headers={"X-Request-ID": rid},
            )

    try:
        response: Response = await call_next(request)
    except Exception as e:
        metrics_inc("requests_failed")
        log.exception("Unhandled error: %s", e)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
            headers={"X-Request-ID": rid},
        )

    elapsed_ms = (time.perf_counter() - start) * 1000.0
    response.headers["X-Request-ID"] = rid
    log.info(
        "%s %s -> %s in %.1fms",
        request.method, request.url.path, response.status_code, elapsed_ms,
    )
    return response


@app.get("/")
async def root():
    return {"name": APP_NAME, "version": APP_VERSION, "status": "ok"}


@app.get("/health")
async def health():
    """Deep health check: DB reachable + classifier + NLP loaded."""
    from app.db.supabase_client import ping as db_ping
    from app.services import ml_classifier, nlp_engine

    db_ok = db_ping()
    nlp_engine._try_load()  # type: ignore[attr-defined]
    ml_classifier._try_load_model()  # type: ignore[attr-defined]

    status_dict = {
        "status": "ok" if db_ok else "degraded",
        "db": "ok" if db_ok else "unreachable",
        "nlp_loaded": nlp_engine._nlp is not None,  # type: ignore[attr-defined]
        "classifier_loaded": ml_classifier.is_model_loaded(),
        "version": APP_VERSION,
    }
    code = 200 if db_ok else 503
    return JSONResponse(status_dict, status_code=code)


@app.get("/metrics")
async def metrics():
    """Lightweight metrics view (single-process). For Prometheus, swap for prom_client."""
    return {"counters": dict(_metrics)}


app.include_router(listing.router)
app.include_router(comments.router)
app.include_router(deep.router)
app.include_router(url_check.router)
app.include_router(scans.router)
app.include_router(reports.router)
app.include_router(admin.router)
app.include_router(auth.router)
app.include_router(training.router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    log.warning("422 validation error on %s %s: %s", request.method, request.url.path, exc.errors())
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
