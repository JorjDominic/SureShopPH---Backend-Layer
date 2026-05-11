"""POST /analyze/comments — Comments Only Scan."""
from fastapi import APIRouter, Depends

from app.auth import require_user
from app.models.schemas import CommentsPayload, CommentsAnalysisResponse
from app.rate_limit import rate_limit_analyze
from app.services.ml_classifier import bot_likelihood, fake_review_likelihood
from app.services.insights import (
    enrich_flags, build_recommendations, comment_summary,
    extract_comment_themes, comment_pattern_summary,
)

router = APIRouter(prefix="/analyze", tags=["analyze"])


def analyze_comments_payload(payload: CommentsPayload) -> dict:
    raw = [c.model_dump() for c in payload.comments]
    bot, bot_flags, bot_stats = bot_likelihood(raw)
    fake, fake_flags = fake_review_likelihood(raw)

    avg = (bot + fake) / 2
    if avg >= 0.66:
        confidence = "High"
    elif avg >= 0.33:
        confidence = "Moderate"
    else:
        confidence = "Low"

    coverage_pct = int(round((payload.page_number / payload.total_pages) * 100)) \
        if payload.total_pages else 0

    flags = bot_flags + fake_flags
    # Deduplicate flags while preserving order
    seen_flags: set = set()
    deduped_flags = []
    for f in flags:
        if f not in seen_flags:
            seen_flags.add(f)
            deduped_flags.append(f)
    flags = deduped_flags

    n = len(raw)

    # ---------- Extended rating stats ----------
    rated = [c for c in raw if c.get("rating_stars") is not None]
    n_rated = len(rated)
    five_star_count = sum(1 for c in rated if c.get("rating_stars") == 5)
    avg_rating = round(sum(c["rating_stars"] for c in rated) / n_rated, 2) if n_rated else None
    rating_diversity = any(
        c.get("rating_stars") is not None and c["rating_stars"] < 4 for c in raw
    )
    no_text_count = sum(
        1 for c in raw
        if not (c.get("text") or "").strip()
        or (c.get("text") or "").strip().lower() == "(no written review)"
    )

    # ---------- Review diversity score (0-100, higher = more diverse) ----------
    diversity_score = 100
    if n_rated >= 3 and five_star_count / n_rated > 0.9:
        diversity_score -= 25
    if bot_stats["duplicate_count"] > 1 and n and bot_stats["duplicate_count"] / n > 0.4:
        diversity_score -= 20
    if n and bot_stats["generic_count"] / n > 0.5:
        diversity_score -= 15
    if bot_stats["clustered_dates"]:
        diversity_score -= 20
    if n and no_text_count / n > 0.4:
        diversity_score -= 20
    diversity_score = max(0, diversity_score)

    # ---------- Dominant sentiment ----------
    if bot >= 0.6 or fake >= 0.6:
        dominant_sentiment = "suspicious"
    elif bot >= 0.3 or fake >= 0.3:
        dominant_sentiment = "mixed"
    else:
        dominant_sentiment = "positive"

    # ---------- Coverage note ----------
    pages_coverage_note: str | None = None
    if coverage_pct < 50 and payload.total_pages > 1:
        pages_coverage_note = (
            f"Only {min(100, max(0, coverage_pct))}% of review pages were analyzed. "
            "Results may not represent the full review set — scrolling through more "
            "review pages will improve accuracy."
        )

    # ---------- Build a structured comment_summary object ----------
    def _summary_message() -> str:
        dup = bot_stats["duplicate_count"]
        clustered = bot_stats["clustered_dates"]
        generic = bot_stats["generic_count"]
        avg_len = bot_stats["avg_length"]

        if n == 0:
            return (
                "No comments were available for analysis. Reading whatever "
                "reviews are visible on the page is still useful."
            )
        if not flags and bot < 0.2 and fake < 0.2:
            return (
                "The captured comments appear largely organic — no notable "
                "patterns were detected."
            )
        parts = []
        if dup > 1 and dup / n > 0.4:
            parts.append(
                f"{dup} out of {n} reviews contained nearly identical text"
            )
        if clustered:
            parts.append("several were posted within a short time window")
        if avg_len < 15:
            parts.append(
                f"the average review length was very short ({avg_len} characters)"
            )
        if generic > 0 and generic / n > 0.5:
            parts.append(
                f"{generic} reviews used generic phrases without specific product details"
            )
        if parts:
            body = "; ".join(parts).capitalize() + ". "
            return (
                body
                + "These patterns are sometimes associated with coordinated or "
                "copy-pasted review activity — read the actual reviews to form "
                "your own view."
            )
        if bot >= 0.6:
            return (
                "Several patterns associated with automated or copy-pasted "
                "comments were detected. Reviews here may not fully reflect "
                "real buyer experience — read them with that in mind."
            )
        if fake >= 0.6:
            return (
                "Several patterns associated with inflated reviews were "
                "detected. Look for reviews that describe specific product "
                "details to balance the picture."
            )
        return (
            "A few comment patterns are worth noting. Read through the actual "
            "review text to form your own view; the flags below explain what "
            "stood out."
        )

    structured_summary = {
        "total_analyzed": n,
        "duplicate_count": bot_stats["duplicate_count"],
        "generic_count": bot_stats["generic_count"],
        "clustered_dates": bot_stats["clustered_dates"],
        "avg_length": bot_stats["avg_length"],
        "summary_message": _summary_message(),
        "five_star_pct": int(round(five_star_count / n_rated * 100)) if n_rated else 0,
        "rated_count": n_rated,
        "avg_rating": avg_rating,
        "no_text_count": no_text_count,
        "rating_diversity": rating_diversity,
    }

    return {
        "bot_likelihood": round(bot, 3),
        "fake_review_likelihood": round(fake, 3),
        "bot_likelihood_pct": int(round(bot * 100)),
        "fake_review_pct": int(round(fake * 100)),
        "confidence": confidence,
        "comments_analyzed": n,
        "pages_analyzed": payload.page_number,
        "total_pages": payload.total_pages,
        "coverage_pct": min(100, max(0, coverage_pct)),
        "flags": flags,
        "flag_details": enrich_flags(flags, payload.platform),
        "summary": comment_summary(bot, fake, flags, n),
        "comment_summary": structured_summary,
        "comment_pattern_summary": comment_pattern_summary(flags, n, bot, fake),
        "small_sample_warning": (
            f"Only {n} review{'s' if n != 1 else ''} analyzed. Switch between star rating tabs "
            "and navigate through more comment pages to improve the reliability of this assessment."
            if n < 10 else None
        ),
        "recommendations": build_recommendations(flags),
        "review_diversity_score": diversity_score,
        "pages_coverage_note": pages_coverage_note,
        "dominant_sentiment": dominant_sentiment,
        "review_themes": extract_comment_themes(raw),
    }


@router.post("/comments", response_model=CommentsAnalysisResponse)
async def analyze_comments(
    payload: CommentsPayload,
    user=Depends(require_user),
    _rl=Depends(rate_limit_analyze),
):
    return analyze_comments_payload(payload)
