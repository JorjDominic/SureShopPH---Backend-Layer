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
        "code": "no_sales",
        "category": "metadata",
        "severity": "low",
        "tip": (
            "No completed sales are shown for this listing yet. New "
            "listings often start this way; you may simply be among the "
            "first buyers."
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
    "Lazada specifications missing": {
        "code": "specs_missing_lazada",
        "category": "text",
        "severity": "low",
        "tip": (
            "The specifications section is empty. The seller may still "
            "provide details on request — a quick message can fill in "
            "the gaps."
        ),
    },
    "Shopee specifications missing": {
        "code": "specs_missing_shopee",
        "category": "text",
        "severity": "low",
        "tip": (
            "The specifications section is empty. Ask the seller for the "
            "details that matter most for your purchase."
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
            "This page is not using a secure (HTTPS) connection. Avoid "
            "entering payment or account information here."
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
    "All comments are 5-star": {
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
    "No negative or mixed ratings detected among all reviews": {
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
    "url_no_https": "Avoid entering payment or login details on a non-secure page.",
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
    "payment_pressure": "Pay through the platform's official checkout — avoid direct GCash or bank transfers.",
    "url_malformed": "Type the official platform URL into the browser yourself.",
    "url_typo": "Verify the domain in the address bar matches the official platform.",
    "url_no_https": "Do not enter login or payment details on this page.",
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
            }
        else:
            entry = {
                "code": meta["code"],
                "category": meta["category"],
                "severity": meta["severity"],
                "label": label,
                "tip": meta["tip"],
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


def contextual_risk_message(level: str, flags: List[str]) -> str:
    """Produce a band-appropriate message that mentions the most relevant
    finding when one exists. Wording stays observational, never accusatory.
    """
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
