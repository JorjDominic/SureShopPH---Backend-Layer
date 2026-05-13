# SureShopPH Backend - Comprehensive Test Case Documentation

**Last Updated:** May 13, 2026  
**Status:** Corrected for Academic Rigor & Real-World Validation

---

## Table of Contents
1. [Pricing & Product Metadata](#1-pricing--product-metadata-test-cases)
2. [Seller Attributes](#2-seller-attributes-test-cases)
3. [Description & Text Patterns](#3-description--text-pattern-test-cases)
4. [URL & Domain](#4-url--domain-test-cases)
5. [Platform-Specific](#5-platform-specific-test-cases)
6. [Data Quality & Confidence](#6-data-quality--confidence-test-cases)
7. [Combined Scenarios](#7-combined-scenario-test-cases)
8. [Edge Cases & Error Handling](#8-edge-cases--error-handling-test-cases)
9. [Risk Score Bands (CORRECTED)](#9-risk-score-bands-test-cases-corrected)
10. [Score Breakdown Capping](#10-score-breakdown-capping-test-cases)
11. [Deep Scan Specific Cases](#11-deep-scan-specific-test-cases)
12. [Rating Filter Tooltip Tests](#12-rating-filter-tooltip-tests-new)
13. [Comment Summarizer Tests](#13-comment-summarizer-tests-new)
14. [Product Notice Tests](#14-product-notice-tests-new)
15. [Scan Mode Platform Tests](#15-scan-mode-platform-tests-new)
16. [Positive Signal Test Cases (CRITICAL)](#16-positive-signal-test-cases-new--critical)
17. [Taglish & Mixed-Language NLP Tests](#17-taglish--mixed-language-nlp-tests-new--critical)

---

## 1. PRICING & PRODUCT METADATA TEST CASES

| Input Scenario | Expected Behavior | Score Impact |
|---|---|---|
| **Low Pricing + Missing Description** | Both flags triggered; score increase | +8pts (low price) + 10pts (missing desc) |
| **Price = ₱0 without "free" keyword** | Flagged as suspicious | +8pts |
| **Price = ₱150 (below ₱200 baseline)** | Flagged as suspiciously low | +10pts |
| **Price variant indicator set** | Facebook-specific flag | +5pts |
| **No images provided** | Confidence reduced; flag added | +10pts |
| **1-2 images only** | Lower confidence | +5pts |
| **0 items sold / No sales history** | Flagged | +10pts (zero sales) or +8pts (no items) |
| **Perfect 5.0 rating with <10 reviews** | **Increases** risk (suspicious pattern) | +15pts |
| **Rating <3.5 stars** | Low seller credibility signal | +15pts |
| **Rating <4.0 stars** | Moderate concern signal | +8pts |
| **No ratings yet** | Explicit flag | +14pts |
| **Description <20 characters** | Too vague; insufficient info | +10pts |

---

## 2. SELLER ATTRIBUTES TEST CASES

| Input Scenario | Expected Behavior | Score Impact |
|---|---|---|
| **Missing seller name** | Major red flag | +15pts |
| **Recently joined** | Shop age = 0 days | +15pts |
| **Account age <30 days** | New, untrusted seller | +15pts |
| **Account age <90 days** | Still new | +8pts |
| **Response rate <50%** | Poor communication signal | +10pts |
| **Response rate <80%** | Moderate concern signal | +5pts |
| **Lazada seller rating <70%** | Poor rating signal | +15pts |
| **Lazada seller rating <85%** | Below acceptable signal | +8pts |
| **Shopee/Lazada Mall seller** | Verified, trustworthy | **-10pts** (positive signal) |
| **Top Seller badge** | Established seller signal | **-5pts** (positive signal) |
| **Preferred Seller badge** | Trusted status signal | **-5pts** (positive signal) |

---

## 3. DESCRIPTION & TEXT PATTERN TEST CASES

### Urgency Language Detected
| Phrases | Score Impact | Example | Category |
|---|---|---|---|
| "limited stocks", "bili na", "huli na", "rush", "last piece", "paubos na", "flash sale" | +10pts | "Limited stocks na! Bili na!" | Urgency Signals |

### Over-Promising Language
| Phrases | Score Impact | Example | Category |
|---|---|---|---|
| "100% legit", "guaranteed", "original na original", "no issues", "authentic po", "sealed", "brand new sealed" | +10pts | "100% original sealed guaranteed!" | Over-promising Signals |

### Payment Pressure
| Phrases | Score Impact | Example | Category |
|---|---|---|---|
| "COD only", "GCash muna", "no returns", "downpayment first", "full payment required", "no cancel" | +10pts | "GCash muna, walang cancel" | Payment Pressure Signals |

### Vague Branding
| Phrases | Score Impact | Example | Category |
|---|---|---|---|
| "generic", "no brand", "walang brand", "chinese brand", "local brand", "no name brand" | +5pts | "Walang brand, quality item" | Vague Branding Signals |

---

## 4. URL & DOMAIN TEST CASES

| Input Scenario | Expected Behavior | Score Impact |
|---|---|---|
| **Typosquatting detected** (e.g., "shoope", "lazadaa", "f4cebook") | Major phishing red flag | +25pts |
| **Non-HTTPS URL** | Insecure connection signal | +10pts |
| **Unusually deep subdomain** (>2 levels from base, e.g., `a.b.c.example.com`) | Suspicious structure signal | +10pts |
| **Malformed URL** | Cannot be parsed | +25pts |

---

## 5. PLATFORM-SPECIFIC TEST CASES

### SHOPEE

| Input Scenario | Expected Behavior | Score Impact |
|---|---|---|
| **All 6 fields present** | High confidence (≥5 fields) | Confidence = "High" (100%) |
| **3-4 fields present** | Moderate confidence | Confidence = "Moderate" |
| **<3 fields present** | Low confidence | Confidence = "Low" |
| **Shopee Mall indicator = true** | Verified store signal | -10pts |
| **Regular seller (not mall)** | Generic seller | Normal scoring |

### LAZADA

| Input Scenario | Expected Behavior | Score Impact |
|---|---|---|
| **Seller rating <70%** | Poor performance signal | +15pts |
| **Seller rating 70-85%** | Below average signal | +8pts |
| **LazMall badge present** | Official store signal | -10pts |
| **Multiple badges (Top Seller, Preferred)** | Each badge reduces risk | -5pts each |

### FACEBOOK

| Input Scenario | Expected Behavior | Score Impact |
|---|---|---|
| **Only 4 required fields present** (vs 5+ for Shopee/Lazada) | Platform-aware calculation | Adjusted confidence calculation |
| **Condition field missing** | Required metadata gap | +5pts |
| **Price variant = true** | Variable pricing signal | +5pts |
| **Listed <24 hours ago** | Very new listing signal | +8pts |
| **Auto-generated description pattern detected** | Lazy seller signal (pattern-based) | +8pts |
| **No seller ratings available** | Facebook limitation | Note: "Ratings not available on Facebook" |

---

## 6. DATA QUALITY & CONFIDENCE TEST CASES (CORRECTED)

### Confidence Calculation Method
Confidence percentage = (fields_present / total_fields) × 100

### By Platform - Actual Field Count Examples

#### Shopee Platform
| Fields Present | Total Fields | Percentage | Confidence Level |
|---|---|---|---|
| 6 | 6 | 100% | **High** |
| 5 | 6 | 83% | **High** |
| 4 | 6 | 67% | **Moderate** |
| 3 | 6 | 50% | **Moderate** |
| 2 | 6 | 33% | **Low** |
| 1 | 6 | 17% | **Low** |
| 0 | 6 | 0% | **Low** |

#### Lazada Platform
| Fields Present | Total Fields | Percentage | Confidence Level |
|---|---|---|---|
| 6 | 6 | 100% | **High** |
| 5 | 6 | 83% | **High** |
| 4 | 6 | 67% | **Moderate** |
| 3 | 6 | 50% | **Moderate** |
| 2 | 6 | 33% | **Low** |

#### Facebook Platform
| Fields Present | Total Fields | Percentage | Confidence Level |
|---|---|---|---|
| 4 | 4 | 100% | **High** |
| 3 | 4 | 75% | **High** |
| 2 | 4 | 50% | **Moderate** |
| 1 | 4 | 25% | **Low** |
| 0 | 4 | 0% | **Low** |

### Confidence Trust Multiplier Application

| Scenario | Field Quality Distribution | Trust Multiplier | Example Impact |
|---|---|---|---|
| **All high-confidence fields** | Seller score 25pts, all high | 1.0× | Final: 25pts |
| **Mix of high/medium** | Seller score 25pts, 50% medium | 0.85× | Final: ~21pts |
| **All medium-confidence fields** | Seller score 25pts, all medium | 0.7× | Final: ~18pts |
| **Mix of medium/low** | Seller score 25pts, 50% low | 0.55× | Final: ~14pts |
| **All low-confidence fields** | Seller score 25pts, all low | 0.4× | Final: ~10pts |

---

## 7. COMBINED SCENARIO TEST CASES

| Scenario | Expected Score Range | Risk Level | Rationale |
|---|---|---|---|
| **New seller + Missing description + Low price + No reviews** | 70-85 | **High** | Multiple signal indicators present |
| **New seller + Missing description + Low price + 5.0 rating (<10 reviews)** | 75-90 | **High** | Suspicious pattern detected |
| **Established seller + Full details + Good rating + High price** | 5-20 | **Very Low** | Positive indicators present |
| **Mall seller + Good details + Good rating** | 0-15 | **Very Low** | Multiple positive trust signals |
| **Typosquatted URL + Low price + Missing description** | 85-100 | **High** | Security/phishing indicators present |
| **Non-HTTPS + Payment pressure patterns + No seller name** | 80-95 | **High** | Security and behavioral concern signals |
| **Perfect 5.0 rating + <10 reviews + Low price + Urgency language** | 70-85 | **High** | Statistical anomaly detected |

---

## 8. EDGE CASES & ERROR HANDLING TEST CASES

| Input Scenario | Expected Behavior | Response |
|---|---|---|
| **Empty payload {}** | Graceful fallback | risk_score = 0, all scores = 0, empty flags |
| **Missing platform field** | Use default field sets | Process gracefully with note |
| **Malformed shop_age string** | Safe parsing | Returns None, no penalty |
| **Invalid response_rate** | Skip that rule | No error, just skip |
| **Null/zero confidence fields** | Treated as missing | Confidence % reduced |
| **No comments provided for deep scan** | Note: "No comments available" | Process only listing portion |
| **<10 comments for analysis** | Flag: "small_sample_warning" | Process with caution note |
| **Invalid JWT token** | 401 Unauthorized | Authentication fails |
| **Invalid activation key format** | 400 Bad Request | Validation fails |
| **Payload >1 MB** | 413 Payload Too Large | Request rejected |
| **Rate limit exceeded** | 429 Too Many Requests | Throttled response |
| **Same idempotency key, different payload** | Return cached result from first request | Replay protection |

---

## 9. RISK SCORE BANDS TEST CASES (CORRECTED)

### Corrected Messages — Probabilistic Framing

**NOTE:** All messages use probabilistic language describing detected signals, not verdict-based claims. The system cannot confirm legitimacy; it can only report signal presence or absence.

| Risk Score Range | Risk Level | Risk Color | Message (CORRECTED) |
|---|---|---|---|
| **0-25** | Very Low | Green | "No strong risk signals detected. Standard buying caution applies." |
| **26-50** | Low | Yellow | "Minor observable signals detected. Review the indicators and proceed with your own judgment." |
| **51-75** | Medium | Orange | "Multiple observable signals detected. Consider verifying key details with the seller before purchasing." |
| **76-100** | High | Red | "Several high-weight signals detected. Take time to review all indicators carefully before making any payment." |

**Rationale for Correction:** 
- Removed "Legitimate seller" verdict claim
- Removed "Avoid or verify extensively" prescriptive language
- Replaced with descriptive signal-based framing
- Maintains buyer agency (their judgment, their decision)
- Aligns with system's stated probabilistic design

---

## 10. SCORE BREAKDOWN CAPPING TEST CASES

Each category has a **maximum contribution**. Caps are applied **before** confidence multipliers.

| Category | Max Points | Example: Multiple Flags | Note |
|---|---|---|---|
| **Seller Attributes** | 25pts | Missing name (+15) + Recently joined (+15) = 25pts capped | Before multiplier |
| **Listing Metadata** | 25pts | No images (+10) + No ratings (+14) + Low price (+10) = 25pts capped | Before multiplier |
| **Text/NLP** | 35pts | Missing desc (+10) + Urgency (+10) + Over-promising (+10) + Payment pressure (+10) = 35pts capped | Before multiplier |
| **URL/Domain** | 25pts | Typosquatting (+25) + Non-HTTPS (+10) = 25pts capped | Before multiplier |

### Score Capping + Confidence Multiplier Calculation (CLARIFIED)

**Calculation Order:** Raw Score → Category Cap → Apply Confidence Multiplier

**Example:**
- Seller attributes detected: Missing name (+15) + Recently joined (+15) = 30 raw points
- Apply category cap: 30 → 25pts (capped)
- Field confidence level: Medium (0.7 multiplier)
- Final seller contribution: 25 × 0.7 = **17.5pts** (rounds to 18pts)

**Key Point:** The confidence multiplier is applied *after* the category cap, so a heavily flagged category with low field confidence will contribute proportionally less to the final risk score.

---

## 11. DEEP SCAN SPECIFIC TEST CASES

### Deep Scan Combined Score Formula (JUSTIFIED)

**Formula:**
```
combined_score = (listing_score × 0.7) + (bot_likelihood_pct × 0.3)
```

**Weight Justification:**
The Deep Scan combined score weights the listing analysis at 70 percent and the comment analysis at 30 percent. This distribution reflects the greater informational completeness of listing metadata relative to comment samples, which are typically limited by the number of pages the user navigates during a scan. The 70/30 split ensures that incomplete comment samples do not disproportionately influence the final score, while still incorporating comment signals as a secondary validation layer.

### Test Cases

| Input Scenario | Expected Output | Calculation |
|---|---|---|
| **Listing score 50 + Bot likelihood 80%** | Combined = 59 (Medium) | (50 × 0.7) + (80 × 0.3) = 35 + 24 = 59 |
| **Listing score 30 + Fake reviews 70%** | Combined = 42 (Low) | (30 × 0.7) + (70 × 0.3) = 21 + 21 = 42 |
| **Listing score 10 + All comments legit (0% bot)** | Combined = 7 (Very Low) | (10 × 0.7) + (0 × 0.3) = 7 + 0 = 7 |
| **Listing score 80 + Bot likelihood 95%** | Combined = 84 (High) | (80 × 0.7) + (95 × 0.3) = 56 + 28.5 = 84.5 |
| **Listing score 20 + Fake reviews 60%** | Combined = 32 (Low) | (20 × 0.7) + (60 × 0.3) = 14 + 18 = 32 |
| **Duplicate reviews detected** | Flag: "Duplicate reviews detected" | Increases bot_likelihood_pct by 15-25% |
| **Clustered review dates** | Flag: "Reviews posted in clusters (suspicious)" | Pattern detected in timestamps |
| **Low review diversity** | Flag: "Low review diversity; most reviews use similar language" | Entropy analysis indicates uniformity |

---

## 12. RATING FILTER TOOLTIP TESTS (NEW)

These test cases verify that the rating filter tooltip appears at strategic moments without over-triggering.

| Condition | Expected Behavior | Notes |
|---|---|---|
| **3 pages collected, all 5-star** | Mid-scan tooltip appears in side panel | Alerts user to potential rating bias |
| **User switches to 3-star filter tab** | Positive reinforcement message shown | Confirms finding alternative perspectives |
| **Tooltip shown 3 times in session** | No more tooltips shown this session | Prevents notification fatigue |
| **Tooltip shown 3 times total** | Reset after 24 hours | Cross-session frequency cap |
| **Facebook Marketplace listing** | Tooltip never appears | Facebook lacks rating system |
| **Deep scan on Shopee** | Tooltip eligible during comments phase | Shows when reviewing comment sentiment |
| **User dismisses tooltip** | Tooltip not shown again for 1 hour | Respects user preference |

---

## 13. COMMENT SUMMARIZER TESTS (NEW)

These test cases validate that comment analysis correctly identifies themes and flags.

| Input Scenario | Expected Output | Validation |
|---|---|---|
| **20 reviews, mostly mention "fast delivery"** | Theme: "Delivery positive" detected | Positive indicator |
| **15 reviews, several mention "wrong item received"** | Theme: "Accuracy negative" detected | Concern indicator |
| **5 reviews all say "goods" or "ok"** | Small sample warning + generic reviews flagged | Low information value |
| **Mixed reviews with specific product details mentioned** | Genuine review pattern detected; diversity score >60 | Confidence: High |
| **All reviews have identical text** | Duplicate review flag + bot_likelihood increase by 25% | Likely fabricated |
| **Reviews mention same typos/grammar patterns** | Clustered authorship pattern detected | Potential duplicate author network |
| **Review dates all within 2-day window** | Clustered posting detected | Artificial inflation pattern |
| **10 reviews, 8 are 5-star, 1 is 3-star, 1 is 1-star** | Normal distribution, no flag | Genuine diversity |
| **50 reviews, 49 are 5-star, 1 is 1-star** | Rating diversity score low; flag triggered | Skewed distribution signal |

---

## 14. PRODUCT NOTICE TESTS (NEW)

These test cases verify that Product Notice logic correctly identifies when additional caution is warranted.

| Condition | Expected Output | Notes |
|---|---|---|
| **No brand mentioned in description** | Product Notice triggered | High-value items need brand verification |
| **Price below ₱200 for electronics category** | Product Notice triggered | Common counterfeiting target |
| **Brand clearly mentioned in description** | No Product Notice | Reduces counterfeiting likelihood |
| **Book listing with no publisher mentioned** | Product Notice triggered | ISBN/publisher verification recommended |
| **Generic item (e.g., "phone charger") with no brand** | No Product Notice | Generic items less likely to be counterfeit |
| **Luxury brand at <50% market price** | Product Notice triggered + price_variance flag | Counterfeiting indicator |
| **Fashion item with inconsistent size chart** | Product Notice triggered | Authenticity concern |

---

## 15. SCAN MODE PLATFORM TESTS (NEW)

These test cases verify platform-aware scan mode availability and behavior.

| Scenario | Expected Behavior | Platform Limitation |
|---|---|---|
| **Normal Scan on Facebook** | Runs successfully | Full listing analysis available |
| **Comments Scan on Facebook** | Disabled, shows platform notice | Facebook API limitations; ratings unavailable |
| **Deep Scan on Facebook** | Disabled, shows platform notice | Cannot combine with comments analysis |
| **Normal Scan on Shopee** | Runs full listing analysis | All fields available |
| **Deep Scan on Shopee with no comments** | Listing analysis only, shows "No comments available" note | Graceful degradation |
| **Comments-only Scan on Lazada** | Processes only comment sentiment analysis | Listing data not required |
| **Deep Scan on Lazada with 1 comment** | Processes with "small_sample_warning" | Insufficient data for statistical confidence |

---

## 16. POSITIVE SIGNAL TEST CASES (NEW - CRITICAL)

**Purpose:** Verify the system does not over-flag legitimate sellers. These test cases confirm fair treatment and prevent seller-side bias.

### High-Confidence Legitimate Scenarios

| Scenario | Expected Score | Expected Level | Rationale |
|---|---|---|---|
| **Shopee Mall seller + complete data (6 fields) + 4.5-star rating + 500 items sold** | 0-10 | Very Low | Multiple positive trust signals; established presence |
| **Lazada LazMall seller + all positive badges (Top Seller, Preferred) + 4.8-star rating** | 0-5 | Very Low | Highest verification tier; strong historical performance |
| **Established seller 2+ years on platform + 4.8-star rating + 200+ reviews** | 5-15 | Very Low | Long history demonstrates reliability |
| **Normal Shopee seller + all metadata complete + reasonable price (₱500-1000) + detailed 150-char description** | 10-25 | Very Low to Low | Good data quality without premium badges |
| **New seller (14 days old) but complete metadata + reasonable price + detailed 200+ char description + response rate 90%** | 20-35 | Low | Compensates for recency with exceptional data |
| **Facebook seller + all 4 required fields + recent listings (weekly) + fast response pattern in comments** | 15-30 | Low to Medium | Newer platform; limited history available |
| **Lazada seller + LazMall status + 4.7-star rating + <2% return rate** | 0-8 | Very Low | Official channel + operational excellence |
| **Shopee seller + 3-year history + response rate 95% + consistently 4.6+ ratings** | 0-12 | Very Low | Long-term pattern of reliability |

### Medium-Confidence Legitimate Scenarios

| Scenario | Expected Score | Expected Level | Rationale |
|---|---|---|---|
| **Newer established seller (8 months) + 4.2-star rating + 50 items sold + complete metadata** | 20-40 | Low | Good track record despite relative newness |
| **Small seller + high response rate (88%) + 4.1-star rating + specific product niche** | 15-35 | Low to Medium | Limited volume but consistent quality |
| **Marketplace seller + 3.8-star rating + detailed descriptions + reasonable 48-hour shipping** | 20-40 | Low | Good communication compensates for moderate rating |

### Negative Test: Ensure Legitimate Sellers Are Not Over-Flagged

| Anti-Pattern | Should NOT Trigger | Reason |
|---|---|---|
| Simply having account age <30 days | Automatically High score | Compensated by other positive signals |
| Description <80 characters if specific/clear | Auto-generated description flag | Pattern-based detection, not length-based |
| Mentioning "new listing" or "recently added"** | Urgency flag | Legitimate seller announcements ≠ pressure tactics |
| Using common platform-acceptable phrases | NLP false positives | Baseline patterns must be distinguished from pressure |

---

## 17. TAGLISH & MIXED-LANGUAGE NLP TESTS (NEW - CRITICAL)

**Purpose:** Validate NLP detection against real Taglish marketplace language, not English-only phrases.

### Test Cases with Real Taglish Examples

#### Should Detect Urgency (Multiple Patterns)
| Text Sample | Expected Detection | Points | Validation |
|---|---|---|---|
| "Legit po ito! Bili na bago maubusan!" | Urgency + Over-promising | +20pts | Taglish urgency ("bili na") + promise ("legit") |
| "Limited lang ito, mabilis maubos talaga" | Urgency detected | +10pts | Local pattern for scarcity |
| "Available lang ng 3 pieces, bili na!" | Urgency detected | +10pts | Explicit scarcity + call-to-action |
| "Rush! Konti na lang bago sold out" | Urgency detected | +10pts | English "rush" + Tagalog pattern |
| "Paubos na yan, bilisan ninyo!" | Urgency detected | +10pts | Tagalog urgency phrase |

#### Should Detect Payment Pressure (Multiple Patterns)
| Text Sample | Expected Detection | Points | Validation |
|---|---|---|---|
| "GCash muna bago mag-ship, no cancel ha" | Pressure payment + no refund signal | +10pts | Local payment pattern + inflexibility |
| "Bayad agad, deliver kaagad. COD lang." | Payment pressure + restriction | +10pts | Cash-on-delivery restriction |
| "Deposit first, balance on delivery, walang returns" | Payment pressure + no refunds | +10pts | Upfront payment requirement |
| "GCash/PayMaya lang, walang installment" | Payment restriction | +5pts | Limited payment options |
| "Bayad agad walang checking" | Upfront + no inspection | +10pts | Pressure tactic |

#### Should Detect Over-Promising (Multiple Patterns)
| Text Sample | Expected Detection | Points | Validation |
|---|---|---|---|
| "Brand new sealed, 100% original guaranteed, limited na" | Over-promising + urgency | +20pts | Multiple guarantee claims + scarcity |
| "Original po talaga, 100% legit guaranteed, walang fake" | Over-promising repetition | +10pts | Excessive assurances in Taglish |
| "Brand new, factory sealed, authentic original, best quality" | Over-promising stacking | +10pts | Multiple quality claims |
| "Certified authentic, 200% legit, proven quality" | Over-promising with exaggeration | +10pts | Impossible percentage claim |
| "Galing sa warehouse, sealed talaga, original 100%" | Mixed legitimate + over-claiming | +8pts | Some legitimacy but excessive assurance |

#### Should Detect Vague Branding (Multiple Patterns)
| Text Sample | Expected Detection | Points | Validation |
|---|---|---|---|
| "Murang-mura, quality naman kahit walang brand" | Vague branding + price focus | +5pts | Local pattern acknowledging no-brand |
| "Generic brand pero matibay talaga" | Explicit generic admission | +5pts | Direct brand vagueness |
| "No brand pero goods, sulit lang yan" | Generic value pitch | +5pts | Taglish no-brand pattern |
| "Brand? Hindi importante, gamit lang yan" | Dismissive of brand value | +5pts | Deliberately vague about origin |
| "Chinese brand pero okay, hindi scam" | Vague origin + defensive | +5pts | Defensive vagueness |

#### SHOULD NOT Flag (Legitimate Descriptive Language)
| Text Sample | Expected Detection | Points | Validation |
|---|---|---|---|
| "Fast delivery, good quality, sulit ang presyo" | No flags — genuine description | 0pts | Common positive descriptors without pressure |
| "Authentic brands available, stocks updated weekly" | No flags — informational | 0pts | Generic but not suspicious |
| "Premium quality products for everyday use, satisfaction guaranteed" | No flags — generic quality claims | 0pts | Standard merchant language, not over-claiming |
| "Available nationwide, trusted ng thousands of customers" | No flags — trust building | 0pts | Legitimate seller confidence statement |
| "Imported items, quality checked before delivery, 7-day return policy" | No flags — clear terms | 0pts | Transparency, not pressure |
| "Bagong dating, aming pinili personally para sa inyo" | No flags — supplier commentary | 0pts | Sourcing narrative, not urgency |
| "Kumpleto ang package, may warranty card kasama" | No flags — feature listing | 0pts | Factual product information |

#### Mixed-Language Detection (Taglish Code-Switching)
| Text Sample | Expected Detection | Points | Validation |
|---|---|---|---|
| "Original talaga ito, legit po. Bumili ka na ngayon, limited stocks" | Urgency (Taglish) + Over-promise (English) | +18pts | Detects across language boundaries |
| "GCash lang ang option, downpayment required agad. Hindi kami nag-accept ng refunds" | Payment pressure (English + Taglish) | +10pts | Mixed-language restriction patterns |
| "100% authentic, walang fake. Bili na bago sold out, mabilis yan" | Over-promise (English) + Urgency (Taglish) | +18pts | Bilingual flag detection |

#### Platform-Specific Taglish Patterns
| Platform | Pattern Example | Expected Detection | Notes |
|---|---|---|---|
| **Shopee** | "Shop voucher lang, promo code here" | No flag | Legitimate promo language |
| **Shopee** | "Shopee mall dito, trusted seller, bili na!" | Urgency flag | "Bili na" urgency phrase |
| **Lazada** | "Free shipping nationwide, limited offer lang" | Urgency flag | "Limited offer" scarcity pattern |
| **Facebook** | "Must go, clearing stock, messaging me now!" | Urgency flag | Clearance + pressure |

---

## Summary of Fixes Applied

| Issue | Fix Applied | Section |
|---|---|---|
| **Issue 1 - Risk Messages** | Replaced verdict language with probabilistic signal descriptions | Section 9 |
| **Issue 2 - 70/30 Weighting** | Added detailed justification for Deep Scan weight distribution | Section 11 |
| **Issue 3 - Auto-Generated Description** | Pattern-based detection (not just 80-char threshold) | Section 5 (Facebook) |
| **Issue 4 - Positive Signal Cases** | Added 8 high-confidence + 3 medium-confidence scenarios | Section 16 (NEW) |
| **Issue 5 - Taglish NLP** | Added 20+ real Taglish examples with detection validation | Section 17 (NEW) |
| **Issue 6 - Confidence Percentages** | Corrected with actual field counts per platform | Section 6 |
| **Issue 7 - Comment Summarizer** | Added 9 comprehensive test cases | Section 13 (NEW) |
| **Issue 8 - Tooltip Trigger** | Added 7 test cases for rating filter tooltips | Section 12 (NEW) |
| **Issue 9 - Capping Clarification** | Explained calculation order and multiplier application | Section 10 |

---

## Academic Rigor Notes

### Design Principles Embedded in Test Cases
1. **Probabilistic Framing:** All messages describe signal presence, not verdicts
2. **Bias Prevention:** Positive signal cases ensure fair treatment of legitimate sellers
3. **Real-World Validation:** Taglish testing reflects actual market language
4. **Transparent Thresholds:** Justifications provided for weights and heuristics
5. **Platform Awareness:** Cases account for platform-specific data availability
6. **Graceful Degradation:** Edge cases show system resilience without false positives

### Critical Validation Checkpoints
- ✓ Risk messages do not claim legitimacy verification
- ✓ Positive seller scenarios confirm non-discriminatory scoring
- ✓ Taglish NLP tested against real market language
- ✓ Confidence calculations match actual implementation
- ✓ Score capping logic explained with multiplier effects
- ✓ Deep Scan weights justified in methodology

---

**Document Version:** 2.0 (Corrected for Academic Review)  
**Last Reviewed:** May 13, 2026
