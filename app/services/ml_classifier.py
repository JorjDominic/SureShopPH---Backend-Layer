"""Bot likelihood + fake review classifier (sklearn) with rule fallbacks."""
from __future__ import annotations
import os
import pathlib
import re
from collections import Counter
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any, Dict, List, Tuple

# Resolve relative to the project root so the path is correct regardless of
# the current working directory (Docker, tests, IDE run configs, etc.).
_BASE_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
MODEL_PATH = str(_BASE_DIR / "models" / "fake_review_model.pkl")

_model = None
_load_attempted = False


def _try_load_model():
    global _model, _load_attempted
    if _load_attempted:
        return
    _load_attempted = True
    try:
        import joblib  # type: ignore
        if os.path.exists(MODEL_PATH):
            _model = joblib.load(MODEL_PATH)
    except Exception:
        _model = None


def reload_model() -> bool:
    """Force-reload the model from disk. Returns True if loaded successfully."""
    global _model, _load_attempted
    _load_attempted = False
    _model = None
    _try_load_model()
    return _model is not None


def is_model_loaded() -> bool:
    _try_load_model()
    return _model is not None


GENERIC_PHRASES = [
    "goods", "ok", "okay", "legit", "salamat", "thank you", "nice", "good",
    "great", "recommended", "fast delivery", "as described",
    # Tagalog promotional spam phrases
    "sulit", "worth it", "panalo", "swak", "bilhin na", "mabilis dumating",
    "ganda ng quality", "highly recommend", "must buy",
    # Additional Filipino/Taglish generic phrases common in Shopee PH reviews
    "perfect", "satisfied", "no issues", "solid", "authentic", "original",
    "five stars", "5 stars", "love it", "love this", "amazing", "excellent",
    "will order again", "mag-order ulit", "maganda", "mabilis", "ang ganda",
    "as expected", "no problem", "no complaints", "super nice", "super legit",
    "ganda", "ayos", "okay lang", "ok lang", "nice naman", "legit seller",
    "fast", "legit po", "worth the price", "quality is good", "good quality",
    "product is good", "item is good", "item received", "goods received",
    "exactly as", "exactly what", "no regrets", "highly recommended",
    "best seller", "shipping was fast", "delivery was fast",
]

# Pattern for bot-style usernames: user12345, buyer_abc123, t****r
_BOT_USERNAME_RE = re.compile(r"^(user|buyer|guest|shopper)[_-]?\d{3,}$|^.\*+.$", re.IGNORECASE)


def _parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(s.strip(), fmt)
        except Exception:
            pass
    return None


def bot_likelihood(comments: List[Dict[str, Any]]) -> Tuple[float, List[str], Dict]:
    """Return (score, flags, stats).

    stats keys: duplicate_count, clustered_dates, avg_length, generic_count
    """
    flags: List[str] = []
    stats: Dict[str, Any] = {
        "duplicate_count": 0,
        "clustered_dates": False,
        "avg_length": 0.0,
        "generic_count": 0,
    }
    if not comments:
        return 0.0, flags, stats

    score = 0.0
    # Exclude placeholder text inserted by the extension when no review was written
    comments = [c for c in comments if (c.get("text") or "").strip().lower() != "(no written review)"]
    texts = [(c.get("text") or "").strip().lower() for c in comments]
    n = len(texts)
    if n == 0:
        return 0.0, flags, stats

    # Duplicate text > 85%
    if n > 0:
        most_common = Counter(texts).most_common(1)[0][1]
        dup_ratio = most_common / n
        stats["duplicate_count"] = most_common
        if dup_ratio > 0.85:
            score += 0.5
            flags.append("High duplicate-text ratio across comments")

    # Time clustering — 60-min window holds majority
    # Raised threshold from 50% → 65% to reduce false positives from same-day
    # delivery batches which are common for flash sales.
    dts = [_parse_dt(c.get("date")) for c in comments]
    dts_valid = [d for d in dts if d is not None]
    if len(dts_valid) >= 4:
        dts_valid.sort()
        for i in range(len(dts_valid)):
            window = [d for d in dts_valid if 0 <= (d - dts_valid[i]).total_seconds() <= 3600]
            if len(window) / len(dts_valid) > 0.65:
                score += 0.35
                stats["clustered_dates"] = True
                flags.append("Multiple comments posted within a 60-minute window")
                break

    # 7-day burst — >75% of dated reviews within any 7-day window
    # Raised from 60% → 75% to avoid false-positive on normal delivery batches.
    if len(dts_valid) >= 5:
        burst_found = False
        for i in range(len(dts_valid)):
            window_7d = [d for d in dts_valid if 0 <= (d - dts_valid[i]).days <= 7]
            if len(window_7d) / len(dts_valid) > 0.75:
                score += 0.35
                flags.append("Majority of reviews posted within a 7-day burst")
                burst_found = True
                break
        # If no burst but all reviews fall in same day, still flag clustered_dates
        if not burst_found and dts_valid:
            pass  # handled below

    # Average length — Filipino reviews are typically very short ("legit", "ok", "nice");
    # only flag genuinely minimal reviews (< 12 chars) to avoid false positives.
    avg_len = sum(len(t) for t in texts) / n
    stats["avg_length"] = round(avg_len, 1)
    if avg_len < 12:
        score += 0.3
        flags.append("Average comment length is very short")

    # Generic phrases — PH reviews commonly use short positive phrases like
    # "legit", "sulit", "ok"; only flag when they overwhelmingly dominate.
    generic_hits = sum(1 for t in texts if any(p in t for p in GENERIC_PHRASES))
    stats["generic_count"] = generic_hits
    if n and generic_hits / n > 0.60:
        score += 0.25
        flags.append("Generic phrases dominate comments")

    # Date clustering — same day > 75%
    if dts_valid:
        days = Counter(d.date() for d in dts_valid)
        top_day = days.most_common(1)[0][1]
        if top_day / len(dts_valid) > 0.75:
            score += 0.4
            flags.append("Most comments cluster on a single date")

    # Bot-pattern usernames — exclude "Anonymous" (extension fallback, not a real username)
    usernames = [(c.get("username") or c.get("user") or "").strip() for c in comments]
    real_usernames = [u for u in usernames if u and u.lower() != "anonymous"]
    n_real = len(real_usernames)
    bot_username_hits = sum(1 for u in real_usernames if _BOT_USERNAME_RE.match(u))
    if n_real and bot_username_hits / n_real > 0.4:
        score += 0.3
        flags.append("Many usernames match bot-style patterns")

    # Sequential username patterns — user001, user002 etc.
    _SEQ_RE = re.compile(r"^(.*?)(\d+)$")
    seq_groups: Counter = Counter()
    for u in real_usernames:
        m = _SEQ_RE.match(u.lower())
        if m:
            seq_groups[m.group(1)] += 1
    if n_real and any(v / n_real > 0.3 for v in seq_groups.values()):
        score += 0.35
        flags.append("Usernames follow sequential numbering patterns")

    # Rating diversity — zero reviews below 4 stars among rated comments.
    # Require at least 10 rated reviews to avoid over-penalizing listings
    # that simply haven't received any negative feedback yet.
    rated_all = [c for c in comments if c.get("rating_stars") is not None]
    if len(rated_all) >= 10:
        below_4 = sum(1 for c in rated_all if c["rating_stars"] < 4)
        if below_4 == 0:
            score += 0.2
            flags.append("All collected reviews are 4–5 star — no critical ratings found")

        # High 1-star ratio among collected comments
        one_star = sum(1 for c in rated_all if c["rating_stars"] == 1)
        one_star_ratio = one_star / len(rated_all)
        if one_star_ratio > 0.35:
            score += 0.5
            flags.append("Very high proportion of 1-star reviews among collected comments")
        elif one_star_ratio > 0.20:
            score += 0.3
            flags.append("High proportion of 1-star reviews among collected comments")

    # Fuzzy duplicate detection — catches near-identical reviews that differ by
    # only a word or two (exact-duplicate check above misses these).
    # Cap pairwise comparisons at 30 reviews to keep O(n²) bounded.
    if n >= 3:
        sample = texts[:30]
        pairs = [(i, j) for i in range(len(sample)) for j in range(i + 1, len(sample))]
        similar = sum(
            1 for i, j in pairs
            if SequenceMatcher(None, sample[i], sample[j]).ratio() > 0.80
        )
        if pairs and similar / len(pairs) > 0.35:
            score += 0.35
            flags.append("High near-duplicate text similarity across reviews")

    # Uniform review length — bots tend to post reviews of very similar lengths.
    # Bucket lengths to the nearest 10 chars; flag when one bucket dominates.
    if n >= 5:
        length_buckets = Counter(round(len(t) / 10) * 10 for t in texts)
        top_bucket_ratio = length_buckets.most_common(1)[0][1] / n
        if top_bucket_ratio > 0.70:
            score += 0.2
            flags.append("Review lengths are suspiciously uniform")

    # Small-sample dampening — with fewer than 8 reviews the signals are not
    # reliable enough to justify a high bot score. Scale down proportionally.
    if n < 8:
        score *= max(0.4, n / 8)

    return min(score, 1.0), flags, stats


def fake_review_likelihood(comments: List[Dict[str, Any]]) -> Tuple[float, List[str]]:
    """Combine ML model (if available) with rules. Returns weighted hybrid score."""
    _try_load_model()
    flags: List[str] = []
    if not comments:
        return 0.0, flags

    rule_score = _fake_review_rules(comments, flags)

    if _model is not None:
        try:
            texts = [(c.get("text") or "") for c in comments]
            preds = _model.predict_proba(texts)
            # assume class 1 == fake
            model_score = float(sum(p[1] for p in preds) / len(preds))
            if model_score > 0.6:
                flags.append("Classifier indicates elevated fake-review probability")
            # Hybrid: 40% model, 60% rules
            final = (model_score * 0.4) + (rule_score * 0.6)
            return min(max(final, 0.0), 1.0), flags
        except Exception:
            pass

    return min(rule_score, 1.0), flags


def _fake_review_rules(comments: List[Dict[str, Any]], flags: List[str]) -> float:
    score = 0.0
    # Exclude placeholder reviews with no written text
    comments = [c for c in comments if (c.get("text") or "").strip().lower() != "(no written review)"]
    n = len(comments)
    if n == 0:
        return 0.0

    # Only count reviews that actually have a star rating (null means not captured)
    # Require at least 8 rated reviews before flagging all-5-star uniformity.
    rated = [c for c in comments if c.get("rating_stars") is not None]
    n_rated = len(rated)
    five_star = sum(1 for c in rated if c.get("rating_stars") == 5)
    if n_rated >= 8 and five_star / n_rated == 1.0:
        score += 0.2
        flags.append("All rated reviews are exactly 5-star (suspiciously uniform)")

    texts = [(c.get("text") or "").lower() for c in comments]
    raw_texts = [(c.get("text") or "") for c in comments]

    generic_hits = sum(1 for t in texts if any(p in t for p in GENERIC_PHRASES))
    if generic_hits / n > 0.65:
        score += 0.2
        flags.append("Generic phrases dominate comments")

    # Includes Tagalog equivalents: produkto, kulay, sukat, kalidad, delivery
    no_specifics = sum(
        1 for t in texts
        if not re.search(
            r"(ship|deliver|courier|product|item|color|size|quality"
            r"|produkto|kulay|sukat|kalidad|pagpadala|barya|delivery)",
            t,
        )
    )
    if no_specifics / n > 0.75:
        score += 0.15
        flags.append("Comments lack shipping or product specifics")

    # All-caps text — common in fake review farms
    all_caps = sum(1 for t in raw_texts if len(t) >= 10 and t == t.upper() and any(c.isalpha() for c in t))
    if all_caps / n > 0.3:
        score += 0.2
        flags.append("Many comments are written in ALL-CAPS")

    # Single-word reviews with 5 stars (only where rating was actually captured)
    single_word_5 = sum(
        1 for c, t in zip(comments, texts)
        if c.get("rating_stars") == 5 and len(t.split()) <= 1
    )
    if single_word_5 / n > 0.4:
        score += 0.2
        flags.append("Many 5-star reviews are single-word")

    # Short reviews without any product-specific detail
    short_vague = sum(
        1 for c, t in zip(comments, texts)
        if len(t.split()) <= 3 and not re.search(
            r"(ship|deliver|product|item|color|size|quality|produkto|kalidad)", t
        )
    )
    if n and short_vague / n > 0.65:
        score += 0.15
        flags.append("Many reviews are very short with no product details")

    # Meaningless reviews — no word longer than 4 characters and under 15 chars total.
    # Catches emoji-only, single-letter strings, and placeholder noise.
    # Raised threshold from 50% → 65% to avoid penalizing PH listings where short
    # affirmations like "legit", "sulit", "ok" are the norm.
    meaningless = sum(
        1 for t in texts
        if len(t.strip()) < 15 or not re.search(r"\b\w{5,}\b", t)
    )
    if n and meaningless / n > 0.65:
        score += 0.15
        flags.append("Majority of reviews contain no meaningful words")

    # Rating-text mismatch — 5-star review containing clearly negative language
    NEGATIVE_WORDS = [
        "disappoint", "broken", "fake", "peke", "bad quality", "hindi maganda",
        "scam", "defective", "wrong item", "refund", "not working", "di gumagana",
        "hindi original", "pangit", "sira", "busted",
    ]
    mismatch = sum(
        1 for c, t in zip(comments, texts)
        if c.get("rating_stars") == 5 and any(w in t for w in NEGATIVE_WORDS)
    )
    if n and mismatch / n > 0.15:
        score += 0.5
        flags.append("High-rated reviews contain negative language")

    # Excessive emoji — >40% of comments are mostly emoji with short text
    def _is_mostly_emoji(text: str) -> bool:
        if len(text) < 3:
            return False
        emoji_chars = sum(1 for ch in text if ord(ch) > 0x1F300)
        return emoji_chars / len(text) >= 0.5 and len(text) < 30
    excessive_emoji = sum(1 for t in texts if _is_mostly_emoji(t))
    if n and excessive_emoji / n > 0.4:
        score += 0.2
        flags.append("Many reviews consist mostly of emoji with no text")

    # Forced product mention — product name in >70% of comments
    raw_texts_orig = [(c.get("text") or "") for c in comments]
    # Try to get product name from comments context — not available here, skip
    # But detect repetitive keyword injection: same rare word appears in >70% of texts
    from collections import Counter as _Counter
    word_counts: _Counter = _Counter()
    for t in texts:
        for word in set(re.findall(r"\b[a-z]{5,}\b", t)):
            if word not in GENERIC_PHRASES:
                word_counts[word] += 1
    for word, cnt in word_counts.items():
        if cnt / n > 0.7 and n >= 5:
            score += 0.3
            flags.append("Repetitive keyword injection detected across reviews")
            break

    # Identical sentence endings — >40% end with same terminal phrase
    endings = [re.split(r"[.!?]", t.strip())[-1].strip() for t in texts if t.strip()]
    endings = [e for e in endings if len(e) >= 5]
    if endings:
        top_end, top_end_count = Counter(endings).most_common(1)[0]
        if top_end_count / n > 0.4:
            score += 0.3
            flags.append("Many reviews end with identical phrases")

    return score

