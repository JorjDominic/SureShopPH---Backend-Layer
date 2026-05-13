"""Unit tests for the rule-based scoring helpers and category scorers."""
from app.services.rule_engine import (
    score_seller, score_metadata, score_text,
    _parse_shop_age_days, _parse_percent, _parse_sold_count,
)


# ────────────────── Helpers ──────────────────

def test_parse_shop_age_recently_joined():
    assert _parse_shop_age_days("recently joined") == 0


def test_parse_shop_age_years():
    assert _parse_shop_age_days("2 years") == 730


def test_parse_shop_age_months():
    assert _parse_shop_age_days("3 months") == 90


def test_parse_shop_age_weeks():
    assert _parse_shop_age_days("2 weeks") == 14


def test_parse_shop_age_days_only():
    assert _parse_shop_age_days("45 days") == 45


def test_parse_shop_age_combined():
    # 1 year (365) + 2 months (60) = 425
    assert _parse_shop_age_days("1 year 2 months") == 425


def test_parse_shop_age_none_inputs():
    assert _parse_shop_age_days(None) is None
    assert _parse_shop_age_days("") is None
    assert _parse_shop_age_days("unknown timing") is None


def test_parse_percent_float():
    assert _parse_percent(95.5) == 95.5


def test_parse_percent_string():
    assert _parse_percent("95%") == 95.0


def test_parse_percent_none_or_garbage():
    assert _parse_percent(None) is None
    assert _parse_percent("not-a-number") is None


def test_parse_sold_count_int():
    assert _parse_sold_count(100) == 100


def test_parse_sold_count_k_suffix():
    assert _parse_sold_count("1.5k") == 1500


def test_parse_sold_count_plus_and_commas():
    assert _parse_sold_count("1,200+") == 1200


def test_parse_sold_count_none():
    assert _parse_sold_count(None) is None


# ────────────────── score_seller ──────────────────

def test_score_seller_no_name_adds_points():
    score, flags = score_seller({"platform": "shopee"})
    assert score > 0
    assert any("seller name" in f.lower() for f in flags)


def test_score_seller_mall_reduces_score():
    normal, _ = score_seller({"platform": "shopee", "seller_name": "X"})
    mall, _ = score_seller({"platform": "shopee", "seller_name": "X", "is_shopee_mall": True})
    assert mall <= normal


def test_score_seller_recently_joined():
    score, flags = score_seller({
        "platform": "shopee", "seller_name": "X", "shop_age": "recently joined",
    })
    assert score > 0
    assert any("recently joined" in f.lower() for f in flags)


def test_score_seller_capped_at_25():
    score, _ = score_seller({
        "platform": "shopee", "shop_age": "recently joined", "response_rate": 5,
    })
    assert score <= 25


def test_score_seller_low_response_rate():
    _, flags = score_seller({
        "platform": "shopee", "seller_name": "X", "response_rate": 30,
    })
    assert any("response rate" in f.lower() for f in flags)


# ────────────────── score_metadata ──────────────────

def test_score_metadata_no_images():
    score, flags = score_metadata({"platform": "shopee", "image_count": 0})
    assert score > 0
    assert any("image" in f.lower() for f in flags)


def test_score_metadata_perfect_rating_few_reviews():
    _, flags = score_metadata({
        "platform": "shopee", "rating": 5.0, "rating_count": 3,
    })
    assert any("perfect rating" in f.lower() for f in flags)


def test_score_metadata_zero_sales():
    _, flags = score_metadata({"platform": "shopee", "sold_count": 0})
    assert any("zero" in f.lower() for f in flags)


def test_score_metadata_capped_at_25():
    score, _ = score_metadata({
        "platform": "shopee", "price": 0, "rating": 1.0, "image_count": 0,
    })
    assert score <= 25


# ────────────────── score_text ──────────────────

def test_score_text_urgency_phrase():
    score, flags, _ = score_text({
        "platform": "shopee",
        "description": "Limited stocks! Bili na!",
    })
    assert score > 0
    assert any("urgency" in f.lower() for f in flags)


def test_score_text_promise_phrase():
    score, _, _tb = score_text({
        "platform": "shopee",
        "description": "100% legit, guaranteed authentic po",
    })
    assert score > 0


def test_score_text_payment_phrase():
    score, _, _tb = score_text({
        "platform": "facebook",
        "description": "GCash only, no refund",
    })
    assert score > 0


def test_score_text_clean_description():
    score, _, _tb = score_text({
        "platform": "shopee",
        "description": "Quality product. Brand new with manufacturer warranty.",
    })
    # Clean copy should score very low compared to scam-y descriptions
    assert score < 10


def test_score_text_taglish_urgency_and_promise():
    score, flags, _tb = score_text({
        "platform": "shopee",
        "description": "Legit po ito! Bili na bago maubusan!",
    })
    assert score >= 20
    assert any("urgency" in f.lower() for f in flags)
    assert any("over-promising" in f.lower() for f in flags)


def test_score_metadata_facebook_auto_generated_pattern():
    score, flags = score_metadata({
        "platform": "facebook",
        "description": "Condition: New",
        "listing_date": "2 hours ago",
        "condition": None,
        "image_count": 0,
    })
    assert score > 0
    assert any("auto-generated" in f.lower() for f in flags)
