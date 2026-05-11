"""Tests for confidence-aware scoring."""
from app.services.confidence import compute_confidence


def test_all_present_shopee_is_high():
    result = compute_confidence("shopee", [], {})
    assert result["level"] == "High"
    assert result["percentage"] == 100


def test_all_missing_shopee_is_low():
    all_fields = [
        "price", "shop_age", "rating", "rating_count", "description", "response_rate",
    ]
    result = compute_confidence("shopee", all_fields, {})
    assert result["level"] == "Low"
    assert result["fields_present"] == 0


def test_low_confidence_fields_reduce_percentage():
    all_low = {f: "low" for f in [
        "price", "shop_age", "rating", "rating_count", "description", "response_rate",
    ]}
    result = compute_confidence("shopee", [], all_low)
    assert result["percentage"] < 100


def test_partial_missing():
    result = compute_confidence("shopee", ["response_rate"], {})
    assert result["fields_present"] == 5


def test_facebook_has_fewer_fields():
    result = compute_confidence("facebook", [], {})
    assert result["total_fields"] == 4


def test_unknown_platform_graceful():
    result = compute_confidence("unknown_platform", [], {})
    assert result["total_fields"] == 0
    assert result["percentage"] == 0


def test_could_not_retrieve_populated():
    result = compute_confidence("shopee", ["price", "rating"], {})
    assert "price" in result["could_not_retrieve"]
    assert "rating" in result["could_not_retrieve"]
