"""Optional Groq-backed comment summary generation with local fallback safety."""
from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional

import httpx

from app.config import (
    ENABLE_GROQ_COMMENT_SUMMARY,
    GROQ_API_KEY,
    GROQ_MODEL,
    GROQ_TIMEOUT_SECONDS,
)

_GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"


def _build_prompt(context: Dict[str, Any]) -> list[dict[str, str]]:
    system = (
        "You rewrite structured marketplace comment-analysis data into a short, plain summary for everyday shoppers. "
        "Use simple, everyday language — avoid technical terms like 'bot likelihood', 'coordinated activity', "
        "'probabilistic', or 'sentiment'. Write as if explaining to a friend, not a researcher. "
        "Use cautious wording — describe what was noticed, not conclusions. "
        "Do not claim the reviews are fake, scam, fraudulent, legitimate, or verified. "
        "Do not invent facts. Keep it to 1-2 sentences and under 300 characters."
    )
    user = json.dumps(context, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _clean_summary(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "")).strip().strip('"\'`')
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
    except Exception:
        return None