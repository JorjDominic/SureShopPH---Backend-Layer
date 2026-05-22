"""POST /analyze/listing — Normal Scan."""
from fastapi import APIRouter, BackgroundTasks, Depends, Body, Header
from datetime import datetime, timezone

from app.auth import require_user
from app.cache import hash_payload, get_scan, set_scan, get_idempotent, set_idempotent
from app.db.queries import save_scan, maybe_save_high_risk
from app.models.schemas import ListingAnalysisResponse
from app.rate_limit import rate_limit_analyze
from app.services.analyzer import analyze_listing_payload

router = APIRouter(prefix="/analyze", tags=["analyze"])


@router.post("/listing", response_model=ListingAnalysisResponse)
async def analyze_listing(
    background: BackgroundTasks,
    payload: dict = Body(...),
    user=Depends(require_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    _rl=Depends(rate_limit_analyze),
):
    if idempotency_key:
        idem_key = f"{user['id']}:{idempotency_key}"
        cached = get_idempotent(idem_key)
        if cached is not None:
            return cached

    cache_key = hash_payload({"listing": payload})
    cached = get_scan(cache_key)
    if cached is not None:
        if idempotency_key:
            set_idempotent(f"{user['id']}:{idempotency_key}", cached)
        return cached

    result = analyze_listing_payload(payload)
    
    # Add ISO timestamp for client-side relative time calculations (Issue 10)
    result["scanned_at_iso"] = datetime.now(timezone.utc).isoformat()

    background.add_task(save_scan, user["id"], {
        "platform": payload.get("platform"),
        "url": payload.get("url"),
        "risk_score": result["risk_score"],
        "risk_level": result["risk_level"],
        "flags": result["flags"],
        "confidence_level": result["confidence"]["level"],
        "confidence_pct": result["confidence"]["percentage"],
        "scan_mode": "extension",
        "notes": result.get("risk_message"),
        "raw_data": {
            "flag_details": result.get("flag_details"),
            "positive_signals": result.get("positive_signals"),
            "recommendations": result.get("recommendations"),
            "verify_checklist": result.get("verify_checklist"),
            "risk_message_source": result.get("risk_message_source"),
        },
    })
    background.add_task(maybe_save_high_risk, {
        "platform": payload.get("platform"),
        "url": payload.get("url"),
        "risk_score": result["risk_score"],
        "risk_level": result["risk_level"],
        "flags": result["flags"],
    })

    set_scan(cache_key, result)
    if idempotency_key:
        set_idempotent(f"{user['id']}:{idempotency_key}", result)
    return result
