"""POST /analyze/deep — listing + comments combined."""
from __future__ import annotations
from fastapi import APIRouter, BackgroundTasks, Depends, Body, Header, Request

from app.auth import require_user
from app.cache import (
    hash_payload, get_scan, set_scan, get_idempotent, set_idempotent,
)
from app.config import DEEP_LISTING_WEIGHT, DEEP_COMMENTS_WEIGHT
from app.db.queries import save_scan, maybe_save_high_risk
from app.logging_config import get_logger
from app.models.schemas import CommentsPayload
from app.rate_limit import rate_limit_analyze
from app.routers.comments import analyze_comments_payload
from app.services.analyzer import analyze_listing_payload
from app.services.nlp_engine import detect_patterns
from app.services.score_calculator import band, risk_message
from app.services.insights import (
    contextual_risk_message, build_recommendations, build_verify_checklist,
)
from app.services.groq_summarizer import generate_deep_summary

router = APIRouter(prefix="/analyze", tags=["analyze"])
log = get_logger(__name__)


@router.post("/deep")
async def analyze_deep(
    request: Request,
    background: BackgroundTasks,
    payload: dict = Body(...),
    user=Depends(require_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    _rl=Depends(rate_limit_analyze),
):
    listing_in = payload.get("listing") or {}
    comments_in = payload.get("comments") or {
        "platform": listing_in.get("platform"),
        "comments": [],
        "page_number": 1,
        "total_pages": 1,
    }

    # ---------- Idempotency ----------
    if idempotency_key:
        idem_cache_key = f"{user['id']}:{idempotency_key}"
        cached = get_idempotent(idem_cache_key)
        if cached is not None:
            log.info("idempotent replay for key=%s", idempotency_key[:8])
            return cached

    # ---------- Result cache (per-content) ----------
    cache_key = hash_payload({"l": listing_in, "c": comments_in})
    cached = get_scan(cache_key)
    if cached is not None:
        if idempotency_key:
            set_idempotent(f"{user['id']}:{idempotency_key}", cached)
        return cached

    # ---------- Compute ----------
    listing_result = analyze_listing_payload(listing_in)
    comments_result = analyze_comments_payload(CommentsPayload(**comments_in))

    # NLP pattern matches from description for Groq context
    _nlp_hits = detect_patterns(listing_in.get("description") or "")
    _desc_patterns: dict = {}
    if _nlp_hits.get("urgency_match"):
        _desc_patterns["urgency_phrase_found"] = _nlp_hits["urgency_match"]
    if _nlp_hits.get("promise_match"):
        _desc_patterns["over_promise_phrase_found"] = _nlp_hits["promise_match"]
    if _nlp_hits.get("payment_match"):
        _desc_patterns["payment_warning_phrase_found"] = _nlp_hits["payment_match"]
    if _nlp_hits.get("vague_match"):
        _desc_patterns["vague_brand_phrase_found"] = _nlp_hits["vague_match"]
    _raw_desc = (listing_in.get("description") or "").strip()

    # Blend weights from config (must sum to ~1)
    bot_pct = comments_result["bot_likelihood"]
    fake_pct = comments_result["fake_review_likelihood"]
    comment_weight = (bot_pct + fake_pct) / 2  # 0..1
    n_comments = comments_result.get("comments_analyzed", 0)

    if n_comments == 0:
        # No reviews available — applying the formula would silently discount the
        # listing score by the comment weight (e.g. 35 × 0.7 = 24.5).
        # Zero reviews is a data gap, not evidence of safety; use listing score as-is.
        combined = listing_result["risk_score"]
    else:
        combined = int(round(
            listing_result["risk_score"] * DEEP_LISTING_WEIGHT
            + comment_weight * 100 * DEEP_COMMENTS_WEIGHT
        ))
    combined = max(0, min(combined, 100))

    level, color = band(combined)

    combined_flags = listing_result["flags"] + comments_result["flags"]

    deep_ctx = {
        "platform": listing_in.get("platform", ""),
        "combined_risk_score": combined,
        "combined_risk_level": level,
        "listing_score": listing_result["risk_score"],
        "listing_risk_level": listing_result["risk_level"],
        "confidence": listing_result["confidence"]["level"],
        "score_breakdown": listing_result["score_breakdown"],
        "listing_flags": listing_result["flags"],
        "positive_signals": [s["message"] for s in listing_result.get("positive_signals", [])],
        "recommendations": build_recommendations(combined_flags)[:6],
        "seller_account_age": listing_in.get("shop_age"),
        "seller_rating": listing_in.get("seller_rating"),
        "listing_rating_count": listing_in.get("rating_count"),
        "listing_sold_count": listing_in.get("sold_count"),
        "price": listing_in.get("price"),
        "description_patterns": _desc_patterns if _desc_patterns else None,
        "comments": {
            "analyzed": comments_result["comments_analyzed"],
            "bot_likelihood_pct": comments_result["bot_likelihood_pct"],
            "fake_review_pct": comments_result["fake_review_pct"],
            "dominant_sentiment": comments_result["dominant_sentiment"],
            "review_diversity_score": comments_result.get("review_diversity_score"),
            "flags": comments_result["flags"],
        },
    }
    groq_deep_msg = generate_deep_summary(deep_ctx)
    if groq_deep_msg:
        listing_result["risk_message"] = groq_deep_msg
        listing_result["risk_message_source"] = "groq"

    response = {
        "listing": listing_result,
        "comments": comments_result,
        "combined_risk_score": combined,
        "combined_risk_level": level,
        "combined_risk_color": color,
        "combined_risk_message": contextual_risk_message(level, combined_flags),
        "combined_recommendations": build_recommendations(combined_flags),
        "combined_verify_checklist": build_verify_checklist(combined_flags, level),
        # Surface the two signals independently so the UI can explain *why*
        "signals": {
            "listing_risk": listing_result["risk_score"],
            "bot_likelihood_pct": comments_result["bot_likelihood_pct"],
            "fake_review_pct": comments_result["fake_review_pct"],
            "weights": {
                "listing": DEEP_LISTING_WEIGHT,
                "comments": DEEP_COMMENTS_WEIGHT,
            },
        },
    }

    # ---------- Persist (off the request thread) ----------
    background.add_task(
        save_scan, user["id"], {
            "platform": listing_in.get("platform"),
            "url": listing_in.get("url"),
            "risk_score": combined,
            "risk_level": level,
            "flags": listing_result["flags"] + comments_result["flags"],
            "confidence_level": listing_result["confidence"]["level"],
            "confidence_pct": listing_result["confidence"]["percentage"],
            "scan_mode": "extension",
            "notes": groq_deep_msg or contextual_risk_message(level, combined_flags),
            "raw_data": {
                "flag_details": listing_result.get("flag_details"),
                "positive_signals": listing_result.get("positive_signals"),
                "recommendations": response.get("combined_recommendations"),
                "verify_checklist": response.get("combined_verify_checklist"),
                "comments_summary": {
                    "analyzed": comments_result["comments_analyzed"],
                    "no_comments_available": comments_result.get("no_comments_available", False),
                    "bot_likelihood_pct": comments_result["bot_likelihood_pct"],
                    "bot_likelihood_note": (
                        "Detects patterns associated with automated or coordinated activity — "
                        "such as duplicate comment text, time-clustered posts, generic phrases, "
                        "and bot-style usernames."
                    ),
                    "fake_review_pct": comments_result["fake_review_pct"],
                    "fake_review_note": (
                        "Combines an ML classifier trained on review patterns with rule-based "
                        "signals to flag comments that may not reflect genuine buyer experience."
                    ),
                    "dominant_sentiment": comments_result["dominant_sentiment"],
                },
                "risk_message_source": listing_result.get("risk_message_source"),
            },
        },
    )
    background.add_task(
        maybe_save_high_risk, {
            "platform": listing_in.get("platform"),
            "url": listing_in.get("url"),
            "risk_score": combined,
            "risk_level": level,
            "flags": listing_result["flags"] + comments_result["flags"],
        },
    )

    # ---------- Cache ----------
    set_scan(cache_key, response)
    if idempotency_key:
        set_idempotent(f"{user['id']}:{idempotency_key}", response)

    return response
