"""Helpful, neutral-toned explanations for flags, recommendations, and
verification checklists.

Wording guidelines used throughout this module:
- Describe observations, not verdicts ("appears", "could not be confirmed",
  "worth checking") — never "scam", "fake seller", "fraud", "untrustworthy".
- Suggest, don't dictate ("you may want to", "consider") — never "do not buy".
- Treat sellers as legitimate by default. Findings are informational signals,
  not accusations.
"""
from __future__ import annotations
from typing import Dict, List, Set


# ---------------------------------------------------------------------------
# Flag → metadata registry. Every flag string emitted by the rule engine and
# the ML classifier should appear here. Unknown flags fall back to a generic
# entry in `enrich_flags()`.
# ---------------------------------------------------------------------------

FLAG_INSIGHTS: Dict[str, Dict[str, str]] = {
    # ---- Seller attributes ----
    "Seller name not available": {
        "code": "seller_name_missing",
        "category": "seller",
        "severity": "low",
        "tip": (
            "The seller's display name was not visible on this page. "
            "You may want to open the seller's profile to confirm details "
            "before purchasing."
        ),
    },
    "Seller recently joined the platform": {
        "code": "seller_new",
        "category": "seller",
        "severity": "medium",
        "tip": (
            "This account appears to be relatively new. Newer sellers can "
            "be perfectly legitimate — taking a moment to look at their "
            "other listings and reviews can give a fuller picture."
        ),
    },
    "Seller account under 30 days old": {
        "code": "seller_under_30d",
        "category": "seller",
        "severity": "medium",
        "tip": (
            "The seller account looks less than a month old. Consider "
            "checking how many items they have sold and how buyers describe "
            "their experience."
        ),
    },
    "Seller account under 90 days old": {
        "code": "seller_under_90d",
        "category": "seller",
        "severity": "low",
        "tip": (
            "The seller account is fairly new. A quick look at their "
            "other listings can help you decide if it's a good fit."
        ),
    },
    "Very low seller response rate": {
        "code": "seller_response_low",
        "category": "seller",
        "severity": "medium",
        "tip": (
            "The seller's response rate is on the lower side. If you have "
            "questions about the item, you may want to message them first "
            "and see how quickly they reply before checking out."
        ),
    },
    "Below-average seller response rate": {
        "code": "seller_response_below_avg",
        "category": "seller",
        "severity": "low",
        "tip": (
            "The seller's response rate is a bit below average. Sending a "
            "quick message before ordering can help confirm the item is "
            "still available."
        ),
    },
    "Very low seller rating": {
        "code": "seller_rating_low",
        "category": "seller",
        "severity": "medium",
        "tip": (
            "Recent buyer feedback for this seller is on the lower side. "
            "Reading the most recent reviews can help you understand why."
        ),
    },
    "Below-average seller rating": {
        "code": "seller_rating_below_avg",
        "category": "seller",
        "severity": "low",
        "tip": (
            "The seller's average rating is a little below typical. "
            "It's worth scanning recent reviews to see common feedback."
        ),
    },

    # ---- Listing metadata ----
    "No product images provided": {
        "code": "no_images",
        "category": "metadata",
        "severity": "medium",
        "tip": (
            "No product photos were detected on this page. You may want "
            "to ask the seller for actual photos of the item before placing "
            "your order."
        ),
    },
    "Very few product images": {
        "code": "few_images",
        "category": "metadata",
        "severity": "low",
        "tip": (
            "Only a few photos are shown. Asking the seller for additional "
            "images — including different angles — can help you confirm "
            "what you'll receive."
        ),
    },
    "Price reported as 0 without 'free' indication": {
        "code": "price_zero",
        "category": "metadata",
        "severity": "medium",
        "tip": (
            "The displayed price reads as zero. This is sometimes a "
            "placeholder while the seller updates variants. Consider "
            "messaging the seller to confirm the actual price."
        ),
    },
    "Price unusually low compared to typical market": {
        "code": "price_low",
        "category": "metadata",
        "severity": "medium",
        "tip": (
            "The price is noticeably lower than typical market values for "
            "this kind of item. It could be a genuine sale — or a "
            "different version. Comparing with a few other listings can "
            "help confirm what's included."
        ),
    },
    "Perfect rating with very few reviews": {
        "code": "perfect_rating_few_reviews",
        "category": "metadata",
        "severity": "low",
        "tip": (
            "A perfect score from a small number of reviews can shift "
            "easily. Looking for listings with more reviews — or reading "
            "the available ones carefully — gives a clearer picture."
        ),
    },
    "Low average rating": {
        "code": "rating_low",
        "category": "metadata",
        "severity": "medium",
        "tip": (
            "The average rating is on the lower side. Reading the most "
            "recent reviews can help you understand the common concerns."
        ),
    },
    "Product has no ratings yet": {
        "code": "rating_none",
        "category": "metadata",
        "severity": "medium",
        "tip": (
            "This product has not received any buyer ratings. Without "
            "review history it is harder to gauge product quality or "
            "seller reliability — looking at the seller's other listings "
            "for buyer feedback can help."
        ),
    },
    "Below-average rating": {
        "code": "rating_below_avg",
        "category": "metadata",
        "severity": "low",
        "tip": (
            "The rating is a bit below average. A quick scan of recent "
            "reviews can highlight what buyers typically mention."
        ),
    },
    "Zero recorded sales": {
        "code": "sales_zero",
        "category": "metadata",
        "severity": "medium",
        "tip": (
            "No completed sales are shown for this listing. An untested "
            "listing carries more uncertainty — checking the seller\'s "
            "other listings for buyer feedback is a useful alternative."
        ),
    },
    "Seller account age and response rate not visible": {
        "code": "seller_profile_unverifiable",
        "category": "seller",
        "severity": "low",
        "tip": (
            "This seller's account age and response rate were not visible on "
            "the listing page and no platform badge confirms their standing. "
            "Checking the seller's shop page directly can give you a better "
            "picture of their history before purchasing."
        ),
    },
    "Unverified listing: no recorded sales or buyer ratings": {
        "code": "listing_no_history",
        "category": "metadata",
        "severity": "medium",
        "tip": (
            "This listing has no completed sales and no buyer ratings, "
            "meaning there is no purchase history to assess. Consider "
            "checking the seller's other listings for buyer feedback, or "
            "purchasing elsewhere until some buyer history is available."
        ),
    },
    "No items sold on this listing": {
        "code": "sales_unavailable",
        "category": "metadata",
        "severity": "low",
        "tip": (
            "The number of items sold was not visible on this page. "
            "Without purchase history it is harder to gauge how well the "
            "product performs — the seller\'s overall reviews can give "
            "a better picture."
        ),
    },
    "Price shown as a variant range": {
        "code": "price_variant",
        "category": "metadata",
        "severity": "low",
        "tip": (
            "The price appears as a range, which usually means different "
            "variants. Confirm with the seller which variant matches the "
            "price you expect to pay."
        ),
    },
    "Item condition not specified": {
        "code": "condition_unspecified",
        "category": "metadata",
        "severity": "low",
        "tip": (
            "The item's condition (new, used, refurbished) was not stated. "
            "Asking the seller directly can prevent surprises on arrival."
        ),
    },
    "Listing posted very recently (under 24h)": {
        "code": "listing_new",
        "category": "metadata",
        "severity": "low",
        "tip": (
            "This listing was posted very recently. It may simply be new "
            "stock — taking a moment to review the seller's profile can "
            "still be useful."
        ),
    },
    "Description appears auto-generated only": {
        "code": "description_autogen",
        "category": "metadata",
        "severity": "low",
        "tip": (
            "The description looks like it may be auto-generated. Asking "
            "the seller for specific details (size, model, contents) can "
            "help confirm what's included."
        ),
    },
    "Facebook Marketplace: no platform buyer protection or seller verification": {
        "code": "fb_platform_risk",
        "category": "metadata",
        "severity": "low",
        "tip": (
            "Facebook Marketplace does not offer built-in buyer protection or "
            "formal seller verification. This is noted as platform context — "
            "it reflects the environment, not a finding specific to this seller."
        ),
    },
    "Price Transparency Risk: single-digit price may be a placeholder — confirm actual price with seller": {
        "code": "fb_price_placeholder_single",
        "category": "metadata",
        "severity": "medium",
        "tip": (
            "A single-digit price is almost certainly a placeholder set while "
            "the seller arranges details. Message the seller to confirm the "
            "real price before proceeding."
        ),
    },
    "Price Transparency Risk: repeated-digit price pattern may indicate a placeholder — confirm actual price with seller": {
        "code": "fb_price_placeholder_repeated",
        "category": "metadata",
        "severity": "medium",
        "tip": (
            "Prices like 1111 or 9999 are common placeholder values on "
            "Facebook Marketplace. Confirm the actual price with the seller "
            "before agreeing to any payment."
        ),
    },
    "Price Transparency Risk: sequential-digit price may indicate a placeholder — confirm actual price with seller": {
        "code": "fb_price_placeholder_sequential",
        "category": "metadata",
        "severity": "medium",
        "tip": (
            "Sequential prices like 1234 or 12345 are commonly used as "
            "placeholder values. Ask the seller to confirm the real price "
            "before making any payment."
        ),
    },
    "Seller response time is slow": {
        "code": "seller_response_slow",
        "category": "seller",
        "severity": "low",
        "tip": (
            "The seller's response time is listed as a few days or longer. "
            "Send a message before ordering and factor in how long a reply "
            "might take if you have questions or issues after purchase."
        ),
    },
    "Unusually low rating coverage for sales volume": {
        "code": "rating_coverage_low",
        "category": "metadata",
        "severity": "low",
        "tip": (
            "This listing has a large number of recorded sales but very few "
            "buyer ratings. The gap between purchases and reviews is wider "
            "than typical — read the available reviews carefully and consider "
            "checking similar products for more feedback."
        ),
    },
    "Soft persuasion language reinforces other risk signals in this listing": {
        "code": "soft_bait_compound",
        "category": "text",
        "severity": "low",
        "tip": (
            "The description uses multiple soft persuasion words (such as "
            '"sale", "mura", or "legit") alongside other flagged signals. '
            "Taken alone these are common phrases — in combination with "
            "other flags they add to the overall picture."
        ),
    },

    # ---- Textual / NLP ----
    "Description missing or too short": {
        "code": "description_short",
        "category": "text",
        "severity": "low",
        "tip": (
            "Very little product information was provided. Reaching out "
            "to the seller for details before ordering can help avoid "
            "mismatches."
        ),
    },
    "Urgency or scarcity language detected": {
        "code": "urgency_language",
        "category": "text",
        "severity": "medium",
        "tip": (
            "The listing uses time-pressure or scarcity wording (e.g. "
            "\"last stock\", \"today only\"). Take the time you need — "
            "comparing similar listings often shows the item is still "
            "widely available."
        ),
    },
    "Over-promising language detected": {
        "code": "promise_language",
        "category": "text",
        "severity": "low",
        "tip": (
            "The listing uses strong assurance phrases (e.g. "
            "\"100% legit\", \"guaranteed\"). These are common marketing "
            "phrases — confirming specifics with the seller is still a "
            "good practice."
        ),
    },
    "Pressure payment terms detected": {
        "code": "payment_pressure",
        "category": "text",
        "severity": "high",
        "tip": (
            "The listing mentions payment conditions like upfront-only or "
            "no-refund. Whenever possible, prefer the platform's official "
            "checkout — it offers buyer protection if something goes wrong."
        ),
    },
    "Vague brand or publisher information": {
        "code": "brand_vague",
        "category": "text",
        "severity": "low",
        "tip": (
            "Brand or publisher details are not clearly stated. If the "
            "exact brand matters to you, ask the seller to confirm before "
            "ordering."
        ),
    },
    # ---- URL / domain ----
    "Malformed URL": {
        "code": "url_malformed",
        "category": "url",
        "severity": "high",
        "tip": (
            "The page URL could not be parsed cleanly. If you arrived from "
            "a link in a message, prefer typing the platform's address "
            "into the browser yourself."
        ),
    },
    "Possible typosquatting domain": {
        "code": "url_typo",
        "category": "url",
        "severity": "high",
        "tip": (
            "The web address looks similar to — but not exactly the same "
            "as — a known shopping site. Double-check the URL bar before "
            "entering any login or payment details."
        ),
    },
    "Connection is not HTTPS": {
        "code": "url_no_https",
        "category": "url",
        "severity": "high",
        "tip": (
            "This page is not using a secure (HTTPS) connection. "
            "Entering payment or account information here is not recommended."
        ),
    },
    "Unusually deep subdomain": {
        "code": "url_deep_subdomain",
        "category": "url",
        "severity": "low",
        "tip": (
            "The URL has more sub-parts than usual for an official "
            "platform page. Confirming the site address is genuine is a "
            "small step that adds peace of mind."
        ),
    },

    # ---- Comments: bot likelihood ----
    "High duplicate-text ratio across comments": {
        "code": "comments_duplicate",
        "category": "comments",
        "severity": "medium",
        "tip": (
            "Many of the comments contain identical or near-identical "
            "text. Reviews with specific product details usually offer "
            "more useful insight than repeated short phrases."
        ),
    },
    "Multiple comments posted within a 60-minute window": {
        "code": "comments_time_cluster",
        "category": "comments",
        "severity": "medium",
        "tip": (
            "Several comments were posted close together in time. Look "
            "for reviews spread across different dates for a more "
            "balanced view."
        ),
    },
    "Average comment length is very short": {
        "code": "comments_short",
        "category": "comments",
        "severity": "low",
        "tip": (
            "Most comments here are brief. Longer reviews that mention "
            "shipping time, packaging or product details tend to be more "
            "informative."
        ),
    },
    "Generic phrases dominate comments": {
        "code": "comments_generic",
        "category": "comments",
        "severity": "low",
        "tip": (
            "Many comments use general phrases like \"legit\" or "
            "\"sulit\" without product specifics. Reviews that describe "
            "the item itself are usually more helpful for your decision."
        ),
    },
    "Most comments cluster on a single date": {
        "code": "comments_date_cluster",
        "category": "comments",
        "severity": "medium",
        "tip": (
            "Most reviews fall on the same date. Looking for reviews "
            "from a range of dates gives a clearer ongoing picture."
        ),
    },
    "Many usernames match bot-style patterns": {
        "code": "comments_bot_usernames",
        "category": "comments",
        "severity": "low",
        "tip": (
            "Several reviewer usernames follow generic auto-generated "
            "patterns. This is informational only — many real users keep "
            "default usernames."
        ),
    },

    # ---- Comments: fake review rules ----
    "All rated reviews are exactly 5-star (suspiciously uniform)": {
        "code": "comments_all_5star",
        "category": "comments",
        "severity": "low",
        "tip": (
            "Every captured review is 5 stars. A mix of ratings tends to "
            "be a more realistic sign — though great products do exist. "
            "Reading the actual review text can help confirm."
        ),
    },
    "Comments lack shipping or product specifics": {
        "code": "comments_no_specifics",
        "category": "comments",
        "severity": "low",
        "tip": (
            "Few comments mention shipping or product specifics. Reviews "
            "describing real-use details are usually the most useful for "
            "deciding whether to buy."
        ),
    },
    "Many comments are written in ALL-CAPS": {
        "code": "comments_all_caps",
        "category": "comments",
        "severity": "low",
        "tip": (
            "Several comments are written entirely in capital letters. "
            "This is a minor stylistic signal — read the content itself "
            "rather than relying on formatting alone."
        ),
    },
    "Many 5-star reviews are single-word": {
        "code": "comments_single_word_5",
        "category": "comments",
        "severity": "low",
        "tip": (
            "A number of 5-star reviews contain only one word. Detailed "
            "reviews — even shorter ones with specifics — usually carry "
            "more useful information."
        ),
    },
    "Most reviews are not verified purchases": {
        "code": "comments_unverified",
        "category": "comments",
        "severity": "medium",
        "tip": (
            "Most reviews here are not marked as verified purchases. "
            "Verified-purchase reviews tend to reflect actual buyer "
            "experience more reliably."
        ),
    },
    "Multiple photo-only reviews with no text": {
        "code": "comments_photo_only",
        "category": "comments",
        "severity": "low",
        "tip": (
            "Several reviews are photo-only with no written feedback. "
            "Photos are useful, but written experience adds context that "
            "images alone cannot."
        ),
    },
    "Classifier indicates elevated fake-review probability": {
        "code": "comments_ml_signal",
        "category": "comments",
        "severity": "medium",
        "tip": (
            "Our review-pattern model flagged this set of comments as "
            "showing patterns commonly seen in inflated reviews. Treat "
            "this as one signal among many — read the comments yourself "
            "to form your own view."
        ),
    },
    # ---- New comment flags ----
    "Majority of reviews posted within a 7-day burst": {
        "code": "comments_review_burst",
        "category": "comments",
        "severity": "high",
        "tip": (
            "The majority of reviews were posted within a short 7-day window, "
            "which can indicate a coordinated review campaign. Look for reviews "
            "spread across different weeks or months for a more balanced picture."
        ),
    },
    "All collected reviews are 4–5 star — no critical ratings found": {
        "code": "comments_no_rating_diversity",
        "category": "comments",
        "severity": "medium",
        "tip": (
            "None of the captured reviews are below 4 stars. While this could "
            "mean a genuinely great product, a complete absence of mixed ratings "
            "is uncommon and worth keeping in mind when reading the reviews."
        ),
    },
    "Usernames follow sequential numbering patterns": {
        "code": "comments_username_sequence",
        "category": "comments",
        "severity": "medium",
        "tip": (
            "Several reviewer usernames share the same prefix with incrementing "
            "numbers (e.g. user001, user002). This can be a sign of accounts "
            "created in bulk. Read the review content itself to form your own view."
        ),
    },
    "High-rated reviews contain negative language": {
        "code": "comments_rating_text_mismatch",
        "category": "comments",
        "severity": "high",
        "tip": (
            "Some reviews are rated 5 stars but contain words that suggest "
            "disappointment or a problem with the product. This mismatch can "
            "indicate purchased or coerced reviews — read the full text carefully."
        ),
    },
    "Many reviews consist mostly of emoji with no text": {
        "code": "comments_excessive_emoji",
        "category": "comments",
        "severity": "low",
        "tip": (
            "A significant portion of the reviews contain mostly emoji characters "
            "with little or no written text. Prioritize written reviews that "
            "describe the product or delivery experience."
        ),
    },
    "Repetitive keyword injection detected across reviews": {
        "code": "comments_forced_product_mention",
        "category": "comments",
        "severity": "medium",
        "tip": (
            "An unusual word appears across the majority of reviews, which can "
            "be a sign of template-based or coordinated review writing. Read "
            "reviews individually to see which ones offer genuine detail."
        ),
    },
    "Many reviews end with identical phrases": {
        "code": "comments_identical_sentence_end",
        "category": "comments",
        "severity": "medium",
        "tip": (
            "Many of the reviews end with the same phrase or sentence. This "
            "pattern is associated with copy-pasted or template-generated reviews. "
            "Look for reviews that describe specific product experiences."
        ),
    },
}


# ---------------------------------------------------------------------------
# Per-code recommendations: short, action-oriented bullets surfaced once each.
# ---------------------------------------------------------------------------

RECOMMENDATIONS_BY_CODE: Dict[str, str] = {
    "seller_new": "Browse the seller's other listings and reviews to get a fuller sense of their activity.",
    "seller_under_30d": "Send a brief message to the seller before ordering — response speed and tone are useful clues.",
    "seller_under_90d": "Glance over the seller's recent listings to see if they're consistent.",
    "seller_response_low": "Try messaging the seller first; if they reply quickly, that's a positive sign.",
    "seller_response_below_avg": "A short pre-order message can confirm stock and shipping timeline.",
    "seller_rating_low": "Read the most recent reviews to see what concerns buyers commonly mention.",
    "seller_rating_below_avg": "Skim the latest reviews to spot recurring themes.",
    "seller_name_missing": "Open the seller's profile directly to confirm their store details.",
    "no_images": "Ask the seller for actual photos of the item before placing an order.",
    "few_images": "Request additional photos — different angles or close-ups help confirm condition.",
    "price_zero": "Confirm the actual price with the seller before checking out.",
    "price_low": "Compare with a couple of similar listings to make sure the version matches what you expect.",
    "perfect_rating_few_reviews": "Look for similar listings with more reviews to compare buyer experience.",
    "rating_low": "Read recent reviews carefully before deciding.",
    "rating_below_avg": "Check the latest reviews for recurring feedback.",
    "no_sales": "Consider asking the seller about stock and shipping before committing.",
    "price_variant": "Confirm which variant matches the price you saw and what's included.",
    "condition_unspecified": "Ask the seller whether the item is brand new, used, or refurbished.",
    "listing_new": "Take a look at the seller's other listings before deciding.",
    "description_autogen": "Ask the seller for specific details that matter to your purchase.",
    "description_short": "Message the seller for the missing details before ordering.",
    "urgency_language": "Take your time — comparing other listings helps confirm if the item is widely available.",
    "promise_language": "Verify specific claims (warranty, authenticity, sealed packaging) directly with the seller.",
    "payment_pressure": "Use the platform's official checkout when possible — it offers buyer protection.",
    "brand_vague": "Ask the seller to confirm the exact brand or publisher.",
    "specs_missing_lazada": "Request the missing specifications from the seller.",
    "specs_missing_shopee": "Request the missing specifications from the seller.",
    "url_malformed": "Type the platform's web address directly in the browser instead of clicking the link.",
    "url_typo": "Double-check the address bar — ensure you're on the official site before logging in or paying.",
    "url_no_https": "Entering payment or login details on a non-secure page is not recommended.",
    "url_deep_subdomain": "Verify you're on the official platform domain before continuing.",
    "comments_duplicate": "Look for reviews that describe specific product details rather than repeating phrases.",
    "comments_time_cluster": "Look for reviews spread across different dates for a more balanced view.",
    "comments_short": "Prioritize longer reviews that mention shipping, packaging, or product details.",
    "comments_generic": "Focus on reviews that describe the actual item rather than only saying \"legit\" or \"ok\".",
    "comments_date_cluster": "Look for reviews from different time periods, not just one date.",
    "comments_bot_usernames": "Read the review content itself rather than judging by usernames.",
    "comments_all_5star": "Read the review text — a uniform 5-star pattern can be either real enthusiasm or inflation.",
    "comments_no_specifics": "Prioritize reviews that mention shipping, packaging, or product use.",
    "comments_all_caps": "Focus on the substance of reviews rather than their formatting.",
    "comments_single_word_5": "Look for detailed reviews — even short ones — that mention real product details.",
    "comments_unverified": "Give more weight to verified-purchase reviews when available.",
    "comments_photo_only": "Combine photo evidence with the written reviews you can find.",
    "comments_ml_signal": "Read several reviews yourself before drawing conclusions — the model is one signal, not a verdict.",
    "comments_review_burst": "Look for reviews spread across different weeks or months rather than a single concentrated window.",
    "comments_no_rating_diversity": "Search for reviews on similar products to compare whether a perfect rating is typical for this category.",
    "comments_username_sequence": "Focus on the review content itself rather than judging by the reviewer's username.",
    "comments_rating_text_mismatch": "Read the full review text carefully — star ratings alone may not reflect the actual buyer experience here.",
    "comments_excessive_emoji": "Prioritize written reviews that describe the product or delivery experience.",
    "comments_forced_product_mention": "Look for reviews that describe a genuine personal experience rather than repeating keywords.",
    "comments_identical_sentence_end": "Seek out reviews with unique, specific detail — reviews ending with identical phrases are less informative.",
    "fb_platform_risk": "Exercise the same precautions you would for any unverified online transaction — confirm item details and agree on payment method before committing.",
    "fb_price_placeholder_single": "Message the seller to confirm the actual price before agreeing to anything.",
    "fb_price_placeholder_repeated": "Ask the seller directly what the real price is — do not send any payment until you have a clear written answer.",
    "fb_price_placeholder_sequential": "Confirm the real price in writing before proceeding.",
    "seller_response_slow": "Factor in the seller's response time when planning your purchase — send your questions early.",
    "rating_coverage_low": "Check the seller's overall profile for additional buyer feedback beyond this listing's reviews.",
    "soft_bait_compound": "Compare the listing against similar items to see whether the claimed deal matches the market.",
}


# ---------------------------------------------------------------------------
# Per-code explanation text: "why it matters and what to do" (second part of
# the two-part flag format). Surfaced alongside the detection label in the
# extension's flag_details output.
# ---------------------------------------------------------------------------

EXPLANATIONS_BY_CODE: Dict[str, str] = {
    "seller_name_missing": "Without a visible seller name it is harder to look up their track record. Open the seller's profile directly to confirm their store details before purchasing.",
    "seller_new": "A newly created account has no purchase history, making it harder to gauge reliability. Browse their other listings or send a message to gauge responsiveness before committing.",
    "seller_under_30d": "Accounts active for less than a month have not had time to build buyer feedback. Send a brief message before ordering — response speed is a useful signal.",
    "seller_under_90d": "A seller less than 90 days old is still building their track record. Glancing at their other listings gives a fuller picture of their activity.",
    "seller_response_low": "A very low response rate can mean slower replies when you have questions or issues after purchase. Try messaging the seller first — a prompt reply is a positive sign.",
    "seller_response_below_avg": "Slower-than-average response times may affect how quickly your questions get answered. A short pre-order message can confirm stock availability and shipping timelines.",
    "seller_rating_low": "A low seller rating reflects feedback from past buyers. Reading the most recent reviews helps you understand what concerns buyers commonly mention.",
    "seller_rating_below_avg": "A slightly below-average rating suggests some buyers had a less-than-ideal experience. Skimming the latest reviews for recurring themes is a quick way to check.",
    "no_images": "Without photos it is impossible to visually verify the item's condition. Ask the seller for actual photos of the product — not stock images — before placing an order.",
    "few_images": "Limited photos make it harder to assess the item's condition and what is included. Requesting additional angles or close-ups helps confirm what you will receive.",
    "price_zero": "A zero price is sometimes a placeholder while the seller sets up variants. Confirm the actual price in writing with the seller before proceeding to checkout.",
    "price_low": "A price significantly below similar listings could reflect a genuine sale, a used item, a budget edition, or a different variant. Verify the product condition, edition, and what is included with the seller before completing your purchase.",
    "price_variant": "Variant pricing means the final cost depends on which option you select. Confirm which variant matches the price you expect before adding to cart.",
    "rating_none": "Without any buyer ratings there is no purchase history to draw on. Looking at the seller's other listings for buyer feedback gives a better sense of their reliability.",
    "perfect_rating_few_reviews": "A perfect score from a very small number of reviews can shift with just one negative experience. Look for similar listings with more reviews to compare buyer experiences.",
    "rating_low": "A below-average product rating indicates that buyers have reported concerns. Reading recent reviews helps you understand the most common issues.",
    "rating_below_avg": "A slightly below-average rating suggests mixed buyer experiences. A quick look at recent reviews can highlight what buyers most often mention.",
    "sales_zero": "No recorded sales means there is no purchase history for this listing. Check the seller's other listings for buyer feedback as an alternative reference.",
    "sales_unavailable": "Without a visible sales count it is harder to assess how well this product has performed. The seller's overall profile reviews can give a better picture.",
    "condition_unspecified": "Not knowing whether an item is brand new, used, or refurbished makes it harder to judge value and what to expect on arrival. Ask the seller directly before placing your order.",
    "listing_new": "A listing with no buyer interaction history provides no track record to assess. Taking a moment to review the seller's profile and other listings is a useful extra step.",
    "description_autogen": "Auto-generated descriptions often lack specifics that genuine sellers would include. Ask for details — size, model, or contents — that matter for your purchase.",
    "description_short": "Very little product information makes it harder to know exactly what you are buying. Message the seller for the details that are missing before ordering.",
    "urgency_language": "Pressure wording is designed to speed up purchase decisions. Taking time to compare similar listings typically shows the item is not as scarce as the description suggests.",
    "promise_language": "Assurance phrases are common in marketing but do not substitute for verification. Ask the seller to confirm specific claims such as warranty coverage or original packaging.",
    "payment_pressure": "Upfront or off-platform payment terms reduce buyer protection significantly. Whenever possible, use the platform's official checkout — it offers recourse if the item does not arrive as described.",
    "brand_vague": "Unspecified brand information makes it harder to verify the product's origin and authenticity. If the brand matters to you, ask the seller to confirm before ordering.",
    "url_malformed": "A URL that cannot be parsed cleanly may indicate you arrived via an unusual link. Type the platform's official web address directly into your browser rather than following external links.",
    "url_typo": "A web address that closely resembles but does not exactly match an official platform domain is a common technique used to misdirect buyers. Double-check the address bar before logging in or entering payment details.",
    "url_no_https": "An unencrypted connection means your login and payment information is not protected. Entering sensitive details on this page is not recommended.",
    "url_deep_subdomain": "An unusually complex URL is atypical for official platform listings. Verify that the domain in the address bar matches the platform's official web address.",
    "comments_duplicate": "Reviews that share nearly identical text are less likely to reflect independent personal buyer experiences. Look for reviews that describe specific product details — delivery time, packaging, condition.",
    "comments_time_cluster": "A concentration of reviews posted in a short window is unusual for organic buyer activity. Look for reviews spread across different dates for a more balanced view.",
    "comments_review_burst": "The majority of reviews arriving within one week is unusual for organic buyer activity. Look for reviews spread across different months rather than relying on a single concentrated window.",
    "comments_all_5star": "A completely uniform rating across all collected reviews is uncommon for most products. While it could reflect genuine satisfaction, reading the actual review text helps confirm whether the feedback reflects real experiences.",
    "comments_no_specifics": "Reviews that do not mention specific details like delivery time, packaging quality, or product condition provide less useful information. Prioritize reviews that describe a real purchase experience.",
    "comments_ml_signal": "The review-pattern model flagged this set of comments as showing patterns associated with review inflation. This is one signal among many — reading the reviews yourself provides the most reliable picture.",
    "comments_rating_text_mismatch": "A mismatch between a high star rating and language suggesting disappointment is an unusual pattern. Read the full text of several high-rated reviews before relying on the star score.",
    "comments_no_rating_diversity": "A complete absence of negative or mixed ratings is uncommon for most products. Comparing with reviews on similar product listings helps provide context for whether a perfect rating is typical.",
    "comments_username_sequence": "Reviewer usernames that follow a sequential numbering pattern can indicate accounts created in bulk. Focus on the review content itself rather than the usernames.",
    "comments_forced_product_mention": "The same unusual word appearing across most reviews can indicate template-based review writing. Look for reviews that describe a genuine personal experience with the product.",
    "comments_identical_sentence_end": "Reviews that end with the same phrase are associated with copy-pasted review activity. Seek out reviews with unique, specific detail for more useful buyer information.",
    "comments_generic": "Short generic phrases like 'legit' or 'sulit' without product specifics are common in both genuine and non-genuine reviews. Prioritize reviews that describe the actual item.",
    "comments_short": "Very short reviews provide limited information regardless of their rating. Focus on longer reviews that mention delivery time, product condition, or specific details.",
    "comments_date_cluster": "Most reviews concentrated on a single date is unusual for organic buyer activity. Look for reviews from a range of dates for a more reliable picture.",
    "comments_bot_usernames": "Several reviewers use generic auto-generated username formats. Many real users keep default usernames, so focus on the review content itself.",
    "comments_all_caps": "All-caps reviews are a minor stylistic signal. Judge reviews by their content rather than their formatting.",
    "comments_single_word_5": "Single-word 5-star reviews provide almost no useful information about the product. Look for reviews that describe a real purchase experience.",
    "comments_unverified": "Unverified reviews are not linked to a confirmed purchase of this specific item. Give more weight to verified-purchase reviews when they are available.",
    "comments_photo_only": "Photo-only reviews without written feedback provide limited context. Combine photo evidence with written reviews that describe the actual purchase experience.",
    "comments_excessive_emoji": "Reviews consisting mostly of emoji with little written text provide limited information. Prioritize written reviews that describe the product or delivery experience.",
    "rating_none": "Without any buyer ratings there is no purchase history to draw on. Looking at the seller's other listings for buyer feedback gives a better sense of their reliability.",
    "fb_platform_risk": "Facebook Marketplace operates without the buyer protection guarantees of Shopee or Lazada. There is no platform-managed escrow, return guarantee, or formal seller verification process. This is noted as context for all FB listings.",
    "fb_price_placeholder_single": "A single-digit price on Facebook Marketplace almost always means the seller has not yet set the real price. Do not assume this is the actual amount — confirm in writing before any payment.",
    "fb_price_placeholder_repeated": "Repeated-digit prices like 1111 or 9999 are a well-known pattern for placeholder entries on Facebook Marketplace. Always confirm the seller's real asking price before making any payment.",
    "fb_price_placeholder_sequential": "Sequential prices like 1234 or 123456 are frequently used as temporary placeholders. Confirm the real amount with the seller before proceeding.",
    "seller_response_slow": "A seller whose response time is measured in days may be slower to address questions, shipping updates, or concerns. Sending your questions before ordering gives you time to receive a reply before committing.",
    "rating_coverage_low": "When a listing shows many sales but very few reviews, most buyers did not leave feedback. This is not necessarily a problem — but it limits the usefulness of the ratings you can see.",
    "soft_bait_compound": "Words like 'sale', 'mura', 'legit', or 'below SRP' are extremely common in Philippine online listings and are not individually meaningful. When several appear together alongside other flagged signals, the overall pattern is worth factoring into your decision.",
}

# ---------------------------------------------------------------------------
# Flag weights for dynamic risk message generation.
# Higher weight = more prominently named in the summary message.
# ---------------------------------------------------------------------------

_SEVERITY_WEIGHT: Dict[str, int] = {"high": 3, "medium": 2, "low": 1}

_CODE_WEIGHT_OVERRIDE: Dict[str, int] = {
    "url_typo": 6, "url_no_https": 6, "url_malformed": 6,
    "payment_pressure": 6,
    "comments_rating_text_mismatch": 5,
    "seller_under_30d": 4, "seller_new": 4,
    "comments_review_burst": 4,
    "urgency_language": 3, "price_low": 3, "rating_none": 3, "sales_zero": 3,
    "perfect_rating_few_reviews": 3, "comments_ml_signal": 3,
    "fb_price_placeholder_single": 4, "fb_price_placeholder_repeated": 4, "fb_price_placeholder_sequential": 4,
}

# Plain-English description of each signal for use in the dynamic risk message.
_FLAG_PLAIN_NAMES: Dict[str, str] = {
    "url_typo": "a web address that does not match the official platform domain",
    "url_no_https": "an insecure page connection",
    "url_malformed": "a URL that could not be properly parsed",
    "url_deep_subdomain": "an unusually deep subdomain structure",
    "payment_pressure": "payment terms that require upfront or off-platform payment",
    "seller_new": "a seller account with no established sales history",
    "seller_under_30d": "a seller account created within the last 30 days",
    "seller_under_90d": "a seller account less than 90 days old",
    "seller_name_missing": "a seller whose display name was not visible",
    "seller_response_low": "a seller with a very low response rate",
    "seller_response_below_avg": "a seller with a below-average response rate",
    "seller_rating_low": "a seller with a very low rating from buyers",
    "seller_rating_below_avg": "a seller with a below-average buyer rating",
    "no_images": "a listing with no product photos",
    "few_images": "a listing with very few product photos",
    "price_zero": "a price displayed as zero",
    "price_low": "a listed price notably lower than similar items",
    "price_variant": "a price shown as a range across variants",
    "rating_none": "a product with no buyer ratings yet",
    "perfect_rating_few_reviews": "a perfect 5-star rating based on very few reviews",
    "rating_low": "a below-average product rating from buyers",
    "rating_below_avg": "a product rating slightly below average",
    "sales_zero": "zero recorded sales for this listing",
    "sales_unavailable": "a listing where the sales count was not visible",
    "condition_unspecified": "an item condition not specified by the seller",
    "listing_new": "a listing posted within the last 24 hours",
    "description_autogen": "a description that appears auto-generated",
    "description_short": "a product description that is missing or very short",
    "urgency_language": "time-pressure or scarcity wording in the listing description",
    "promise_language": "strong assurance phrases in the listing description",
    "brand_vague": "vague or unspecified brand and publisher information",
    "comments_duplicate": "a high proportion of identical review texts",
    "comments_time_cluster": "several reviews posted within a 60-minute window",
    "comments_review_burst": "the majority of reviews posted within a single 7-day window",
    "comments_all_5star": "all rated reviews are exactly 5-star (suspiciously uniform)",
    "comments_no_specifics": "reviews that do not mention specific product or delivery details",
    "comments_ml_signal": "review patterns that the classifier associates with elevated review inflation",
    "comments_rating_text_mismatch": "high-rated reviews containing language that suggests disappointment",
    "comments_no_rating_diversity": "all collected reviews are 4–5 star with no critical ratings",
    "comments_username_sequence": "reviewer usernames following sequential numbering patterns",
    "comments_forced_product_mention": "an unusual word repeated across the majority of reviews",
    "comments_identical_sentence_end": "many reviews ending with identical phrases",
    "comments_generic": "reviews dominated by short generic phrases",
    "comments_short": "reviews that are unusually short on average",
    "comments_bot_usernames": "several usernames matching bot-style patterns",
    "fb_platform_risk": "a Facebook Marketplace listing with no platform buyer protection",
    "fb_price_placeholder_single": "a price that appears to be a single-digit placeholder",
    "fb_price_placeholder_repeated": "a price that appears to be a repeated-digit placeholder",
    "fb_price_placeholder_sequential": "a price that appears to be a sequential-digit placeholder",
    "seller_response_slow": "a seller with a slow listed response time",
    "rating_coverage_low": "an unusually low review rate relative to the number of sales",
    "soft_bait_compound": "soft persuasion language appearing alongside other flagged signals",
}


# ---------------------------------------------------------------------------
# Verification checklist items — short, neutral steps a buyer can run through
# when the risk band is Medium or High. Keyed by code so we can build the
# list from whatever flags actually fired.
# ---------------------------------------------------------------------------

CHECKLIST_BY_CODE: Dict[str, str] = {
    "seller_new": "Open the seller's profile and review their other listings.",
    "seller_under_30d": "Confirm with the seller how long they've been selling and what items they ship most.",
    "seller_response_low": "Send a test message and wait for a reply before paying.",
    "seller_rating_low": "Read at least 5 of the most recent reviews.",
    "no_images": "Request photos of the actual item, not stock images.",
    "price_zero": "Confirm the real price in writing before checking out.",
    "price_low": "Compare against at least two similar listings.",
    "perfect_rating_few_reviews": "Find a similar listing with more reviews and compare.",
    "urgency_language": "Pause — give yourself time to compare before deciding.",
    "promise_language": "Ask for proof of specific claims (e.g. authenticity card, warranty).",
    "payment_pressure": "Using the platform's official checkout offers more buyer protection than direct GCash or bank transfers.",
    "url_malformed": "Type the official platform URL into the browser yourself.",
    "url_typo": "Verify the domain in the address bar matches the official platform.",
    "url_no_https": "Entering login or payment details on this page is not recommended.",
    "comments_duplicate": "Skim reviews looking for unique, detail-rich entries before relying on the rating.",
    "comments_time_cluster": "Look for reviews posted across different weeks or months.",
    "comments_unverified": "Filter for verified-purchase reviews if the platform allows.",
    "comments_ml_signal": "Read at least a handful of reviews yourself to form your own opinion.",
    "comments_review_burst": "Look for reviews posted across different months — avoid relying only on a single burst window.",
    "comments_no_rating_diversity": "Compare with other listings for this product type to see if a perfect rating is typical.",
    "comments_rating_text_mismatch": "Read the full text of several high-rated reviews before deciding.",
    "comments_username_sequence": "Read at least 5 reviews and assess their content independently of the username.",
    "comments_forced_product_mention": "Look for at least 3 reviews that describe a real use experience.",
    "comments_identical_sentence_end": "Find reviews that end differently and describe the product specifically.",
    "fb_price_placeholder_single": "Confirm the actual price with the seller in writing before sending any payment.",
    "fb_price_placeholder_repeated": "Ask the seller directly for the real price — do not assume the displayed amount is correct.",
    "fb_price_placeholder_sequential": "Get the confirmed price in writing before proceeding with payment.",
    "soft_bait_compound": "Compare this listing's price and claims against two or three similar listings.",
}


# ---------------------------------------------------------------------------
# Per-category descriptions surfaced alongside the score breakdown.
# ---------------------------------------------------------------------------

BREAKDOWN_DESCRIPTIONS: Dict[str, Dict[str, str]] = {
    "seller_attributes": {
        "label": "Seller profile",
        "description": "Signals from the seller's account: age, response rate, ratings, and badges.",
    },
    "listing_metadata": {
        "label": "Listing details",
        "description": "Signals from price, photos, ratings, and other listing fields.",
    },
    "textual_nlp": {
        "label": "Description language",
        "description": "Signals from the wording used in the listing's description and specs.",
    },
    "url_domain": {
        "label": "Web address",
        "description": "Signals from the URL itself — domain, security, and structure.",
    },
}


# ---------------------------------------------------------------------------
# Platform-specific label overrides.
# When a flag fires for a known platform, use the platform-specific label
# so it reads naturally ("This Shopee seller..." rather than "The seller...").
# Keys: (flag_string, platform) → overridden label string.
# Only the `label` field is overridden; code/severity/tip stay the same.
# ---------------------------------------------------------------------------

PLATFORM_FLAG_LABELS: Dict[tuple, str] = {
    # ---- Shopee ----
    ("Seller name not available", "shopee"): (
        "The seller's display name was not visible on this Shopee page."
    ),
    ("Seller recently joined the platform", "shopee"): (
        "This Shopee seller account was created recently and has not yet built a sales history."
    ),
    ("Seller account under 30 days old", "shopee"): (
        "This Shopee seller account is less than 30 days old with very limited sales history."
    ),
    ("Seller account under 90 days old", "shopee"): (
        "This Shopee seller account is less than 90 days old and is still building its track record."
    ),
    ("Very low seller response rate", "shopee"): (
        "The seller's response rate on Shopee is below the platform average for established sellers."
    ),
    ("Below-average seller response rate", "shopee"): (
        "This Shopee seller responds to buyer messages less frequently than most established sellers."
    ),
    ("Perfect rating with very few reviews", "shopee"): (
        "This Shopee listing has a perfect 5-star rating but fewer than 10 reviews, which is uncommon for established products."
    ),
    ("Price unusually low compared to typical market", "shopee"): (
        "The price on this Shopee listing is notably lower than what is typically seen for similar items."
    ),
    ("Zero recorded sales", "shopee"): (
        "This Shopee listing shows no recorded sales yet, so there is no buyer history to reference."
    ),
    # ---- Lazada ----
    ("Seller name not available", "lazada"): (
        "The seller's display name was not visible on this Lazada page."
    ),
    ("Seller recently joined the platform", "lazada"): (
        "This Lazada seller account was created recently and may not have an established sales record."
    ),
    ("Seller account under 30 days old", "lazada"): (
        "This Lazada seller account is less than 30 days old with no significant sales history yet."
    ),
    ("Seller account under 90 days old", "lazada"): (
        "This Lazada seller account is relatively new and is still building its track record on the platform."
    ),
    ("Very low seller rating", "lazada"): (
        "This Lazada seller's rating is below the threshold typically associated with reliable sellers."
    ),
    ("Below-average seller rating", "lazada"): (
        "This Lazada seller's rating is lower than the platform average for established sellers."
    ),
    ("Perfect rating with very few reviews", "lazada"): (
        "This Lazada listing shows a perfect rating but has fewer than 10 reviews — worth checking further."
    ),
    ("Price unusually low compared to typical market", "lazada"): (
        "The price on this Lazada listing appears significantly lower than similar items on the platform."
    ),
    # ---- Facebook ----
    ("Seller name not available", "facebook"): (
        "The seller's name was not visible on this Facebook Marketplace listing."
    ),
    ("Seller recently joined the platform", "facebook"): (
        "This Facebook Marketplace seller has no visible review history, which is common among first-time sellers."
    ),
    ("Seller account under 30 days old", "facebook"): (
        "This Facebook Marketplace seller account appears to be very new with no established track record."
    ),
    ("Item condition not specified", "facebook"): (
        "The item condition was not specified by the seller, which makes it harder to assess the listing accurately."
    ),
    ("Listing posted very recently (under 24h)", "facebook"): (
        "This Facebook Marketplace listing was posted very recently and has no buyer interaction history yet."
    ),
    ("Price unusually low compared to typical market", "facebook"): (
        "The price on this Facebook Marketplace listing is notably low compared to similar items."
    ),
    ("No product images provided", "facebook"): (
        "This Facebook Marketplace listing has no photos attached, making it difficult to verify the item."
    ),
    ("Facebook Marketplace: no platform buyer protection or seller verification", "facebook"): (
        "Facebook Marketplace does not offer the buyer protections available on Shopee or Lazada — "
        "there is no platform-managed escrow, return guarantee, or formal seller verification."
    ),
    ("Price Transparency Risk: single-digit price may be a placeholder — confirm actual price with seller", "facebook"): (
        "The listed price is a single digit, which is almost certainly a placeholder — "
        "confirm the real price with the seller before proceeding."
    ),
    ("Price Transparency Risk: repeated-digit price pattern may indicate a placeholder — confirm actual price with seller", "facebook"): (
        "The listed price follows a repeated-digit pattern (e.g. 1111, 9999), a common placeholder "
        "on Facebook Marketplace — confirm the actual price with the seller."
    ),
    ("Price Transparency Risk: sequential-digit price may indicate a placeholder — confirm actual price with seller", "facebook"): (
        "The listed price uses a sequential number pattern (e.g. 1234, 12345), a common placeholder "
        "on Facebook Marketplace — confirm the actual price with the seller."
    ),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def enrich_flags(
    flags: List[str],
    platform: str = "",
    triggered_by: Dict[str, str] | None = None,
) -> List[Dict[str, str]]:
    """Convert raw flag strings into structured objects with code/severity/tip.

    Pass `platform` to get platform-specific label wording where available.
    Pass `triggered_by` (flag_string -> matched phrase) to include the exact
    text excerpt that fired each text-based flag — only populated for NLP flags.
    Unknown flags fall back to a generic informational entry so the API
    contract stays stable when new flags are added before this registry
    is updated.
    """
    out: List[Dict[str, str]] = []
    seen: Set[str] = set()
    plat = (platform or "").lower()
    tb = triggered_by or {}
    for f in flags:
        if f in seen:
            continue
        seen.add(f)
        meta = FLAG_INSIGHTS.get(f)
        # Platform-specific label override takes priority over generic label
        label = PLATFORM_FLAG_LABELS.get((f, plat), f)
        entry: Dict[str, str] = {}
        if meta is None:
            entry = {
                "code": "informational",
                "category": "general",
                "severity": "low",
                "label": label,
                "tip": "This is an informational signal. Take it as one data point alongside your own judgment.",
                "explanation": "Consider this observation as context when evaluating the listing.",
            }
        else:
            entry = {
                "code": meta["code"],
                "category": meta["category"],
                "severity": meta["severity"],
                "label": label,
                "tip": meta["tip"],
                "explanation": EXPLANATIONS_BY_CODE.get(meta["code"], ""),
            }
        # Only include triggered_by for text-category flags where we have a match
        phrase = tb.get(f)
        if phrase and entry.get("category") in ("text", "general"):
            entry["triggered_by"] = phrase
        out.append(entry)
    return out


def codes_from_flags(flags: List[str]) -> Set[str]:
    """Return the set of insight codes that correspond to the given flags."""
    codes: Set[str] = set()
    for f in flags:
        meta = FLAG_INSIGHTS.get(f)
        if meta:
            codes.add(meta["code"])
    return codes


def build_recommendations(flags: List[str], limit: int = 6) -> List[str]:
    """Deduplicated, ordered list of short suggestions tied to flags that
    actually fired. Returns at most `limit` items so the UI stays digestible.
    """
    codes = codes_from_flags(flags)
    seen: Set[str] = set()
    recs: List[str] = []
    # Preserve flag order for relevance
    for f in flags:
        meta = FLAG_INSIGHTS.get(f)
        if not meta:
            continue
        rec = RECOMMENDATIONS_BY_CODE.get(meta["code"])
        if rec and rec not in seen:
            seen.add(rec)
            recs.append(rec)
        if len(recs) >= limit:
            break
    return recs


def build_verify_checklist(flags: List[str], level: str, limit: int = 5) -> List[str]:
    """Short checklist of verification steps. Only populated for Medium/High
    risk bands so we don't nag users on low-risk listings.
    """
    if level not in ("Medium", "High"):
        return []
    seen: Set[str] = set()
    items: List[str] = []
    for f in flags:
        meta = FLAG_INSIGHTS.get(f)
        if not meta:
            continue
        item = CHECKLIST_BY_CODE.get(meta["code"])
        if item and item not in seen:
            seen.add(item)
            items.append(item)
        if len(items) >= limit:
            break
    return items


def dynamic_risk_message(flags: List[str], level: str) -> str:
    """Build a specific, flag-driven risk message naming the top two signals.

    Selects the two highest-weight flags, names them in plain language, and
    adds one contextual action sentence. Never uses "scam", "fraud", or "fake".
    """
    if not flags:
        return {
            "Very Low": (
                "This listing does not show strong observable risk signals based on "
                "the available information. Standard buying caution still applies as "
                "the system can only assess publicly visible data."
            ),
            "Low": (
                "A few minor signals were noted. Reviewing the listing details before "
                "purchasing is generally enough."
            ),
            "Medium": (
                "Several signals are worth a closer look before purchasing. "
                "The flags below highlight what may be worth confirming."
            ),
            "High": (
                "Multiple signals are present. The checklist below outlines simple "
                "steps you can take before committing to a purchase."
            ),
        }.get(level, "")

    # Score each flag by weight
    weighted: List[tuple] = []
    for f in flags:
        meta = FLAG_INSIGHTS.get(f)
        if meta:
            code = meta["code"]
            override = _CODE_WEIGHT_OVERRIDE.get(code)
            weight = override if override is not None else _SEVERITY_WEIGHT.get(meta["severity"], 1)
            weighted.append((weight, f, code))
    weighted.sort(key=lambda x: -x[0])

    top = weighted[:2]
    if not top:
        return contextual_risk_message(level, flags)

    names = [_FLAG_PLAIN_NAMES.get(t[2], t[1].lower()) for t in top]
    top_codes = {t[2] for t in top}

    # Pick a contextual action sentence
    if top_codes & {"url_typo", "url_no_https", "url_malformed"}:
        action = "Verify that you are on the official platform domain before entering any login or payment details."
    elif "payment_pressure" in top_codes:
        action = "Use the platform's official checkout when possible — it provides buyer protection if anything goes wrong."
    elif top_codes & {"seller_new", "seller_under_30d"}:
        action = "A short message to the seller and a look at their other listings can give a fuller picture before deciding."
    elif top_codes & {"comments_rating_text_mismatch", "comments_review_burst", "comments_ml_signal"}:
        action = "Read the actual review text to form your own view before relying on the star rating alone."
    elif "price_low" in top_codes:
        action = "Compare with similar listings and ask the seller to confirm the product condition and what is included."
    else:
        action = "Review the signals listed below and consider verifying key details with the seller before purchasing."

    if len(names) == 1:
        signal_text = f"This listing shows {names[0]}."
    else:
        signal_text = f"This listing shows {names[0]} and {names[1]}."

    return (
        f"{signal_text} "
        f"These are observable signals worth noting when evaluating this listing. "
        f"{action}"
    )


def contextual_risk_message(level: str, flags: List[str]) -> str:
    """Kept for backward compatibility. New code should use dynamic_risk_message."""
    codes = codes_from_flags(flags)

    # Highest-priority specific messages first.
    if "url_typo" in codes or "url_no_https" in codes or "url_malformed" in codes:
        return (
            "Web-address signals were detected. Confirm you're on the "
            "official platform's domain before entering any login or "
            "payment details."
        )
    if "payment_pressure" in codes and level in ("Medium", "High"):
        return (
            "The listing mentions specific payment conditions. Whenever "
            "possible, prefer the platform's official checkout — it adds "
            "buyer protection if anything goes wrong."
        )
    if ("seller_new" in codes or "seller_under_30d" in codes) and level in ("Medium", "High"):
        return (
            "Several signals point to a relatively new seller account. "
            "A short message to the seller and a quick look at their "
            "other listings can give you a fuller picture before deciding."
        )
    if "urgency_language" in codes and level in ("Medium", "High"):
        return (
            "The listing uses time-pressure wording. There's no need to "
            "rush — comparing similar listings often shows the same item "
            "is widely available."
        )
    if "price_low" in codes and level in ("Medium", "High"):
        return (
            "The price is noticeably below typical market values, alongside "
            "other signals worth checking. Comparing with similar listings "
            "helps confirm what's included."
        )

    # Fallbacks per band — kept neutral.
    return {
        "Very Low": (
            "Few notable signals were detected. Continue with the usual "
            "online-shopping common sense."
        ),
        "Low": (
            "A few minor signals were noted. Reviewing the listing's "
            "details before purchasing is generally enough."
        ),
        "Medium": (
            "Several signals are worth a closer look before purchasing. "
            "The tips below highlight what may be worth confirming."
        ),
        "High": (
            "Multiple signals are present that may be worth verifying "
            "before committing. The checklist below outlines simple "
            "steps you can take."
        ),
    }.get(level, "")


def comment_summary(
    bot: float,
    fake: float,
    flags: List[str],
    comments_analyzed: int,
) -> str:
    """One-sentence plain-language summary of the comments analysis. Stays
    descriptive and avoids declaring reviews fake outright.
    """
    if comments_analyzed == 0:
        return (
            "No comments were available for analysis. Reading whatever "
            "reviews are visible on the page is still useful."
        )
    if not flags and bot < 0.2 and fake < 0.2:
        return (
            "The captured comments appear largely organic — no notable "
            "patterns were detected."
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


def comment_pattern_summary(
    flags: List[str],
    n: int,
    bot: float,
    fake: float,
) -> str:
    """Build a cohesive plain-language summary of what the combined comment
    patterns mean together — not just a list of separate observations.
    """
    if n == 0:
        return (
            "No reviews were collected during this scan. Run a Comments Scan "
            "or Deep Scan while on a listing with buyer reviews to enable "
            "comment analysis."
        )
    if n < 5:
        return (
            f"Only {n} review{'s' if n != 1 else ''} {'were' if n != 1 else 'was'} collected "
            "which is too few to identify reliable patterns. Navigate through more comment "
            "pages or switch between rating tabs to collect a larger sample for a more "
            "reliable assessment."
        )

    flag_set = set(flags)
    has_5star = bool(flag_set & {
        "All rated reviews are exactly 5-star (suspiciously uniform)",
        "All collected reviews are 4–5 star — no critical ratings found",
    })
    has_dup = "High duplicate-text ratio across comments" in flag_set
    has_no_specifics = "Comments lack shipping or product specifics" in flag_set
    has_cluster = bool(flag_set & {
        "Multiple comments posted within a 60-minute window",
        "Most comments cluster on a single date",
    })
    has_burst = "Majority of reviews posted within a 7-day burst" in flag_set
    has_ml = "Classifier indicates elevated fake-review probability" in flag_set
    has_mismatch = "High-rated reviews contain negative language" in flag_set
    has_generic = "Generic phrases dominate comments" in flag_set

    if has_dup and (has_5star or has_generic):
        return (
            "Several collected reviews contain very similar or identical text, "
            "and most are 5-star ratings with little product-specific detail. "
            "This combination is associated with coordinated review activity. "
            "The review scores may not fully reflect genuine buyer experiences — "
            "look for reviews that describe the actual product or delivery."
        )
    if has_dup:
        return (
            "Several collected reviews contain very similar or identical text. "
            "This pattern is associated with coordinated review posting. "
            "The review scores may not fully reflect genuine buyer experiences."
        )
    if has_burst and has_5star:
        return (
            "The majority of reviews were posted within a single short window "
            "and nearly all are 5-star ratings. Genuine buyer feedback typically "
            "accumulates over time from different buyers. "
            "Interpret the rating score with this context in mind."
        )
    if has_burst:
        return (
            "The majority of reviews were posted within a single 7-day window. "
            "Genuine buyer activity typically accumulates over weeks and months. "
            "Look for reviews spread across different time periods for a more balanced view."
        )
    if has_mismatch:
        return (
            "Some reviews are rated 5 stars but contain wording that suggests "
            "the buyer experienced a problem with the product. This mismatch "
            "is worth noting when relying on the star rating. "
            "Read the full text of several reviews to form your own view."
        )
    if has_ml and (has_5star or has_no_specifics):
        return (
            "The review-pattern analysis flagged several signals associated with "
            "inflated reviews — including rating uniformity and limited product-specific detail. "
            "These are probabilistic signals, not confirmed findings. "
            "Reading the actual review text yourself gives the most reliable picture."
        )
    if has_5star and has_no_specifics and n < 15:
        return (
            f"Only {n} reviews were collected, which is a small sample for this listing. "
            "All collected reviews are 5-star and none mention specific details like "
            "delivery experience or product condition. This combination is commonly "
            "observed in listings with limited genuine buyer history. "
            "The review scores should be interpreted with this context in mind."
        )
    if has_5star and has_no_specifics:
        return (
            "All collected reviews are 5-star and none describe specific product "
            "or delivery details. While this could reflect genuine satisfaction, "
            "reviews that only give a perfect rating without detail are harder to "
            "assess independently. Reading several reviews carefully can help."
        )
    if has_cluster:
        return (
            "Several reviews were posted within a very short time window. "
            "Organic buyer reviews typically accumulate gradually over time. "
            "This clustering pattern is worth noting when evaluating the review history."
        )
    if not flags and bot < 0.2 and fake < 0.2:
        return (
            "The collected reviews include a variety of ratings and mention specific "
            "details like delivery time and product condition. These characteristics "
            "are commonly found in genuine buyer feedback."
        )
    return (
        "A few patterns are worth noting in the collected reviews. "
        "The flags below explain what stood out — reading the actual review "
        "text alongside these signals gives the most reliable picture."
    )
# ---------------------------------------------------------------------------

_THEMES: Dict[str, Dict] = {
    "delivery_speed": {
        "label": "Delivery Speed",
        "keywords": [
            "fast", "quick", "mabilis", "speedy", "agad", "maaga", "arrived", "on time",
            "ontime", "delivered", "delivery", "shipping", "shipped", "slow", "late",
            "delayed", "nalate", "matagal", "tagal", "hours", "days", "week",
        ],
        "negative_keywords": ["slow", "late", "delayed", "nalate", "matagal", "tagal"],
    },
    "product_quality": {
        "label": "Product Quality",
        "keywords": [
            "quality", "kalidad", "maayos", "maganda", "ganda", "nice", "good",
            "okay", "ok", "ok naman", "broken", "sira", "defective", "damaged",
            "poor quality", "bad quality", "substandard", "hindi maganda",
            "hindi maayos", "rough", "cheap", "flimsy", "durable", "sturdy",
            "matibay", "tibay", "marupok",
        ],
        "negative_keywords": [
            "broken", "sira", "defective", "damaged", "poor quality", "bad quality",
            "substandard", "hindi maganda", "hindi maayos", "rough", "flimsy",
            "cheap", "marupok",
        ],
    },
    "authenticity": {
        "label": "Authenticity",
        "keywords": [
            "original", "authentic", "legit", "genuine", "tunay", "totoo", "real",
            "fake", "peke", "replika", "replica", "imitation", "counterfeit",
            "not original", "hindi original", "mukhang fake",
        ],
        "negative_keywords": [
            "fake", "peke", "replika", "replica", "imitation", "counterfeit",
            "not original", "hindi original", "mukhang fake",
        ],
    },
    "packaging": {
        "label": "Packaging",
        "keywords": [
            "packaging", "pakete", "box", "kahon", "bubble wrap", "wrapped",
            "well packed", "packed", "sealed", "intact", "secure",
            "crushed", "open", "damaged box", "torn", "bukas", "basag",
        ],
        "negative_keywords": [
            "crushed", "damaged box", "torn", "bukas", "basag", "open",
        ],
    },
    "seller_communication": {
        "label": "Seller Communication",
        "keywords": [
            "seller", "tindera", "vendor", "responsive", "nagreply", "nag-reply",
            "replied", "reply", "communication", "helpful", "accommodating",
            "kind", "mabait", "maayos", "ignored", "no reply", "walang sagot",
            "hindi nagreply", "scammer", "hindi tumugon",
        ],
        "negative_keywords": [
            "ignored", "no reply", "walang sagot", "hindi nagreply", "scammer",
            "hindi tumugon",
        ],
    },
    "listing_accuracy": {
        "label": "Listing Accuracy",
        "keywords": [
            "as described", "as pictured", "same as picture", "kapareho",
            "exactly", "accurate", "tama", "hindi kapareho", "different",
            "not as described", "not as pictured", "misleading", "mali",
            "wrong item", "maling item", "ibang item",
        ],
        "negative_keywords": [
            "hindi kapareho", "different", "not as described", "not as pictured",
            "misleading", "mali", "wrong item", "maling item", "ibang item",
        ],
    },
    "overall_satisfaction": {
        "label": "Overall Satisfaction",
        "keywords": [
            "satisfied", "happy", "masaya", "worth it", "sulit", "recommend",
            "irerecommend", "i-recommend", "will buy again", "bibili ulit",
            "disappointed", "hindi sulit", "not worth", "sayang", "regret",
            "hindi na bibili", "hindi nagustuhan", "maganda", "ayos",
        ],
        "negative_keywords": [
            "disappointed", "hindi sulit", "not worth", "sayang", "regret",
            "hindi na bibili", "hindi nagustuhan",
        ],
    },
}

_NEGATIVE_QUALIFIERS = {
    "hindi", "not", "never", "broken", "fake", "sira", "mali", "wrong",
    "late", "delay", "delayed", "bad", "poor", "disappointed",
}

_DISCLAIMER = (
    "This summary reflects patterns observed in publicly visible buyer comments "
    "and should be used as a general guide only."
)


def extract_comment_themes(comments: List[Dict]) -> Dict:
    """Analyse comment texts for recurring themes using keyword matching.

    Returns a dict with:
      - themes_detected: list of theme dicts (only themes seen in ≥2 comments)
      - summary_text: 1-2 plain sentences covering the top themes
      - disclaimer: fixed advisory string
    """
    texts = [
        (c.get("text") or "").strip().lower()
        for c in comments
        if (c.get("text") or "").strip()
    ]

    if len(texts) < 5:
        return {
            "themes_detected": [],
            "summary_text": (
                "Not enough reviews were collected to identify meaningful patterns."
            ),
            "disclaimer": _DISCLAIMER,
        }

    # Count per-theme hits and detect sentiment
    theme_counts: Dict[str, int] = {}
    theme_negative: Dict[str, int] = {}

    for theme_key, theme_meta in _THEMES.items():
        pos_kws = theme_meta["keywords"]
        neg_kws = set(theme_meta["negative_keywords"])
        hit_count = 0
        neg_count = 0
        for text in texts:
            hit = any(kw in text for kw in pos_kws)
            if not hit:
                continue
            hit_count += 1
            # Negative qualifier near a negative keyword
            has_neg = any(q in text for q in _NEGATIVE_QUALIFIERS) and any(
                nk in text for nk in neg_kws
            )
            if has_neg:
                neg_count += 1
        theme_counts[theme_key] = hit_count
        theme_negative[theme_key] = neg_count

    # Build output — only themes with ≥2 mentions
    detected = []
    for theme_key, count in sorted(theme_counts.items(), key=lambda x: -x[1]):
        if count < 2:
            continue
        neg = theme_negative[theme_key]
        if neg == 0:
            sentiment = "positive"
        elif neg >= count * 0.5:
            sentiment = "negative"
        else:
            sentiment = "mixed"
        detected.append({
            "theme": theme_key,
            "label": _THEMES[theme_key]["label"],
            "mention_count": count,
            "sentiment": sentiment,
        })

    # Build summary_text from top 2-3 themes
    summary_text = _build_theme_summary(detected, len(texts))

    return {
        "themes_detected": detected,
        "summary_text": summary_text,
        "disclaimer": _DISCLAIMER,
    }


def _build_theme_summary(detected: List[Dict], total: int) -> str:
    if not detected:
        return (
            "No recurring themes were identified in the available reviews."
        )

    top = detected[:3]
    parts = []
    for t in top:
        label = t["label"].lower()
        count = t["mention_count"]
        sentiment = t["sentiment"]
        share = int(round(count / total * 100)) if total else 0

        if sentiment == "positive":
            parts.append(f"{count} review{'s' if count != 1 else ''} mention {label} positively ({share}%)")
        elif sentiment == "negative":
            parts.append(f"{count} review{'s' if count != 1 else ''} raise concerns about {label} ({share}%)")
        else:
            parts.append(f"{count} review{'s' if count != 1 else ''} mention {label} with mixed feedback ({share}%)")

    if len(parts) == 1:
        return parts[0].capitalize() + "."
    sentence1 = parts[0].capitalize() + "."
    sentence2 = " ".join(p.capitalize() for p in parts[1:]) + "."
    return f"{sentence1} {sentence2}"


def enriched_breakdown(breakdown: Dict[str, int]) -> Dict[str, Dict]:
    """Wrap the numeric breakdown with category labels and descriptions."""
    out: Dict[str, Dict] = {}
    for key, score in breakdown.items():
        meta = BREAKDOWN_DESCRIPTIONS.get(key, {
            "label": key.replace("_", " ").title(),
            "description": "",
        })
        out[key] = {
            "score": score,
            "label": meta["label"],
            "description": meta["description"],
        }
    return out
