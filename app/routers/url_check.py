"""POST /analyze/url — URL safety check (domain only)."""
import asyncio
from fastapi import APIRouter, Depends

from app.auth import require_user
from app.cache import get_url, set_url
from app.models.schemas import UrlPayload, UrlSafetyResponse, DomainInfo
from app.rate_limit import rate_limit_url
from app.services.rule_engine import score_url
from app.services.domain_info import lookup_domain_info, score_domain_age
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

    # Run heuristic URL checks (fast, synchronous)
    score, flags = score_url(payload.url)

    # Run WHOIS lookup in a thread so it doesn't block the event loop
    domain_data = await asyncio.get_event_loop().run_in_executor(
        None, lookup_domain_info, payload.url
    )
    age_score, age_flags = score_domain_age(domain_data)

    # Combine: heuristic score (capped at 25) + domain age score, total capped at 100
    combined_raw = min(25, score) + age_score
    total = min(100, combined_raw * 4)
    flags = flags + age_flags

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
        "domain_info": DomainInfo(**domain_data),
    }
    set_url(payload.url, result)
    return result
