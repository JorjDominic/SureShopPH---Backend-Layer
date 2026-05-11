"""calamanCy NLP engine with regex fallback for the 4 pattern categories."""
from __future__ import annotations
from typing import Dict
import re

from app.services.rule_engine import (
    URGENCY_PATTERNS, PROMISE_PATTERNS, PAYMENT_PATTERNS, VAGUE_PATTERNS,
)

_nlp = None
_load_attempted = False


def _try_load():
    global _nlp, _load_attempted
    if _load_attempted:
        return
    _load_attempted = True
    try:
        import calamancy  # type: ignore
        # calamancy.load() downloads the model automatically on first use
        _nlp = calamancy.load("tl_calamancy_md-0.2.0")
    except Exception:
        _nlp = None


def detect_patterns(text: str) -> Dict[str, object]:
    """Return which of the 4 pattern categories appear in text, plus the first
    matched phrase for each category (used as `triggered_by` in flag details)."""
    empty: Dict[str, object] = {
        "urgency": False, "promise": False, "payment": False, "vague": False,
        "urgency_match": None, "promise_match": None,
        "payment_match": None, "vague_match": None,
    }
    if not text:
        return empty

    _try_load()

    # Whether or not the calamanCy model loaded, we still run regex —
    # the model is mainly used for tokenization/lemmatization context.
    # If loaded we lemmatize tokens to widen matches.
    haystack = text
    if _nlp is not None:
        try:
            doc = _nlp(text)
            haystack = " ".join([t.lemma_.lower() for t in doc]) + " " + text.lower()
        except Exception:
            haystack = text

    def first_match(patterns) -> str | None:
        for p in patterns:
            m = re.search(p, haystack, flags=re.IGNORECASE)
            if m:
                return m.group(0)
        return None

    u = first_match(URGENCY_PATTERNS)
    pr = first_match(PROMISE_PATTERNS)
    pa = first_match(PAYMENT_PATTERNS)
    v = first_match(VAGUE_PATTERNS)

    return {
        "urgency": u is not None,
        "promise": pr is not None,
        "payment": pa is not None,
        "vague": v is not None,
        "urgency_match": u,
        "promise_match": pr,
        "payment_match": pa,
        "vague_match": v,
    }
