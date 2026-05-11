"""Tests for the centralized risk-band thresholds."""
from app.services.score_calculator import band, risk_message


def test_band_high_range():
    assert band(76)[0] == "High"
    assert band(90)[0] == "High"
    assert band(100)[0] == "High"


def test_band_medium_range():
    assert band(51)[0] == "Medium"
    assert band(60)[0] == "Medium"
    assert band(75)[0] == "Medium"


def test_band_low_range():
    assert band(26)[0] == "Low"
    assert band(50)[0] == "Low"


def test_band_very_low_range():
    assert band(0)[0] == "Very Low"
    assert band(25)[0] == "Very Low"


def test_band_returns_color():
    assert band(90)[1] == "red"
    assert band(60)[1] == "orange"
    assert band(40)[1] == "yellow"
    assert band(10)[1] == "green"


def test_risk_message_all_levels_non_empty():
    for level in ("Very Low", "Low", "Medium", "High"):
        msg = risk_message(level)
        assert isinstance(msg, str) and len(msg) > 10
