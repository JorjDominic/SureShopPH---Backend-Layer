"""POST /analyze/url — URL safety check (domain only)."""
from fastapi import APIRouter, Depends

from app.auth import require_user
from app.cache import get_url, set_url
from app.models.schemas import UrlPayload, UrlSafetyResponse
from app.rate_limit import rate_limit_url
from app.services.rule_engine import score_url
from app.services.score_calculator import band
from app.services.insights import (
    enrich_flags, build_recommendations, build_verify_checklist,
    contextual_risk_message,
)

router = APIRouter(prefix="/analyze", tags=["analyze"])


@router.post("/url", response_model=UrlSafetyResponse)
async def analyze_url(
    payload: UrlPayload,
    user=Depends(require_user),
    _rl=Depends(rate_limit_url),
):
    cached = get_url(payload.url)
    if cached is not None:
        return cached

    score, flags = score_url(payload.url)
    # URL category is /25 — multiply by 4 to express on 0-100 scale
    total = min(100, score * 4)
    level, _color = band(total)
    result = {
        "url": payload.url,
        "risk_score": total,
        "risk_level": level,
        "risk_message": contextual_risk_message(level, flags),
        "flags": flags,
        "flag_details": enrich_flags(flags),
        "recommendations": build_recommendations(flags),
        "verify_checklist": build_verify_checklist(flags, level),
    }
    set_url(payload.url, result)
    return result
