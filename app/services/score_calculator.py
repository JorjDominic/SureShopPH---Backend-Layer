"""Final score assembly — bands, color, message, product notice."""
from __future__ import annotations
from typing import Dict, List, Tuple

from app.config import RISK_BANDS
from app.services.rule_engine import _EVASIVE_DESC_RE


def band(score: int) -> Tuple[str, str]:
    for lo, hi, level, color in RISK_BANDS:
        if lo <= score <= hi:
            return level, color
    return "Very Low", "green"


def risk_message(level: str) -> str:
    return {
        "Very Low": (
            "No strong risk signals detected. Standard buying caution applies."
        ),
        "Low": (
            "Minor observable signals detected. Review the indicators and "
            "proceed with your own judgment."
        ),
        "Medium": (
            "Multiple observable signals detected. Consider verifying key "
            "details with the seller before purchasing."
        ),
        "High": (
            "Several high-weight signals detected. Take time to review all "
            "indicators carefully before making any payment."
        ),
        "Very High": (
            "Strong risk signals detected across multiple categories. Do not "
            "proceed with payment until you have independently verified the "
            "seller and listing details."
        ),
    }.get(level, "")


def closing_line(level: str) -> str:
    """Single takeaway action line shown at the bottom of the result card."""
    return {
        "Very Low": (
            "No strong risk signals detected. Standard buying caution still applies."
        ),
        "Low": (
            "Minor observable signals were detected. Review the indicators above "
            "and proceed with your own judgment."
        ),
        "Medium": (
            "Multiple observable signals were detected. Consider verifying key "
            "details with the seller before buying."
        ),
        "High": (
            "Several high-weight signals were detected. Take time to carefully "
            "review all indicators above before completing any payment."
        ),
        "Very High": (
            "Strong risk signals were detected across multiple categories. "
            "Do not proceed with payment until you have independently verified "
            "the seller and listing details through the platform's official channels."
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

# Category-specific recommended actions for low price alerts
_CATEGORY_ACTIONS: Dict[str, List[str]] = {
    "electronics": [
        "Ask the seller whether the item comes with a warranty and what it covers.",
        "Confirm whether the original box, accessories, and documentation are included.",
        "Request additional photos showing the actual unit, especially ports and labels.",
        "Ask whether the item is brand new, refurbished, or open-box.",
    ],
    "books": [
        "Ask the seller about the edition and publisher, and whether it is an original print or reprint.",
        "Confirm whether the item is new or used and whether all pages are intact.",
        "Request a photo of the title page and copyright information to verify the edition.",
    ],
    "clothing": [
        "Ask the seller to confirm the brand authenticity and whether original tags and packaging are included.",
        "Request measurements or a size chart to confirm the item will fit correctly.",
        "Ask for photos of the actual item showing brand labels and stitching detail.",
    ],
    "general": [
        "Ask the seller about the item's condition — whether it is brand new, used, or refurbished.",
        "Request photos of the actual item rather than stock images.",
        "Confirm exactly what is included in the listing before completing your purchase.",
    ],
}

_ELECTRONICS_KW = {
    "phone", "laptop", "tablet", "headphone", "earphone", "earbuds", "charger", "cable",
    "keyboard", "mouse", "monitor", "speaker", "camera", "smartwatch", "router",
    "powerbank", "power bank", "gadget", "electronic", "appliance", "aircon",
    "refrigerator", "television", " tv", "tv ", "printer", "projector",
}
_BOOKS_KW = {
    "book", "novel", "textbook", "isbn", "author", "publisher", "edition",
    "paperback", "hardcover", "manga", "komik", "journal", "workbook",
}
_CLOTHING_KW = {
    "shirt", "dress", "pants", "jeans", "jacket", "shoes", "sneakers", "sandals",
    "bag", "tote", "backpack", "wallet", "blouse", "skirt", "polo", "shorts",
    "hoodie", "sweatshirt", "cap", "hat", "watch", "jewelry", "bracelet",
    "necklace", "ring",
}

_GENERIC_NO_BRAND_EXPECTED_KW = {
    "charger", "cable", "adapter", "case", "cover", "protector", "holder",
    "stand", "strap", "sticker", "clip", "pouch", "sleeve",
}


def _detect_product_category(product_name: str, description: str) -> str:
    """Roughly classify the product for context-aware recommended actions."""
    combined = (product_name + " " + description).lower()
    if any(kw in combined for kw in _ELECTRONICS_KW):
        return "electronics"
    if any(kw in combined for kw in _BOOKS_KW):
        return "books"
    if any(kw in combined for kw in _CLOTHING_KW):
        return "clothing"
    return "general"


def _generic_no_brand_expected(product_name: str) -> bool:
    normalized_name = product_name.lower().strip()
    return any(kw in normalized_name for kw in _GENERIC_NO_BRAND_EXPECTED_KW)


def build_product_notice(listing: Dict, breakdown: Dict[str, int]) -> Dict | None:
    desc = (listing.get("description") or "").lower()
    product_name = (listing.get("product_name") or "").strip()
    indicators: List[str] = []
    category = _detect_product_category(product_name, desc)
    brand_expected = category in {"electronics", "books", "clothing"} and not _generic_no_brand_expected(product_name)

    if brand_expected and len(desc) > 20 and not any(k in desc for k in PRODUCT_KEYWORDS):
        indicators.append("Description does not mention brand, publisher, or edition")

    price = listing.get("price")
    if isinstance(price, (int, float)) and 0 < price < 200 and brand_expected:
        indicators.append("Price is below typical category baseline")

    if listing.get("platform") in ("shopee", "lazada") and listing.get("specifications") is None and brand_expected:
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
            "Consider requesting photos and a written description of the actual "
            "item from the seller before proceeding."
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

    # Category-aware recommended_actions list for low-price listings
    has_low_price = any("price" in i.lower() for i in indicators)
    recommended_actions = list(_CATEGORY_ACTIONS.get(category, _CATEGORY_ACTIONS["general"])) \
        if has_low_price else [recommended_action]

    return {
        "title": title,
        "message": (
            "Some product attributes could not be confirmed from the listing. "
            "These are observations, not confirmed facts."
        ),
        "severity": severity,
        "indicators": indicators,
        "recommended_action": recommended_action,
        "recommended_actions": recommended_actions,
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

    # --- Platform verification badges ---
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

    # --- Seller profile data present ---
    if listing.get("seller_name"):
        result.append({
            "message": "Seller name is available and was retrieved successfully.",
            "impact": "Seller identity verifiable",
        })

    shop_age_days = None
    _sa = listing.get("shop_age")
    if _sa:
        # Rough parse — mirrors rule_engine._parse_shop_age_days logic
        import re as _re
        _s = str(_sa).lower()
        _days = 0
        m_y = _re.search(r"(\d+)\s*year", _s)
        m_mo = _re.search(r"(\d+)\s*month", _s)
        m_d = _re.search(r"(\d+)\s*day", _s)
        if m_y:  _days += int(m_y.group(1)) * 365
        if m_mo: _days += int(m_mo.group(1)) * 30
        if m_d:  _days += int(m_d.group(1))
        if _days > 0:
            shop_age_days = _days

    if shop_age_days is not None and shop_age_days >= 180:
        years = shop_age_days // 365
        months = (shop_age_days % 365) // 30
        if years >= 1:
            age_label = f"{years} year{'s' if years > 1 else ''}"
        else:
            age_label = f"{months} month{'s' if months > 1 else ''}"
        result.append({
            "message": f"Seller account has been active for {age_label}, indicating an established presence.",
            "impact": "Seller longevity confirmed",
        })

    if platform == "shopee":
        rr = listing.get("response_rate")
        if rr is not None:
            try:
                rr_val = float(str(rr).rstrip("%"))
                if rr_val >= 80:
                    result.append({
                        "message": f"Seller has a {int(rr_val)}% response rate, indicating reliable buyer communication.",
                        "impact": "Seller responsiveness confirmed",
                    })
            except (ValueError, TypeError):
                pass

    if platform == "lazada":
        sr = listing.get("seller_rating")
        if sr is not None:
            try:
                sr_val = float(str(sr).rstrip("%"))
                if sr_val >= 90:
                    result.append({
                        "message": f"Seller has a {int(sr_val)}% seller rating on Lazada, reflecting strong buyer satisfaction.",
                        "impact": "High seller rating",
                    })
            except (ValueError, TypeError):
                pass

    # --- Listing data completeness ---
    rating = listing.get("rating")
    rating_count = listing.get("rating_count")
    try:
        rc_int = int(rating_count) if rating_count is not None else 0
    except (ValueError, TypeError):
        rc_int = 0

    if rating and isinstance(rating, (int, float)) and rating > 0 and rc_int > 0:
        if rc_int >= 100:
            result.append({
                "message": f"Product has {rc_int:,} buyer ratings with an average of {rating:.1f} stars — strong buyer history.",
                "impact": "Verified purchase history",
            })
        elif rc_int >= 10:
            result.append({
                "message": f"Product has {rc_int} buyer ratings with an average of {rating:.1f} stars.",
                "impact": "Buyer ratings present",
            })

    sold_raw = listing.get("sold_count")
    if sold_raw is not None:
        try:
            _s_str = str(sold_raw).lower().replace("+", "").replace(",", "")
            if _s_str.endswith("k"):
                sold_int = int(float(_s_str[:-1]) * 1000)
            else:
                sold_int = int(float(_s_str))
            if sold_int >= 100:
                result.append({
                    "message": f"Listing shows {sold_raw}+ recorded sales, confirming active buyer transactions.",
                    "impact": "Sales history present",
                })
        except (ValueError, TypeError):
            pass

    desc = (listing.get("description") or "").strip()
    # A description qualifies as a positive signal only if it has real content:
    # it must be long enough to be meaningful, not a fallback message, and not
    # primarily a price-evasion phrase (e.g. "kayo na bahala mag price / pm nalang").
    if (
        len(desc) >= 80
        and not desc.startswith("No ")
        and not _EVASIVE_DESC_RE.search(desc)
    ):
        result.append({
            "message": "Product description is present and provides details about the item.",
            "impact": "Listing transparency",
        })

    image_count = listing.get("image_count") or 0
    if image_count >= 3:
        result.append({
            "message": f"{image_count} product image{'s' if image_count != 1 else ''} detected — visual evidence of the item is available.",
            "impact": "Listing has product photos",
        })

    if platform in ("shopee", "lazada") and listing.get("specifications"):
        result.append({
            "message": "Product specifications section is present, providing verifiable item details.",
            "impact": "Specifications available",
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
    "price transparency": "listing_metadata",
    "platform buyer protection": "listing_metadata",
    "rating coverage": "listing_metadata",
    "response time is slow": "seller_attributes",
    "soft persuasion": "textual_nlp",
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
