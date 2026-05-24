"""Shared analyzer used by listing.py and deep.py."""
from __future__ import annotations
import re
from datetime import datetime, timezone
from typing import Any, Dict

from app.services.rule_engine import score_seller, score_metadata, score_text
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
from app.services.groq_summarizer import generate_listing_summary
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


_PARTS_OUT_RE = re.compile(
    r"\bparts?\s+out\b|\bpart-out\b|\bparting\s+out\b"
    r"|\bpor\s+parte\b"
    r"|\bselling\s+(?:by\s+)?(?:piece|parts?|separately|individually)\b",
    re.IGNORECASE,
)
_PM_PRICE_RE = re.compile(
    r"\bpm\s+for\s+(?:actual\s+)?price\b"
    r"|\b(?:message|msg|dm|chat|inbox)\s+(?:me\s+)?for\s+(?:actual\s+)?price\b"
    r"|\bprice\s*[:=]\s*(?:pm|dm|tbd)\b"
    r"|\bprice\s+on\s+(?:pm|dm|chat|request)\b",
    re.IGNORECASE,
)


def _derive_listing_type(listing: Dict[str, Any]) -> str:
    """Classify listing type from title and description patterns."""
    desc = (listing.get("description") or "").lower()
    title = (listing.get("title") or listing.get("product_name") or "").lower()
    combined = f"{title} {desc}"
    if _PARTS_OUT_RE.search(combined):
        return "parts_out"
    if _PM_PRICE_RE.search(combined):
        return "price_hidden"
    if re.search(r"\binstallment\b|\bmonthly\s+payment\b|\bdp\s+(?:only|muna)\b|\bdownpayment\b", combined, re.I):
        return "installment"
    if re.search(r"\bbundle\b", combined, re.I):
        return "bundle"
    return "single_item"


def _derive_condition(description: str) -> str | None:
    """Infer item condition from description text when not explicitly provided."""
    if not description:
        return None
    d = description.lower()
    if re.search(r"\bbrand\s*new\b|\bnew\s+sealed\b|\bnew\s+in\s+box\b|\bbnib\b", d):
        return "Brand New"
    if re.search(r"\bused\s*like\s*new\b|\bopen\s+box\b|\bulu\b", d):
        return "Used - Like New"
    if re.search(r"\bpre[-\s]?(?:owned|loved)\b|\bpreloved\b|\bsecond[-\s]?hand\b|\b2nd\s+hand\b", d):
        return "Pre-owned"
    if re.search(r"\bfor\s+parts?\b|\bnot\s+working\b|\bdefective\b|\bsalvage\b", d):
        return "For Parts"
    if re.search(r"\bused\b", d):
        return "Used"
    return None


def analyze_listing_payload(listing: Dict[str, Any]) -> Dict[str, Any]:
    """Run the full listing analysis and return a response-shaped dict."""
    nlp_hits = detect_patterns(listing.get("description") or "")

    # Per-field extractor confidence supplied by the content script (optional)
    field_conf = (listing.get("data_quality") or {}).get("field_confidence") or {}

    seller_score, seller_flags = score_seller(listing)
    meta_score, meta_flags = score_metadata(listing)
    text_score, text_flags, triggered_by = score_text(listing, nlp_hits=nlp_hits)

    # Apply confidence-aware trust multipliers per category. A flag firing on
    # a low-confidence extracted field is worth less than one firing on a
    # high-confidence field — this prevents bad selectors from inflating risk.
    seller_trust = _category_trust(field_conf, ["shop_age", "response_rate", "seller_rating", "seller_name"])
    meta_trust = _category_trust(field_conf, ["price", "rating", "rating_count", "image_count", "sold_count"])
    text_trust = _category_trust(field_conf, ["description", "specifications"])

    seller_score = int(round(seller_score * seller_trust))
    meta_score = int(round(meta_score * meta_trust))
    text_score = int(round(text_score * text_trust))

    total = seller_score + meta_score + text_score
    total = max(0, min(total, 100))

    flags = seller_flags + meta_flags + text_flags

    # Compound: no buyer history at all — zero sales combined with no ratings
    # represents complete absence of purchase record. This fires after category
    # caps so the cumulative uncertainty is reflected in the total score.
    if (
        "Product has no ratings yet" in flags
        and "Zero recorded sales" in flags
    ):
        total = min(total + 18, 100)
        flags = ["Unverified listing: no recorded sales or buyer ratings"] + flags

    # Compound: sales exist but zero buyer ratings — more unusual than no activity
    # at all, since even a small fraction of buyers normally leaves a review.
    # Consistent with review suppression, inflated/fake sales, or shell listings.
    # Applied after category caps; slightly lower than the zero-everything penalty
    # because the presence of sales is itself a partial legitimacy signal.
    if "Has recorded sales but no buyer ratings — unusual pattern" in flags:
        total = min(total + 12, 100)
        flags = ["Suspicious activity pattern: listing has recorded sales but no buyer ratings"] + flags

    level, color = band(total)

    breakdown = {
        "seller_attributes": seller_score,
        "listing_metadata": meta_score,
        "textual_nlp": text_score,
    }

    confidence = compute_confidence(
        listing.get("platform", ""),
        (listing.get("data_quality") or {}).get("missing", []),
        field_confidences=field_conf,
    )

    # Low-confidence data penalty: when key fields are missing the scoring rules
    # fire on incomplete data, which may underestimate actual risk.
    if confidence["level"] == "Low" and len(confidence.get("could_not_retrieve", [])) >= 3:
        total = min(total + 10, 100)
        flags.append("Limited extracted data — risk assessment may not capture all available signals")
        level, color = band(total)

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

    recs = build_recommendations(flags, platform=platform)
    recs_total = len(build_recommendations(flags, limit=999, platform=platform))
    checklist = build_verify_checklist(flags, level)
    checklist_total = len(build_verify_checklist(flags, level, limit=999))

    listing_type = _derive_listing_type(listing)
    derived_condition = _derive_condition(listing.get("description") or "") if not listing.get("condition") else None
    account_age_label = "Profile Age" if platform == "facebook" else "Shop Age"

    # Build description pattern summary for Groq — only include matched phrases
    _desc_patterns: Dict[str, Any] = {}
    if nlp_hits.get("urgency_match"):
        _desc_patterns["urgency_phrase_found"] = nlp_hits["urgency_match"]
    if nlp_hits.get("promise_match"):
        _desc_patterns["over_promise_phrase_found"] = nlp_hits["promise_match"]
    if nlp_hits.get("payment_match"):
        _desc_patterns["payment_warning_phrase_found"] = nlp_hits["payment_match"]
    if nlp_hits.get("vague_match"):
        _desc_patterns["vague_brand_phrase_found"] = nlp_hits["vague_match"]

    _raw_desc = (listing.get("description") or "").strip()

    groq_listing_ctx = {
        "platform": listing.get("platform", ""),
        "risk_level": level,
        "risk_score": total,
        "confidence": confidence["level"],
        "score_breakdown": {
            "seller_attributes": {"score": seller_score, "max": 25},
            "listing_metadata": {"score": meta_score, "max": 25},
            "text_nlp": {"score": text_score, "max": 35},
        },
        "flags": flags,
        "positive_signals": [s["message"] for s in positive],
        "recommendations": recs[:3],
        "seller_account_age": listing.get("shop_age"),
        "seller_rating": listing.get("seller_rating"),
        "listing_rating_count": listing.get("rating_count"),
        "listing_sold_count": listing.get("sold_count"),
        "price": listing.get("price"),
        "description_patterns": _desc_patterns if _desc_patterns else None,
        "listing_rating": listing.get("rating"),
        "response_rate": listing.get("response_rate"),
        "listing_type": listing_type,
        "condition": listing.get("condition") or derived_condition,
    }
    groq_risk_message = generate_listing_summary(groq_listing_ctx)

    return {
        "risk_score": total,
        "risk_level": level,
        "risk_color": color,
        "risk_message": groq_risk_message or dynamic_risk_message(flags, level),
        "risk_message_source": "groq" if groq_risk_message else "rule_based",
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
        "listing_type": listing_type,
        "derived_condition": derived_condition,
        "account_age_label": account_age_label,
        "scan_timestamp": datetime.now(timezone.utc).isoformat(),
    }
