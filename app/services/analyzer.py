"""Shared analyzer used by listing.py and deep.py."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict

from app.services.rule_engine import score_seller, score_metadata, score_text, score_url
from app.services.confidence import compute_confidence
from app.services.score_calculator import (
    band, risk_message, build_product_notice, platform_signals,
    build_positive_signals, build_scan_completeness, enriched_score_breakdown,
)
from app.services.nlp_engine import detect_patterns
from app.services.insights import (
    enrich_flags, build_recommendations, build_verify_checklist,
    contextual_risk_message, dynamic_risk_message, enriched_breakdown,
)
from app.services.score_calculator import closing_line as _closing_line
from app.config import CONFIDENCE_TRUST


def _category_trust(field_confidences: Dict[str, str], fields: list[str]) -> float:
    """Average trust multiplier across the supplied fields. Defaults to 1.0
    when no confidence info is available (preserves legacy behavior)."""
    if not field_confidences:
        return 1.0
    seen = [field_confidences.get(f) for f in fields if field_confidences.get(f)]
    if not seen:
        return 1.0
    return sum(CONFIDENCE_TRUST.get(c, 1.0) for c in seen) / len(seen)


def analyze_listing_payload(listing: Dict[str, Any]) -> Dict[str, Any]:
    """Run the full listing analysis and return a response-shaped dict."""
    nlp_hits = detect_patterns(listing.get("description") or "")

    # Per-field extractor confidence supplied by the content script (optional)
    field_conf = (listing.get("data_quality") or {}).get("field_confidence") or {}

    seller_score, seller_flags = score_seller(listing)
    meta_score, meta_flags = score_metadata(listing)
    text_score, text_flags, triggered_by = score_text(listing, nlp_hits=nlp_hits)
    url_score, url_flags = score_url(listing.get("url") or "")

    # Apply confidence-aware trust multipliers per category. A flag firing on
    # a low-confidence extracted field is worth less than one firing on a
    # high-confidence field — this prevents bad selectors from inflating risk.
    seller_trust = _category_trust(field_conf, ["shop_age", "response_rate", "seller_rating", "seller_name"])
    meta_trust = _category_trust(field_conf, ["price", "rating", "rating_count", "image_count", "sold_count"])
    text_trust = _category_trust(field_conf, ["description", "specifications"])

    seller_score = int(round(seller_score * seller_trust))
    meta_score = int(round(meta_score * meta_trust))
    text_score = int(round(text_score * text_trust))

    total = seller_score + meta_score + text_score + url_score
    total = max(0, min(total, 100))
    level, color = band(total)

    flags = seller_flags + meta_flags + text_flags + url_flags

    breakdown = {
        "seller_attributes": seller_score,
        "listing_metadata": meta_score,
        "textual_nlp": text_score,
        "url_domain": url_score,
    }

    confidence = compute_confidence(
        listing.get("platform", ""),
        (listing.get("data_quality") or {}).get("missing", []),
        field_confidences=field_conf,
    )

    notice = build_product_notice(listing, breakdown)
    signals = platform_signals(listing)
    positive = build_positive_signals(listing)
    completeness = build_scan_completeness(confidence["percentage"])
    plat = (listing.get("platform") or "").lower()
    breakdown_enriched = enriched_score_breakdown(breakdown, flags)

    platform = listing.get("platform", "").lower()
    scan_mode_note: str | None = None
    if platform == "facebook":
        scan_mode_note = (
            "Comments Scan and Deep Scan are not available on Facebook "
            "Marketplace as this platform commonly does not display buyer "
            "reviews for individual listings. Normal Scan covers all listing "
            "information available on this platform."
        )
    elif platform in ("shopee", "lazada"):
        rating_count = listing.get("rating_count")
        try:
            _rc = int(rating_count) if rating_count is not None else -1
        except (ValueError, TypeError):
            _rc = -1
        if _rc == 0:
            scan_mode_note = (
                "This listing has no buyer ratings yet. "
                "There are no comments available for a Comments Scan at this time."
            )

    recs = build_recommendations(flags)
    recs_total = len(build_recommendations(flags, limit=999))
    checklist = build_verify_checklist(flags, level)
    checklist_total = len(build_verify_checklist(flags, level, limit=999))

    return {
        "risk_score": total,
        "risk_level": level,
        "risk_color": color,
        "risk_message": dynamic_risk_message(flags, level),
        "closing_line": _closing_line(level),
        "flags": flags,
        "flag_details": enrich_flags(flags, plat, triggered_by=triggered_by),
        "positive_signals": positive,
        "recommendations": recs,
        "recommendations_total": recs_total,
        "verify_checklist": checklist,
        "checklist_total": checklist_total,
        "confidence": confidence,
        "score_breakdown": breakdown,
        "score_breakdown_details": breakdown_enriched,
        "product_notice": notice,
        "platform_signals": signals,
        "scan_completeness": completeness,
        "scan_mode_note": scan_mode_note,
        "scan_timestamp": datetime.now(timezone.utc).isoformat(),
    }
