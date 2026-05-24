"""Tests for the centralized risk-band thresholds."""
from app.services.score_calculator import band, risk_message, build_product_notice


def test_band_very_high_range():
    assert band(85)[0] == "Very High"
    assert band(90)[0] == "Very High"
    assert band(100)[0] == "Very High"


def test_band_high_range():
    assert band(70)[0] == "High"
    assert band(76)[0] == "High"
    assert band(84)[0] == "High"


def test_band_medium_range():
    assert band(40)[0] == "Medium"
    assert band(55)[0] == "Medium"
    assert band(69)[0] == "Medium"


def test_band_low_range():
    assert band(20)[0] == "Low"
    assert band(30)[0] == "Low"
    assert band(39)[0] == "Low"


def test_band_very_low_range():
    assert band(0)[0] == "Very Low"
    assert band(10)[0] == "Very Low"
    assert band(19)[0] == "Very Low"


def test_band_returns_color():
    assert band(90)[1] == "dark-red"
    assert band(75)[1] == "red"
    assert band(55)[1] == "orange"
    assert band(30)[1] == "yellow"
    assert band(10)[1] == "green"


def test_risk_message_all_levels_non_empty():
    for level in ("Very Low", "Low", "Medium", "High", "Very High"):
        msg = risk_message(level)
        assert isinstance(msg, str) and len(msg) > 10


def test_risk_message_probabilistic_framing():
    very_low = risk_message("Very Low").lower()
    high = risk_message("High").lower()
    assert "no strong risk signals" in very_low
    assert "legitimate seller" not in very_low
    assert "several high-weight signals" in high


def test_product_notice_not_triggered_for_generic_item_without_brand():
    notice = build_product_notice(
        {
            "platform": "shopee",
            "product_name": "Phone Charger",
            "description": "Fast delivery and good quality charger for daily use",
            "price": 150,
            "image_count": 2,
        },
        {
            "seller_attributes": 0,
            "listing_metadata": 0,
            "textual_nlp": 0,
            "url_domain": 0,
        },
    )
    assert notice is None


def test_product_notice_triggered_for_low_price_electronics_without_brand():
    notice = build_product_notice(
        {
            "platform": "shopee",
            "product_name": "Wireless Earbuds",
            "description": "Compact earbuds with charging case included",
            "price": 150,
            "image_count": 2,
        },
        {
            "seller_attributes": 0,
            "listing_metadata": 0,
            "textual_nlp": 0,
            "url_domain": 0,
        },
    )
    assert notice is not None
    assert "Price is below typical category baseline" in notice["indicators"]
