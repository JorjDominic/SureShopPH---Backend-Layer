"""Rule-based risk scoring across the four categories."""
from __future__ import annotations
import re
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse

from app.config import DEFAULT_PRICE_BASELINE


# ---------- Helpers ----------

def _parse_shop_age_days(shop_age: str | None) -> int | None:
    """Approximate shop age in days from a free-form string.

    Recognized units: years (~365d), months (~30d), weeks (7d), days.
    Returns None when the string carries no recognizable duration.
    """
    if not shop_age:
        return None
    s = shop_age.lower().strip()
    if "recently joined" in s or "new seller" in s:
        return 0
    days = 0
    m_y = re.search(r"(\d+)\s*year", s)
    m_mo = re.search(r"(\d+)\s*month", s)
    m_w = re.search(r"(\d+)\s*week", s)
    m_d = re.search(r"(\d+)\s*day", s)
    if m_y:
        days += int(m_y.group(1)) * 365
    if m_mo:
        days += int(m_mo.group(1)) * 30
    if m_w:
        days += int(m_w.group(1)) * 7
    if m_d:
        days += int(m_d.group(1))
    if days == 0 and not (m_y or m_mo or m_w or m_d):
        return None
    return days


def _parse_percent(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().rstrip("%").strip()
    try:
        return float(s)
    except ValueError:
        return None


def _parse_sold_count(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    s = str(value).strip().lower().replace("+", "").replace(",", "")
    if not s:
        return None
    try:
        if s.endswith("k"):
            return int(float(s[:-1]) * 1000)
        if s.endswith("m"):
            return int(float(s[:-1]) * 1_000_000)
        return int(float(s))
    except ValueError:
        return None


def _looks_auto_generated_facebook_description(description: str) -> bool:
    if not description:
        return False
    text = description.strip().lower()
    patterns = [
        r"^listed\s+\d+",
        r"^condition\s*:\s*\w+[\w\s-]*$",
        r"^location\s*:\s*.+$",
        r"^\[details\]$",
        r"^condition\s*:\s*\w+[\w\s-]*\s*[|,-]\s*location\s*:",
    ]
    return any(re.search(pattern, text) for pattern in patterns)


# Matches explicit prices written in descriptions (e.g. "₱2,500", "PHP 1500", "2500 pesos").
# Used to recover the real price when a FB listing uses a placeholder in the price field.
_PRICE_IN_DESC_RE = re.compile(
    r"(?:₱|php)\s*([\d,]+(?:\.\d{1,2})?)"   # ₱2,500 / PHP 1500
    r"|(\d[\d,]+)\s*(?:pesos?|php)\b"         # 2500 pesos / 2,500 PHP
    r"|price\s*(?:is\s+|:\s*)(?:₱|php)?\s*([\d,]+(?:\.\d{1,2})?)",  # price: ₱2500
    re.IGNORECASE,
)


def _extract_price_from_description(desc: str) -> float | None:
    """Return the first plausible price found in free-form description text, or None."""
    if not desc:
        return None
    for m in _PRICE_IN_DESC_RE.finditer(desc):
        raw = (m.group(1) or m.group(2) or m.group(3) or "").replace(",", "")
        try:
            v = float(raw)
            if 50 < v < 5_000_000:
                return v
        except ValueError:
            pass
    return None


# Phrases that indicate a description is price-evasive rather than informative.
# Used by both the scoring penalty and the positive-signal filter.
_EVASIVE_DESC_RE = re.compile(
    r"\bpm\s+(?:na\s+lang\s+)?(?:for\s+)?(?:actual\s+)?price\b"
    r"|\bkayo\s+na\s+(?:mag[- ]?)?(?:bahala|decide|decide)\b"
    r"|\b(?:message|msg|dm|chat|inbox)\s+(?:me\s+)?(?:na\s+lang\s+)?for\s+(?:actual\s+)?price\b"
    r"|\bprice\s*[:=]\s*(?:pm|dm|tbd|neg)\b"
    r"|\bneg(?:otiable)?\s+price\b"  # "neg price" alone is fine but combined with no other info is evasive
    r"|\bprice\s+on\s+(?:pm|dm|chat|request)\b",
    re.IGNORECASE,
)


# ---------- Category 1: Seller attributes ----------

def score_seller(listing: Dict[str, Any]) -> Tuple[int, List[str]]:
    score = 0
    flags: List[str] = []
    platform = listing.get("platform")

    if not listing.get("seller_name"):
        score += 15
        flags.append("Seller name not available")

    # Profile URL not separately captured — treat absent seller_name as proxy

    days = _parse_shop_age_days(listing.get("shop_age"))
    if days is not None:
        if days == 0 and (listing.get("shop_age") or "").lower().find("recently") != -1:
            score += 15
            flags.append("Seller recently joined the platform")
        elif days < 30:
            score += 15
            flags.append("Seller account under 30 days old")
        elif days < 90:
            score += 8
            flags.append("Seller account under 90 days old")

    if platform == "shopee":
        rr = _parse_percent(listing.get("response_rate"))
        if rr is not None:
            if rr < 50:
                score += 10
                flags.append("Very low seller response rate")
            elif rr < 80:
                score += 5
                flags.append("Below-average seller response rate")

    if platform == "lazada":
        sr = _parse_percent(listing.get("seller_rating"))
        if sr is not None:
            if sr < 70:
                score += 15
                flags.append("Very low seller rating")
            elif sr < 85:
                score += 8
                flags.append("Below-average seller rating")
        else:
            score += 6
            flags.append("Seller rating could not be retrieved")

    # Positive signals — reduce
    if platform == "shopee" and listing.get("is_shopee_mall"):
        score -= 10
    if platform == "lazada" and listing.get("is_lazmall"):
        score -= 10
    badges = listing.get("seller_badges") or []
    badge_set = {str(b).lower() for b in badges}
    if any("lazmall" in b for b in badge_set):
        score -= 10
    if any("top seller" in b for b in badge_set):
        score -= 5
    if any("preferred" in b for b in badge_set):
        score -= 5

    # Shopee: seller profile unverifiable — only the name is known, no account
    # age or response rate, and no platform badge to confirm their standing.
    # Excludes verified/mall/preferred sellers whose details are simply not
    # surfaced on the product page.
    has_positive_badge = (
        listing.get("is_shopee_mall")
        or any(b in badge_set for b in ("preferred", "top seller", "lazmall"))
    )
    if (
        platform == "shopee"
        and listing.get("seller_name")
        and listing.get("shop_age") is None
        and listing.get("response_rate") is None
        and not has_positive_badge
    ):
        score += 6
        flags.append("Seller account age and response rate not visible")

    # Slow response time despite no other positive signals
    rt = str(listing.get("response_time") or "").lower()
    if re.search(r"\b(few\s+days?|within\s+a\s+week|week|month|rarely|seldom)\b", rt):
        score += 5
        flags.append("Seller response time is slow")

    # Seller name anomaly — random digits or throwaway pattern
    _sname = listing.get("seller_name") or ""
    if _sname and len(_sname) >= 3:
        _digit_ratio = sum(c.isdigit() for c in _sname) / len(_sname)
        if _digit_ratio > 0.5 or re.match(r'^[a-zA-Z]+_?\d{4,}$', _sname):
            score += 5
            flags.append("Seller name appears auto-generated or throwaway")

    score = max(0, min(score, 25))
    return score, flags


# ---------- Category 2: Listing metadata ----------

def score_metadata(listing: Dict[str, Any]) -> Tuple[int, List[str]]:
    score = 0
    flags: List[str] = []
    platform = listing.get("platform")

    price = listing.get("price")
    if price == 0 or price == 0.0:
        # Distinguish "free" — Shopee/Lazada normalize free to 0; FB has price=0 if free
        desc = (listing.get("description") or "").lower()
        if "free" not in desc:
            score += 8
            flags.append("Price reported as 0 without 'free' indication")

    if platform in ("shopee", "lazada") and isinstance(price, (int, float)) and price is not None and 0 < price < 50:
        score += 10
        flags.append("Price unusually low compared to typical market")

    if platform in ("shopee", "lazada"):
        rating = listing.get("rating")
        rating_count = listing.get("rating_count")
        no_rating = (rating is None or rating == 0.0) and (rating_count is None or rating_count == 0)
        if no_rating:
            _sold_peek = _parse_sold_count(listing.get("sold_count"))
            if _sold_peek and _sold_peek > 100:
                # Large sold count but zero ratings — likely an extraction failure
                # rather than genuine suppression. Flag softly so the score isn't
                # artificially inflated by bad selector output.
                score += 6
                flags.append("Rating data could not be retrieved — listing has recorded sales")
            elif _sold_peek and _sold_peek > 0:
                # Has sales but zero ratings — more suspicious than no activity at all.
                score += 22
                flags.append("Has recorded sales but no buyer ratings — unusual pattern")
            else:
                score += 14
                flags.append("Product has no ratings yet")
        elif rating == 5.0 and isinstance(rating_count, int) and rating_count < 10:
            score += 15
            flags.append("Perfect rating with very few reviews")
        elif isinstance(rating, (int, float)):
            if rating < 3.5:
                score += 15
                flags.append("Low average rating")
            elif rating < 4.0:
                score += 8
                flags.append("Below-average rating")

        sold = _parse_sold_count(listing.get("sold_count"))
        # Use rating_count as a proxy when sold_count is missing/zero —
        # if buyers left ratings, sales clearly happened.
        _rc_raw = listing.get("rating_count")
        try:
            _rc = int(_rc_raw) if _rc_raw is not None else 0
        except (ValueError, TypeError):
            _rc = 0
        if sold == 0:
            if _rc > 0:
                score += 3
                flags.append("Sold count unavailable — buyer ratings suggest purchases have occurred")
            else:
                score += 10
                flags.append("Zero recorded sales")
        elif sold is None:
            if _rc > 0:
                score += 3
                flags.append("Sold count unavailable — buyer ratings suggest purchases have occurred")
            else:
                score += 8
                flags.append("No items sold on this listing")

        # Sold/rating mismatch — many sales but almost no ratings suggests
        # ratings were suppressed, reset, or the listing is a shell.
        rating_count = listing.get("rating_count")
        if sold and sold > 500 and rating_count is not None:
            try:
                coverage = int(rating_count) / sold
                if coverage < 0.01:
                    score += 10
                    flags.append("Very few ratings relative to sales volume")
                elif coverage < 0.03 and sold > 1000:
                    score += 5
                    flags.append("Unusually low rating coverage for sales volume")
            except (ValueError, ZeroDivisionError, TypeError):
                pass

    if platform == "facebook":
        # Platform baseline — FB has no buyer protection, no escrow, no verified sellers.
        # Elevated to reflect the structural lack of safeguards vs. Shopee/Lazada.
        score += 20
        flags.append("Facebook Marketplace: no platform buyer protection or seller verification")

        if listing.get("price_is_variant"):
            score += 5
            flags.append("Price shown as a variant range")
        if not listing.get("condition"):
            score += 5
            flags.append("Item condition not specified")
        listing_date = (listing.get("listing_date") or "").lower()
        if any(k in listing_date for k in ["minute", "hour", "just now"]) and "day" not in listing_date:
            score += 8
            flags.append("Listing posted very recently (under 24h)")
        desc = listing.get("description") or ""
        if _looks_auto_generated_facebook_description(desc):
            score += 8
            flags.append("Description appears auto-generated only")

        # PM-for-price / hidden actual price — seller explicitly routes price to DMs.
        # Uses the shared _EVASIVE_DESC_RE which also covers Filipino phrasing.
        if desc and _EVASIVE_DESC_RE.search(desc):
            score += 8
            flags.append(
                "Price Transparency Risk: listing instructs buyer to message for actual price — listed price may not reflect true cost"
            )

        # Price transparency — placeholder / bait prices common on FB Marketplace.
        # Before checking placeholders, try to recover the real price from the
        # description text (sellers often write "₱2,500" in the description while
        # using ₱1 as a placeholder in the price field).
        _effective_price = price
        if desc:
            _desc_price = _extract_price_from_description(desc)
            if _desc_price:
                _effective_price = _desc_price

        # Uses obvious anomaly detection only; avoids strong fraud claims.
        if _effective_price is not None and isinstance(_effective_price, (int, float)) and _effective_price > 0:
            try:
                _p = str(int(float(_effective_price)))
            except (ValueError, TypeError):
                _p = ""
            if _p:
                if int(_p) <= 10:
                    score += 6
                    flags.append(
                        "Price Transparency Risk: price appears too low to be real and may be a placeholder — confirm actual price with seller"
                    )
                elif re.match(r'^(\d)\1+$', _p):
                    score += 8
                    flags.append(
                        "Price Transparency Risk: repeated-digit price pattern may indicate a placeholder — confirm actual price with seller"
                    )
                elif _p in ("123", "1234", "12345", "123456", "1234567"):
                    score += 8
                    flags.append(
                        "Price Transparency Risk: sequential-digit price may indicate a placeholder — confirm actual price with seller"
                    )
                elif _effective_price >= 1_000_000:
                    score += 8
                    flags.append(
                        "Price Transparency Risk: listed price is unusually high for a marketplace listing — confirm actual price with seller"
                    )

    score = max(0, min(score, 25))
    return score, flags


# ---------- Category 3: Textual NLP (rule layer) ----------

URGENCY_PATTERNS = [
    r"\blimited\s+stocks?\b", r"\btoday\s+only\b", r"\bbili\s+na\b", r"\bhuli na\b",
    r"\blast\s+\d+\b", r"\brush\b", r"\bhurry\b", r"\bact\s+now\b",
    # Filipino scarcity / urgency phrases
    r"\bkunin\s+na\b", r"\bpaubos\s+na\b", r"\blast\s+piece\b", r"\bfew\s+left\b",
    r"\bsale\s+na\b", r"\bsale\s+ends?\b", r"\bflash\s+sale\b", r"\blimitado\b",
    r"\bhuling\s+(?:piraso|stock)\b", r"\bsolid\s+na\b", r"\blimited\s+na\b",
    r"\bkonti\s+na\s+lang\b", r"\bmaubusan\b", r"\bmabilis\s+maubos\b",
    # Price-bait and time-pressure additions
    r"\bpresyo\s+na\s+ito\b", r"\bsulit\s+na\s+sulit\b",
    r"\bhindi\s+na\s+mababawasan\b", r"\bbest\s+price\b",
    r"\bfor\s+today\s+only\b", r"\bpromo\s+price\b", r"\bdeal\s+of\s+the\s+day\b",
    r"\bhuling\s+araw\b", r"\bsale\s+hanggang\b",
]
PROMISE_PATTERNS = [
    r"\b100\s*%\s*legit\b", r"\bguaranteed\b", r"\bno\s+issues?\b",
    r"\boriginal\s*na\s*original\b", r"\bauthentic\s*po\b",
    # Over-promising phrases
    r"\boriginal\s+talaga\b", r"\bcertified\s+original\b", r"\bseal[ed]*\b",
    r"\bbrand\s+new\s+sealed\b", r"\b100%\s*original\b", r"\blegit\s+seller\b",
    r"\btested\s+and\s+working\b", r"\bno\s+defect\b", r"\bperfect\s+condition\b",
    r"\btotoo\s+na\b", r"\boriginal\s+brand\b", r"\blegit\s+po\b",
    r"\blegit\s+talaga\b", r"\b200%\s*legit\b", r"\bproven\s+quality\b",
    # Brand impersonation / fake authority signals
    r"\bofficial\s+store\b", r"\bauthorized\s+reseller\b",
    r"\bdirect\s+from\s+(?:supplier|factory|manufacturer|china)\b",
    r"\bimported\s+from\b", r"\bsame\s+as\s+(?:original|branded)\b",
    r"\bhigh\s+(?:copy|replica|class\s+a)\b", r"\b1:1\s*(?:copy|replica)?\b",
]
PAYMENT_PATTERNS = [
    r"\bcod\s+only\b", r"\bgcash\s+muna\b", r"\bno\s+returns?\b",
    r"\bnon[-\s]?refundable\b", r"\bdownpayment\s+first\b", r"\bpaid\s+upfront\b",
    # Additional off-platform / pressure payment phrases
    r"\bfull\s+payment\s+(?:muna|first|required)\b", r"\bno\s+cod\b",
    r"\bcash\s+basis\b", r"\bmeet\s*up\s+(?:only|muna|lang)\b",
    r"\bgcash\s+only\b", r"\bpaymaya\s+only\b", r"\bbank\s+transfer\s+(?:only|muna)\b",
    r"\bno\s+cancel\b", r"\bno\s+refund\b", r"\bbayad\s+muna\b",
    r"\bwalang\s+cancel\b", r"\bwalang\s+returns?\b", r"\bbayad\s+agad\b",
    r"\bgcash\s+lang\b", r"\bpaymaya\s+lang\b",
]
VAGUE_PATTERNS = [
    r"\bgeneric\b", r"\bbrand\s*[:\-]?\s*none\b", r"\bno\s+brand\b",
    r"\bunbranded\b", r"\bgeneric\s+brand\b",
    # Additional vague product identity phrases
    r"\bwalang\s+brand\b", r"\bdi\s+ko\s+alam\s+brand\b",
    r"\bchinese\s+brand\b", r"\blocal\s+brand\b", r"\bno\s+name\s+brand\b",
    r"\bmurang[\s-]mura\b", r"\bbrand\?\s*hindi\s+importante\b",
]


def _matches(text: str, patterns: List[str]) -> List[str]:
    found = []
    for p in patterns:
        if re.search(p, text, flags=re.IGNORECASE):
            found.append(p)
    return found


def score_text(listing: Dict[str, Any], nlp_hits: Dict[str, object] | None = None) -> Tuple[int, List[str], Dict[str, str]]:
    """Returns (score, flags, triggered_by_map).

    triggered_by_map: flag_string -> matched phrase (only for text-based flags).
    """
    score = 0
    flags: List[str] = []
    triggered_by: Dict[str, str] = {}
    desc = listing.get("description") or ""
    platform = listing.get("platform")

    if not desc or len(desc.strip()) < 20:
        score += 10
        flags.append("Description missing or too short")
    else:
        text = desc
        # Use spaCy hits if provided, else regex fallback
        urgency = nlp_hits.get("urgency") if nlp_hits else bool(_matches(text, URGENCY_PATTERNS))
        promise = nlp_hits.get("promise") if nlp_hits else bool(_matches(text, PROMISE_PATTERNS))
        payment = nlp_hits.get("payment") if nlp_hits else bool(_matches(text, PAYMENT_PATTERNS))
        vague = nlp_hits.get("vague") if nlp_hits else bool(_matches(text, VAGUE_PATTERNS))

        if urgency:
            score += 10
            flags.append("Urgency or scarcity language detected")
            m = (nlp_hits.get("urgency_match") if nlp_hits else None) or next(
                (re.search(p, text, re.IGNORECASE) for p in URGENCY_PATTERNS if re.search(p, text, re.IGNORECASE)), None
            )
            if m:
                triggered_by["Urgency or scarcity language detected"] = m if isinstance(m, str) else m.group(0)
        if promise:
            score += 10
            flags.append("Over-promising language detected")
            m = (nlp_hits.get("promise_match") if nlp_hits else None) or next(
                (re.search(p, text, re.IGNORECASE) for p in PROMISE_PATTERNS if re.search(p, text, re.IGNORECASE)), None
            )
            if m:
                triggered_by["Over-promising language detected"] = m if isinstance(m, str) else m.group(0)
        if payment:
            score += 10
            flags.append("Pressure payment terms detected")
            m = (nlp_hits.get("payment_match") if nlp_hits else None) or next(
                (re.search(p, text, re.IGNORECASE) for p in PAYMENT_PATTERNS if re.search(p, text, re.IGNORECASE)), None
            )
            if m:
                triggered_by["Pressure payment terms detected"] = m if isinstance(m, str) else m.group(0)
        if vague:
            score += 5
            flags.append("Vague brand or publisher information")
            m = (nlp_hits.get("vague_match") if nlp_hits else None) or next(
                (re.search(p, text, re.IGNORECASE) for p in VAGUE_PATTERNS if re.search(p, text, re.IGNORECASE)), None
            )
            if m:
                triggered_by["Vague brand or publisher information"] = m if isinstance(m, str) else m.group(0)

    specs = listing.get("specifications")
    # Specs absence is surfaced as a product notice (score_calculator.py),
    # not as a scored flag — removes noise for listings that simply hide specs.

    # Contact number or payment account in description — strong off-platform solicitation signal
    _CONTACT_PATTERNS = [
        r'\b09\d{9}\b',
        r'\b\+639\d{9}\b',
        r'\bgcash\s*#?\s*:?\s*09\d{9}\b',
        r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
    ]
    if desc:
        for _cp in _CONTACT_PATTERNS:
            if re.search(_cp, desc, re.IGNORECASE):
                score += 12
                flags.append("Contact number or payment account found in description — seller may be soliciting off-platform payment")
                break

    # Brand name vs. price mismatch — premium brand mentioned but price far below typical retail
    _BRAND_FLOOR = {
        "iphone": 15000, "samsung galaxy": 5000, "dyson": 8000,
        "airpods": 3000, "macbook": 30000, "ipad": 15000,
        "ps5": 20000, "xbox": 15000, "nike": 1500, "adidas": 1200,
        "louis vuitton": 5000, "gucci": 5000, "rolex": 50000,
        # PC hardware
        "ryzen": 5000, "intel core": 7000,
        "rtx 3": 15000, "rtx 4": 25000,
        "gtx 10": 5000, "gtx 16": 8000,
        "rx 6": 10000, "rx 7": 15000,
    }
    _price = listing.get("price")
    _desc_lower = desc.lower() if desc else ""
    if isinstance(_price, (int, float)) and _price > 0 and _desc_lower:
        for _brand, _floor in _BRAND_FLOOR.items():
            if _brand in _desc_lower and _price < _floor * 0.4:
                score += 15
                flags.append(f"Brand name '{_brand}' detected but price is far below typical retail value")
                break

    # High-value item with very short description
    if isinstance(_price, (int, float)) and _price > 5000 and desc:
        if len(desc.split()) < 15:
            score += 8
            flags.append("High-value item listed with very little description")

    # Parts-out / multi-item listing — price may only cover one component
    _PARTS_OUT_RE = re.compile(
        r"\bparts?\s+out\b|\bpart-out\b|\bparting\s+out\b"
        r"|\bpor\s+parte\b"
        r"|\bselling\s+(?:by\s+)?(?:piece|parts?|separately|individually)\b",
        re.IGNORECASE,
    )
    _title_text = listing.get("title") or listing.get("product_name") or ""
    if _PARTS_OUT_RE.search(desc) or _PARTS_OUT_RE.search(_title_text):
        score += 5
        flags.append("Parts-out or multi-item listing detected — verify which items are included at this price")

    # Soft bait language — words like "sale", "legit", "below SRP" are weak on
    # their own but amplify concern when 2+ appear alongside another fired flag.
    SOFT_BAIT = [
        r"\bsale\b", r"\bbig\s+(?:sale|discount)\b", r"\bdiscounted?\b",
        r"\bbelow\s+srp\b", r"\bbelow\s+price\b", r"\bcheap\b",
        r"\bmura\b", r"\bsulit\b", r"\blegit\b", r"\bmas\s+mura\b",
    ]
    if flags and desc:
        _soft = sum(1 for p in SOFT_BAIT if re.search(p, desc, re.IGNORECASE))
        if _soft >= 2:
            score += 5
            flags.append("Soft persuasion language reinforces other risk signals in this listing")

    score = max(0, min(score, 35))
    return score, flags, triggered_by


# ---------- Category 4: URL & domain ----------

LEGIT_DOMAINS = {
    "shopee.ph", "shopee.com.ph", "lazada.com.ph", "facebook.com",
    "m.facebook.com", "web.facebook.com",
}
TYPO_PATTERNS = [
    r"shoope", r"shop+ee[a-z]", r"laz+ad+a[a-z]", r"f[a4]ceb[o0]ok",
    r"shopeephil", r"lazada-ph\.", r"sh0pee", r"lazadaa",
]


def score_url(url: str) -> Tuple[int, List[str]]:
    score = 0
    flags: List[str] = []
    if not url:
        return 0, flags

    try:
        parsed = urlparse(url)
    except Exception:
        return 25, ["Malformed URL"]

    host = (parsed.hostname or "").lower()
    scheme = (parsed.scheme or "").lower()

    # Typosquatting
    is_legit = any(host == d or host.endswith("." + d) for d in LEGIT_DOMAINS)
    if not is_legit:
        for p in TYPO_PATTERNS:
            if re.search(p, host):
                score += 25
                flags.append("Possible typosquatting domain")
                break

    if scheme and scheme != "https":
        score += 10
        flags.append("Connection is not HTTPS")

    # Subdomain depth: count labels minus base (2 labels for typical TLDs, 3 for .com.ph)
    labels = host.split(".") if host else []
    base_len = 3 if host.endswith(".com.ph") else 2
    sub_depth = max(0, len(labels) - base_len)
    if sub_depth > 2:
        score += 10
        flags.append("Unusually deep subdomain")

    score = max(0, min(score, 25))
    return score, flags
