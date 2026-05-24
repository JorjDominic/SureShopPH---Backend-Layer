"""Integration tests for the listing analyzer pipeline."""
from app.services.analyzer import analyze_listing_payload


_BASE = {
    "platform": "shopee",
    "seller_name": "TestSeller",
    "shop_age": "2 years",
    "response_rate": 95,
    "rating": 4.5,
    "rating_count": 200,
    "image_count": 5,
    "price": 500,
    "description": "Quality product, fast shipping.",
    "sold_count": 100,
    "url": "https://shopee.ph/product/123",
}


def test_returns_required_keys():
    result = analyze_listing_payload(_BASE)
    for key in ("risk_score", "risk_level", "risk_color", "flags",
                "confidence", "score_breakdown", "scan_timestamp"):
        assert key in result


def test_score_in_valid_range():
    result = analyze_listing_payload(_BASE)
    assert 0 <= result["risk_score"] <= 100


def test_mall_does_not_increase_score():
    mall = {**_BASE, "is_shopee_mall": True}
    assert analyze_listing_payload(mall)["risk_score"] <= analyze_listing_payload(_BASE)["risk_score"]


def test_new_seller_higher_risk():
    new = {**_BASE, "shop_age": "recently joined"}
    old = {**_BASE, "shop_age": "3 years"}
    assert analyze_listing_payload(new)["risk_score"] > analyze_listing_payload(old)["risk_score"]


def test_empty_payload_does_not_raise():
    result = analyze_listing_payload({"platform": "shopee"})
    assert 0 <= result["risk_score"] <= 100


def test_low_field_confidence_does_not_increase_score():
    low_conf = {**_BASE, "data_quality": {
        "missing": [],
        "field_confidence": {
            "shop_age": "low",
            "response_rate": "low",
            "seller_name": "low",
        },
    }}
    normal = analyze_listing_payload(_BASE)["risk_score"]
    low = analyze_listing_payload(low_conf)["risk_score"]
    # Low confidence dampens the contribution of those fields, so the score
    # must not exceed the normal score (allow tiny rounding tolerance).
    assert low <= normal + 2


def test_facebook_listing_runs():
    fb = {
        "platform": "facebook",
        "description": "iPhone for sale",
        "price": 5000,
        "condition": "used",
        "url": "https://facebook.com/marketplace/item/123",
    }
    result = analyze_listing_payload(fb)
    assert result["risk_level"] in ("Very Low", "Low", "Medium", "High", "Very High")
