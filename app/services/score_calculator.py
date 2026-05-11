"""Final score assembly — bands, color, message, product notice."""
from __future__ import annotations
from typing import Dict, List, Tuple

from app.config import RISK_BANDS


def band(score: int) -> Tuple[str, str]:
    for lo, hi, level, color in RISK_BANDS:
        if lo <= score <= hi:
            return level, color
    return "Very Low", "green"


def risk_message(level: str) -> str:
    return {
        "Very Low": (
            "Few risk signals observed. Continue with normal caution when "
            "buying online."
        ),
        "Low": (
            "Some minor signals observed. Review the listing details before "
            "purchasing."
        ),
        "Medium": (
            "Multiple characteristics associated with elevated risk. "
            "Verify seller reputation and product details before buying."
        ),
        "High": (
            "Several observable risk signals present. Strongly consider "
            "alternative listings or verified sellers."
        ),
    }.get(level, "")


PRODUCT_KEYWORDS = [
    "brand", "publisher", "edition", "model", "isbn", "manufacturer",
    "author", "version",
]

# Per-indicator recommended actions for the product notice
_NOTICE_ACTIONS: Dict[str, str] = {
    "Description does not mention brand, publisher, or edition": (
        "Ask the seller directly about the brand, edition, or authenticity "
        "of this item before completing your purchase."
    ),
    "Price is below typical category baseline": (
        "Compare the price with similar listings on this platform and ask the "
        "seller to confirm the product is genuine and complete."
    ),
    "Specifications section is empty": (
        "Request complete product specifications from the seller, especially "
        "for electronics, appliances, or branded goods."
    ),
}


def build_product_notice(listing: Dict, breakdown: Dict[str, int]) -> Dict | None:
    desc = (listing.get("description") or "").lower()
    product_name = (listing.get("product_name") or "").strip()
    indicators: List[str] = []

    if len(desc) > 20 and not any(k in desc for k in PRODUCT_KEYWORDS):
        indicators.append("Description does not mention brand, publisher, or edition")

    price = listing.get("price")
    if isinstance(price, (int, float)) and 0 < price < 200:
        indicators.append("Price is below typical category baseline")

    if listing.get("platform") in ("shopee", "lazada") and listing.get("specifications") is None:
        indicators.append("Specifications section is empty")

    # New: product name is missing or generic
    _GENERIC_NAMES = {"item", "product", "goods", "stuff", "thing", "paninda"}
    if not product_name or len(product_name) < 5 or product_name.lower() in _GENERIC_NAMES:
        indicators.append("Product name is generic or not provided")

    # New: no description at all
    if not (listing.get("description") or "").strip():
        indicators.append("No written product description provided")

    # New: no images AND no description — neither visual nor text evidence
    image_count = listing.get("image_count") or 0
    if image_count == 0 and not (listing.get("description") or "").strip():
        indicators.append("Listing has no images and no description")

    # New: Facebook condition unknown
    if listing.get("platform") == "facebook" and not listing.get("condition"):
        indicators.append("Item condition is not specified by the seller")

    if not indicators:
        return None

    # Determine severity
    n_ind = len(indicators)
    if n_ind >= 3:
        severity = "warning"
    elif n_ind == 2:
        severity = "caution"
    else:
        severity = "info"

    # Determine title
    _INDICATOR_TITLES = {
        "Description does not mention brand, publisher, or edition": "Missing Product Information",
        "Price is below typical category baseline": "Low Price Alert",
        "Specifications section is empty": "Incomplete Product Specs",
        "Product name is generic or not provided": "Unclear Product Identity",
        "No written product description provided": "No Description Provided",
        "Listing has no images and no description": "Listing Has No Evidence",
        "Item condition is not specified by the seller": "Condition Unknown",
    }
    _NOTICE_ACTIONS_EXTENDED: Dict[str, str] = {
        **_NOTICE_ACTIONS,
        "Product name is generic or not provided": (
            "Ask the seller to confirm the exact product name, model, and brand "
            "before completing your purchase."
        ),
        "No written product description provided": (
            "Request a written description from the seller so you know exactly "
            "what you are buying."
        ),
        "Listing has no images and no description": (
            "Do not purchase without seeing photos and a written description of "
            "the actual item. Ask the seller to provide both before proceeding."
        ),
        "Item condition is not specified by the seller": (
            "Ask the seller whether the item is brand new, used, or refurbished "
            "before placing your order."
        ),
    }

    if n_ind == 1:
        title = _INDICATOR_TITLES.get(indicators[0], "Product Notice")
    elif any("evidence" in i.lower() for i in indicators):
        title = "Listing Lacks Verifiable Details"
    elif any("price" in i.lower() for i in indicators) and any("brand" in i.lower() or "name" in i.lower() for i in indicators):
        title = "Price and Identity Concerns"
    else:
        title = "Product Details to Review"

    recommended_action = next(
        (_NOTICE_ACTIONS_EXTENDED[ind] for ind in indicators if ind in _NOTICE_ACTIONS_EXTENDED),
        "Verify product details with the seller before completing your purchase.",
    )

    return {
        "title": title,
        "message": (
            "Some product attributes could not be confirmed from the listing. "
            "These are observations, not confirmed facts."
        ),
        "severity": severity,
        "indicators": indicators,
        "recommended_action": recommended_action,
        "disclaimer": (
            "All outputs are probabilistic estimates based on observable "
            "signals. Verify directly with the seller before purchasing."
        ),
    }


def platform_signals(listing: Dict) -> Dict:
    badges = listing.get("seller_badges") or []
    is_mall = bool(listing.get("is_shopee_mall") or listing.get("is_lazmall"))
    return {
        "is_mall": is_mall,
        "has_badges": bool(badges),
        "badge_list": list(badges),
    }


def build_positive_signals(listing: Dict) -> List[Dict]:
    """Return a list of positive trust signals for display alongside flags."""
    result: List[Dict] = []
    platform = (listing.get("platform") or "").lower()

    if platform == "shopee" and listing.get("is_shopee_mall"):
        result.append({
            "message": (
                "This seller is part of Shopee Mall, which requires verified "
                "business registration and meets Shopee's quality standards."
            ),
            "impact": "Seller risk contribution reduced",
        })
    if platform == "lazada" and listing.get("is_lazmall"):
        result.append({
            "message": (
                "This seller is part of LazMall, which requires verified "
                "business registration and adherence to Lazada's quality "
                "requirements."
            ),
            "impact": "Seller risk contribution reduced",
        })

    badges = listing.get("seller_badges") or []
    badge_set = {str(b).lower() for b in badges}
    if any("top seller" in b for b in badge_set):
        result.append({
            "message": (
                "The seller holds a Top Seller badge, indicating a strong "
                "track record of sales and positive buyer feedback."
            ),
            "impact": "Seller credibility indicator",
        })
    if any("preferred" in b for b in badge_set):
        result.append({
            "message": (
                "The seller has a Preferred Seller badge, which reflects "
                "consistent performance on this platform."
            ),
            "impact": "Seller credibility indicator",
        })

    return result


def build_scan_completeness(confidence_pct: int) -> Dict:
    """Derive a plain-language scan completeness descriptor from confidence %."""
    if confidence_pct >= 80:
        return {
            "level": "Full",
            "description": (
                "All available listing information was retrieved and analyzed. "
                "This is the most complete assessment possible for this platform."
            ),
        }
    if confidence_pct >= 50:
        return {
            "level": "Partial",
            "description": (
                "Most listing information was retrieved but some fields were "
                "unavailable. The assessment covers the majority of available data."
            ),
        }
    return {
        "level": "Basic",
        "description": (
            "Limited listing information was available for this scan. "
            "Interpret the risk score with extra caution and consider "
            "verifying details manually."
        ),
    }


# Category-level labels and summary generators for score_breakdown_details
_BREAKDOWN_META: Dict[str, Dict] = {
    "seller_attributes": {"label": "Seller Profile", "max": 25},
    "listing_metadata":  {"label": "Listing Details", "max": 25},
    "textual_nlp":       {"label": "Description and Comments", "max": 25},
    "url_domain":        {"label": "Web Address", "max": 25},
}

# Map flag strings (substrings) to the category they belong to — for summary generation
_FLAG_CATEGORY_HINTS: Dict[str, str] = {
    "seller": "seller_attributes",
    "response rate": "seller_attributes",
    "seller rating": "seller_attributes",
    "joined": "seller_attributes",
    "account under": "seller_attributes",
    "price": "listing_metadata",
    "rating": "listing_metadata",
    "image": "listing_metadata",
    "sales": "listing_metadata",
    "condition": "listing_metadata",
    "listing posted": "listing_metadata",
    "reviews": "listing_metadata",
    "description": "textual_nlp",
    "urgency": "textual_nlp",
    "pressure": "textual_nlp",
    "caps": "textual_nlp",
    "url": "url_domain",
    "domain": "url_domain",
    "typosquat": "url_domain",
    "http": "url_domain",
}


def enriched_score_breakdown(breakdown: Dict[str, int], flags: List[str]) -> Dict:
    """Return breakdown with max, label, and a dynamic category summary."""
    # Build a set of flags per category to generate summaries
    cat_flags: Dict[str, List[str]] = {k: [] for k in breakdown}
    for flag in flags:
        fl = flag.lower()
        for hint, cat in _FLAG_CATEGORY_HINTS.items():
            if hint in fl and cat in cat_flags:
                cat_flags[cat].append(flag)
                break

    out: Dict[str, Dict] = {}
    for key, score in breakdown.items():
        meta = _BREAKDOWN_META.get(key, {"label": key.replace("_", " ").title(), "max": 25})
        triggered = cat_flags.get(key, [])
        if triggered:
            # Use the first flag's plain text as the summary, trimmed to ~80 chars
            raw = triggered[0]
            summary = raw if len(raw) <= 80 else raw[:77] + "..."
        else:
            summary = "No risk signals detected in this area."
        out[key] = {
            "score": score,
            "max": meta["max"],
            "label": meta["label"],
            "summary": summary,
        }
    return out
