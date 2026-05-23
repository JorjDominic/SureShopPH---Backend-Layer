"""Optional Groq-backed comment summary generation with local fallback safety."""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Optional

import httpx

_log = logging.getLogger(__name__)

from app.config import (
    ENABLE_GROQ_COMMENT_SUMMARY,
    ENABLE_GROQ_LISTING_SUMMARY,
    GROQ_API_KEY,
    GROQ_MODEL,
    GROQ_TIMEOUT_SECONDS,
)

_GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"


def _strip_markdown(text: str) -> str:
    """Remove common markdown formatting from Groq output."""
    text = re.sub(r'\*{1,3}(.*?)\*{1,3}', r'\1', text)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*[-*•]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    return text


def _build_prompt(context: Dict[str, Any]) -> list[dict[str, str]]:
    system = (
        "You summarize product review data for online shoppers in the Philippines. "
        "Write 2 sentences max in plain, informational English. "
        "Describe only what the data shows — for example, "
        "'Several reviews used similar wording' or 'Most reviews were posted within a short time period'. "
        "If no unusual patterns were detected, state that plainly. "
        "IMPORTANT: No bullet points, no bold text, no markdown, no headers, no numbered lists. Plain sentences only. "
        "Do not label reviews as fake, real, a scam, or verified. Only describe what the data shows. "
        "Under 300 characters."
    )
    user = json.dumps(context, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _clean_summary(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", _strip_markdown(text or "")).strip().strip("\"'`")
    if not cleaned:
        return ""
    parts = re.split(r"(?<=[.!?])\s+", cleaned)
    cleaned = " ".join(parts[:2]).strip()
    if len(cleaned) > 300:
        cleaned = cleaned[:297].rstrip() + "..."
    return cleaned


def generate_comment_summary(context: Dict[str, Any]) -> Optional[str]:
    """Return a Groq-generated summary or None when local fallback should be used."""
    if not ENABLE_GROQ_COMMENT_SUMMARY or not GROQ_API_KEY:
        return None

    payload = {
        "model": GROQ_MODEL,
        "messages": _build_prompt(context),
        "temperature": 0.2,
        "top_p": 0.9,
        "max_tokens": 120,
    }
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        response = httpx.post(
            _GROQ_CHAT_COMPLETIONS_URL,
            headers=headers,
            json=payload,
            timeout=GROQ_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        return _clean_summary(content)
    except Exception as exc:
        _log.warning("groq comment summary failed: %s", exc)
        return None


def _cat_desc(breakdown: Dict[str, Any], key: str, label: str) -> str:
    score = (breakdown.get(key) or {}).get("score", 0)
    if score == 0:
        return f"{label} looked clean"
    elif score <= 8:
        return f"{label} had minor signals"
    else:
        return f"{label} had notable signals"


def _level_phrase(level: str) -> str:
    return {
        "very low": "very low",
        "low": "low",
        "medium": "medium",
        "high": "high",
    }.get(level.lower(), level.lower())


def _buyer_tip(score: int, level: str) -> str:
    lvl = level.lower()
    if score <= 10:
        return "No significant flags were identified. Standard precautions apply when purchasing online."
    elif lvl == "low":
        return "A small number of factors were flagged. Reviewing them before purchasing is advisable."
    elif lvl == "medium":
        return "Several factors were flagged. Reviewing these before completing a purchase is recommended."
    else:
        return "Multiple factors were flagged. A careful review of each item before proceeding is recommended."


def _call_groq(messages: list, max_tokens: int) -> Optional[str]:
    """Shared Groq API call. Returns raw response content or None on failure."""
    if not GROQ_API_KEY:
        return None
    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": 0.3,
        "top_p": 0.9,
        "max_tokens": max_tokens,
    }
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        response = httpx.post(
            _GROQ_CHAT_COMPLETIONS_URL,
            headers=headers,
            json=payload,
            timeout=GROQ_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as exc:
        _log.warning("groq call failed: %s", exc)
        return None


def _clean_insight(text: str, max_sentences: int = 4, max_chars: int = 700) -> str:
    """Like _clean_summary but allows more sentences and characters."""
    cleaned = re.sub(r"\s+", " ", _strip_markdown(text or "")).strip().strip("\"'`")
    if not cleaned:
        return ""
    parts = re.split(r"(?<=[.!?])\s+", cleaned)
    cleaned = " ".join(parts[:max_sentences]).strip()
    if len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars - 3].rstrip() + "..."
    return cleaned


def _build_listing_prompt(context: Dict[str, Any]) -> list:
    system = (
        "You are helping online shoppers in the Philippines understand a product listing scan result. "
        "Write 3-4 short, direct sentences in plain English.\n\n"
        "CRITICAL RULES BEFORE YOU WRITE:\n"
        "- Do NOT open with 'The risk level is...' or 'The risk level indicates...'.\n"
        "- Never call the listing reassuring and then list concerns in the next sentence — that is a contradiction.\n"
        "- Lead with the most important actual finding. If there are notable flags, lead with those. "
        "If the listing looks clean with trust signals, lead with that.\n"
        "- Do NOT infer anything from a raw description. Only use description_patterns keys when they are present.\n"
        "- seller_account_age is how long the seller's account has been registered on the platform. "
        "Do NOT describe it as how long the listing has been posted or active.\n\n"
        "Sentence 1: Describe the single most significant finding about this listing. "
        "Weave the risk level in naturally (e.g. 'This listing has a low overall risk score, but it shows sales with no buyer ratings...' or "
        "'This listing looks mostly trustworthy — it carries a very low risk score and...').\n"
        "Sentence 2: Describe any additional flags factually — what was detected and why it matters. "
        "Rules for specific flags:\n"
        "- Only call a seller new if seller_new or seller_under_30d literally appears in the flags list.\n"
        "- If description_patterns keys are present, quote the matched phrase neutrally. "
        "If description_patterns is absent or empty, do NOT mention it.\n"
        "- Only apply 'Price Transparency Risk' wording if a flag literally starts with that exact phrase.\n"
        "- For Facebook buyer protection flag, add one brief clause — not a full sentence.\n"
        "If there are no additional flags beyond Sentence 1, skip this sentence.\n"
        "Sentence 3: Mention at least one positive aspect when the data supports it — "
        "positive_signals entries; listing_rating >= 4.0 with listing_rating_count > 10; "
        "listing_sold_count > 50; response_rate > 80. "
        "Skip entirely if nothing positive is present.\n"
        "Sentence 4: Give actionable advice. Always include asking the seller for additional product photos "
        "to check the item's quality and condition. "
        "For Facebook Marketplace listings, also cover: verifying the seller's profile and account history, "
        "using safe payment methods such as COD or meeting in person, and inspecting the item before paying.\n\n"
        "RULES: Use you/your. No markdown. No bullet points. No bold. No headers. "
        "Plain sentences only. Factual, neutral tone. Under 600 characters."
    )
    user = json.dumps(context, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _build_deep_prompt(context: Dict[str, Any]) -> list:
    system = (
        "You are helping online shoppers in the Philippines understand a combined listing and review scan result. "
        "Write 4 short, direct sentences in plain English.\n\n"
        "CRITICAL RULES BEFORE YOU WRITE:\n"
        "- Do NOT open with 'The overall result indicates...' or 'The combined risk level is...'.\n"
        "- Never call the listing reassuring and then list concerns — that is a contradiction.\n"
        "- Lead with the most important actual finding. If there are notable flags, lead with those. "
        "If the listing is genuinely clean, lead with that.\n"
        "- Do NOT infer anything from raw description text. Only use description_patterns keys when present.\n"
        "- seller_account_age is how long the seller's account has been registered on the platform. "
        "Do NOT describe it as how long the listing has been posted or active.\n\n"
        "Sentence 1: Describe the single most significant finding from the combined scan. "
        "Weave in the combined risk level naturally (e.g. 'This deep scan found a medium overall risk — "
        "the listing has X reviews analyzed with Y% bot likelihood...' or "
        "'This listing received a low combined risk score across both the listing and its reviews...').\n"
        "Sentence 2: Describe key listing flags factually. "
        "Only call a seller new if seller_new or seller_under_30d is in the flags. "
        "Only quote description_patterns phrases if the key is present. "
        "Only apply Price Transparency Risk wording to flags that literally start with that phrase. "
        "Skip this sentence if there are no additional flags beyond Sentence 1.\n"
        "Sentence 3: Describe the review data using actual numbers (analyzed count, bot %, fake %). "
        "If bot and fake percentages are low, say so positively. "
        "If no reviews exist because the listing has no sales yet, state that plainly. "
        "Also note any positive listing signals — positive_signals entries; "
        "listing_rating >= 4.0 with listing_rating_count > 10; listing_sold_count > 50; "
        "response_rate > 80. Skip positive mention if nothing supports it.\n"
        "Sentence 4: Give actionable advice. Always include asking the seller for additional product photos "
        "to verify the item's quality and condition. "
        "For Facebook Marketplace, also cover: verifying the seller's profile, "
        "using COD or in-person payment, and inspecting the item before handing over money.\n\n"
        "RULES: Use you/your. No markdown. No bullet points. No bold. No headers. "
        "Plain sentences only. Factual, neutral tone. Under 700 characters."
    )
    user = json.dumps(context, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def generate_listing_summary(context: Dict[str, Any]) -> Optional[str]:
    """Return a Groq-powered listing scan insight, falling back to a rule-built summary."""
    # --- Groq path ---
    if ENABLE_GROQ_LISTING_SUMMARY and GROQ_API_KEY:
        raw = _call_groq(_build_listing_prompt(context), max_tokens=210)
        if raw:
            result = _clean_insight(raw, max_sentences=4, max_chars=600)
            if result:
                return result

    # --- Rule-based fallback ---
    try:
        platform = (context.get("platform") or "").strip().title() or "this platform"
        risk_score = int(context.get("risk_score") or 0)
        risk_level = (context.get("risk_level") or "unknown").strip()
        breakdown = context.get("score_breakdown") or {}
        positive = context.get("positive_signals") or []

        # Sentence 1 — overall risk
        s1 = (
            f"This listing on {platform} has a {_level_phrase(risk_level)} risk score of {risk_score}/100."
        )

        # Sentence 2 — category breakdown
        seller = _cat_desc(breakdown, "seller_attributes", "Seller info")
        meta   = _cat_desc(breakdown, "listing_metadata",  "listing details")
        text   = _cat_desc(breakdown, "text_nlp",           "text patterns")
        s2 = f"{seller}, {meta}, and {text}."

        # Sentence 3 — trust signals
        if positive:
            signals_str = "; ".join(positive[:3])
            s3 = f"Good signs found: {signals_str}."
        else:
            s3 = "No trust badges like Mall-verified or Top Seller were found for this seller."

        # Sentence 4 — buyer guidance
        s4 = _buyer_tip(risk_score, risk_level)

        return f"{s1} {s2} {s3} {s4}"
    except Exception as exc:
        _log.warning("listing summary build failed: %s", exc)
        return None


def generate_deep_summary(context: Dict[str, Any]) -> Optional[str]:
    """Return a Groq-powered deep scan insight, falling back to a rule-built summary."""
    # --- Groq path ---
    if ENABLE_GROQ_LISTING_SUMMARY and GROQ_API_KEY:
        raw = _call_groq(_build_deep_prompt(context), max_tokens=230)
        if raw:
            result = _clean_insight(raw, max_sentences=4, max_chars=700)
            if result:
                return result

    # --- Rule-based fallback ---
    try:
        platform = (context.get("platform") or "").strip().title() or "this platform"
        combined_score = int(context.get("combined_risk_score") or 0)
        combined_level = (context.get("combined_risk_level") or "unknown").strip()
        breakdown = context.get("score_breakdown") or {}
        positive = context.get("positive_signals") or []
        comments = context.get("comments") or {}

        # Sentence 1 — combined risk
        s1 = (
            f"This deep scan on {platform} gives an overall {_level_phrase(combined_level)} "
            f"risk score of {combined_score}/100 — based on both the listing details and the reviews."
        )

        # Sentence 2 — listing category breakdown
        seller = _cat_desc(breakdown, "seller_attributes", "Seller info")
        meta   = _cat_desc(breakdown, "listing_metadata",  "listing details")
        text   = _cat_desc(breakdown, "text_nlp",           "text patterns")
        s2 = f"For the listing: {seller}, {meta}, and {text}."

        # Sentence 3 — comment/review analysis
        analyzed = int(comments.get("analyzed") or 0)
        sentiment = (comments.get("dominant_sentiment") or "unknown").lower()
        bot_pct  = float(comments.get("bot_likelihood_pct") or 0)
        fake_pct = float(comments.get("fake_review_pct") or 0)
        comment_flags = comments.get("flags") or []

        if analyzed == 0:
            s3 = "No reviews were captured for this scan, so the review check was skipped."
        else:
            count_note = (
                f"Only {analyzed} review{'s were' if analyzed != 1 else ' was'} collected "
                f"\u2014 not enough for a fully reliable picture"
                if analyzed < 10
                else f"{analyzed} reviews were checked"
            )
            pattern_desc = (
                "and they looked normal"
                if (bot_pct < 30 and fake_pct < 30 and not comment_flags)
                else "and some unusual patterns were noticed"
            )
            sentiment_map = {
                "positive": "mostly positive",
                "negative": "mostly negative",
                "mixed": "mixed",
                "neutral": "mostly neutral",
                "none": "",
            }
            sentiment_desc = sentiment_map.get(sentiment, "")
            s3 = (
                f"{count_note} {pattern_desc}"
                + (f", with {sentiment_desc} overall tone" if sentiment_desc else "")
                + "."
            )

        # Sentence 4 — trust signals
        if positive:
            signals_str = "; ".join(positive[:3])
            s4 = f"Good signs found: {signals_str}."
        else:
            s4 = "No trust badges like Mall-verified or Top Seller were found for this seller."

        # Sentence 5 — buyer guidance
        s5 = _buyer_tip(combined_score, combined_level)

        return f"{s1} {s2} {s3} {s4} {s5}"
    except Exception as exc:
        _log.warning("deep summary build failed: %s", exc)
        return None