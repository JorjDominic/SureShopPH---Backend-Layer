"""Confidence calculation — platform-normalized, trusts extension's data_quality."""
from typing import Dict, List

from app.config import CONFIDENCE_FIELDS, CONFIDENCE_TRUST, NOT_AVAILABLE

# Human-readable labels for field names used in confidence messages
_FIELD_LABELS: Dict[str, str] = {
    "price": "price",
    "shop_age": "seller join date",
    "rating": "product rating",
    "rating_count": "number of ratings",
    "description": "product description",
    "response_rate": "seller response rate",
    "seller_rating": "seller rating",
    "condition": "item condition",
    "sold_count": "number of items sold",
    "specifications": "product specifications",
    "image_count": "product images",
}


def _build_confidence_message(level: str, could_not_retrieve: List[str]) -> str:
    """Dynamically build a plain-language explanation of what confidence means
    for this specific scan, naming the actual missing fields when relevant."""
    if level == "High":
        return (
            "All key listing details were retrieved successfully. "
            "The risk assessment is based on complete information."
        )
    missing_labels = [_FIELD_LABELS.get(f, f.replace("_", " ")) for f in could_not_retrieve]
    if level == "Moderate":
        if missing_labels:
            joined = " and ".join(missing_labels) if len(missing_labels) <= 2 \
                else ", ".join(missing_labels[:-1]) + ", and " + missing_labels[-1]
            return (
                f"Some listing details could not be retrieved — specifically the "
                f"{joined}. The risk score may not fully reflect all available "
                f"signals for this listing."
            )
        return (
            "Some listing details were not visible on this page. The risk score "
            "covers most of the available information but may not be complete."
        )
    # Low
    if missing_labels:
        joined = " and ".join(missing_labels) if len(missing_labels) <= 2 \
            else ", ".join(missing_labels[:-1]) + ", and " + missing_labels[-1]
        return (
            f"Most listing details were unavailable for this scan — including "
            f"{joined}. The risk score is based on limited information and "
            f"should be interpreted with extra caution."
        )
    return (
        "Limited listing information was available for this scan. "
        "The risk score is based on limited information and should be "
        "interpreted with extra caution."
    )


def compute_confidence(
    platform: str,
    data_quality_missing: List[str],
    field_confidences: Dict[str, str] | None = None,
) -> Dict:
    """Compute overall extraction confidence.

    A field that is "present but low-confidence" should not give full credit.
    `field_confidences` is an optional map field_name -> "high"/"medium"/"low".
    When supplied, present fields contribute their trust multiplier instead of 1.0.
    """
    fields = CONFIDENCE_FIELDS.get(platform, [])
    total = len(fields)
    missing_set = set(data_quality_missing or [])
    field_confidences = field_confidences or {}

    could_not_retrieve = [f for f in fields if f in missing_set]
    present_fields = [f for f in fields if f not in missing_set]

    weighted_present = 0.0
    for f in present_fields:
        c = (field_confidences.get(f) or "high").lower()
        weighted_present += CONFIDENCE_TRUST.get(c, 1.0)

    fields_present = len(present_fields)
    pct = int(round((weighted_present / total) * 100)) if total else 0
    pct = max(0, min(pct, 100))

    if platform == "facebook":
        if weighted_present >= 4:
            level = "High"
        elif weighted_present >= 2:
            level = "Moderate"
        else:
            level = "Low"
    else:
        if weighted_present >= 5:
            level = "High"
        elif weighted_present >= 3:
            level = "Moderate"
        else:
            level = "Low"

    return {
        "level": level,
        "percentage": pct,
        "fields_present": fields_present,
        "total_fields": total,
        "confidence_message": _build_confidence_message(level, could_not_retrieve),
        "could_not_retrieve": could_not_retrieve,
        "not_available_on_platform": list(NOT_AVAILABLE.get(platform, [])),
    }
