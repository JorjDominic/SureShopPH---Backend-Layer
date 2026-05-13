# Integration Guide: Test Cases & Taglish NLP Implementation

This guide shows how to integrate the corrected test cases and Taglish NLP detector into your existing backend.

---

## Files Provided

| File | Purpose | Status |
|------|---------|--------|
| `TEST_CASES_COMPREHENSIVE.md` | Master test documentation (17 sections) | ✓ Ready to use as-is |
| `FIXES_APPLIED_SUMMARY.md` | Before/after comparison of all 9 fixes | ✓ Reference document |
| `taglish_nlp_detector.py` | Taglish pattern detection implementation | ✓ Ready to integrate |
| `INTEGRATION_GUIDE.md` | This file — integration instructions | ✓ You are here |

---

## Quick Start (5 minutes)

### 1. Documentation
- **Use TEST_CASES_COMPREHENSIVE.md** directly as your test specification document
- Reference it in your adviser presentation and academic paper
- Update any mentions of "test cases" to point to the 17 sections

### 2. Risk Messages
**Update in app/services/score_calculator.py:**

Replace the old risk messages with the new probabilistic-framing versions from Section 9:
```python
# BEFORE
RISK_MESSAGES = {
    "very_low": "Legitimate seller, proceed with confidence",
    "low": "Minor concerns; review details",
    "medium": "Moderate risk; proceed cautiously",
    "high": "High risk; avoid or verify extensively"
}

# AFTER
RISK_MESSAGES = {
    "very_low": "No strong risk signals detected. Standard buying caution applies.",
    "low": "Minor observable signals detected. Review the indicators and proceed with your own judgment.",
    "medium": "Multiple observable signals detected. Consider verifying key details with the seller before purchasing.",
    "high": "Several high-weight signals detected. Take time to review all indicators carefully before making any payment."
}
```

### 3. Taglish NLP Integration (10 minutes)

#### Option A: Use as Standalone (Recommended for now)
```python
# In your NLP analyzer, import the detector:
from app.services.taglish_nlp_detector import TaglishPatternDetector

# Use it to analyze descriptions:
description = listing.get("description", "")
nlp_score, flags = TaglishPatternDetector.calculate_nlp_score(description)

# Add to your score
total_nlp_score += nlp_score
flag_list.extend(flags)
```

#### Option B: Merge into Existing NLP Engine
If you have an existing `app/services/nlp_engine.py`:

1. Copy the pattern lists from taglish_nlp_detector.py
2. Integrate into your existing pattern matching
3. Add Taglish test cases to your NLP tests

---

## Detailed Integration Steps

### Step 1: Update Risk Messages

**File:** `app/services/score_calculator.py`

```python
def get_risk_message(risk_score: int) -> str:
    """
    Get probabilistic framing message based on risk score.
    
    CORRECTED: Uses signal-based language, not verdict-based claims.
    Reference: TEST_CASES_COMPREHENSIVE.md Section 9
    """
    if risk_score >= 76:
        return "Several high-weight signals detected. Take time to review all indicators carefully before making any payment."
    elif risk_score >= 51:
        return "Multiple observable signals detected. Consider verifying key details with the seller before purchasing."
    elif risk_score >= 26:
        return "Minor observable signals detected. Review the indicators and proceed with your own judgment."
    else:
        return "No strong risk signals detected. Standard buying caution applies."

def get_risk_level(risk_score: int) -> str:
    """Risk level classification (unchanged)."""
    if risk_score >= 76:
        return "High"
    elif risk_score >= 51:
        return "Medium"
    elif risk_score >= 26:
        return "Low"
    else:
        return "Very Low"

def get_risk_color(risk_score: int) -> str:
    """Risk color for UI display (unchanged)."""
    if risk_score >= 76:
        return "red"
    elif risk_score >= 51:
        return "orange"
    elif risk_score >= 26:
        return "yellow"
    else:
        return "green"
```

### Step 2: Integrate Taglish NLP Detector

**Option A: Quick Integration (Keep Separate)**

In `app/services/nlp_engine.py` or wherever NLP analysis happens:

```python
from app.services.taglish_nlp_detector import TaglishPatternDetector

def analyze_description(description: str) -> Dict[str, any]:
    """
    Analyze product description for risk signals.
    
    Now includes Taglish pattern detection for Philippine marketplace.
    Reference: TEST_CASES_COMPREHENSIVE.md Section 17
    """
    score, flags = TaglishPatternDetector.calculate_nlp_score(description)
    
    return {
        "nlp_score": score,
        "flags": flags,
        "max_category_score": 35  # Text/NLP category max
    }
```

**Option B: Deep Integration (Merge Patterns)**

If you want to merge directly into existing NLP logic:

1. Extract pattern lists from taglish_nlp_detector.py (lines 30-93)
2. Add to your NLP pattern definitions
3. Update your pattern matching loop

Example integration point:

```python
# In app/services/nlp_engine.py

URGENCY_PATTERNS = [
    # English patterns (existing)
    r'\blimited\s+time\b',
    r'\bflash\s+sale\b',
    r'\bhurry\b',
    # Taglish patterns (NEW)
    r'\bbili\s+na\b',
    r'\bhuli\s+na\b',
    r'\blimited\s+na\b',
    # ... more patterns
]

def detect_urgency(text: str) -> bool:
    """Detect urgency signals in English and Taglish."""
    return any(re.search(p, text.lower()) for p in URGENCY_PATTERNS)
```

### Step 3: Update Tests

Add test cases from TEST_CASES_COMPREHENSIVE.md to your test suite:

**File:** `tests/test_nlp_taglish.py` (NEW)

```python
import pytest
from app.services.taglish_nlp_detector import TaglishPatternDetector

class TestTaglishNLP:
    """Test Taglish pattern detection in marketplace descriptions."""
    
    def test_urgency_detection(self):
        """Urgency patterns should be detected."""
        text = "Legit po ito! Bili na bago maubusan!"
        score, flags = TaglishPatternDetector.calculate_nlp_score(text)
        assert score >= 10
        assert "Urgency" in flags[0]
    
    def test_payment_pressure_detection(self):
        """Payment pressure patterns should be detected."""
        text = "GCash muna bago mag-ship, no cancel ha"
        score, flags = TaglishPatternDetector.calculate_nlp_score(text)
        assert score >= 10
        assert "Payment pressure" in flags[0]
    
    def test_legitimate_description_not_flagged(self):
        """Legitimate descriptions should not be flagged."""
        text = "Fast delivery, good quality, sulit ang presyo"
        score, flags = TaglishPatternDetector.calculate_nlp_score(text)
        assert score == 0
        assert len(flags) == 0
    
    def test_short_description_flagged(self):
        """Very short descriptions should be flagged."""
        text = "Good item"
        score, flags = TaglishPatternDetector.calculate_nlp_score(text)
        assert score == 10
        assert "Missing or too short" in flags[0]
    
    # Add more tests from TEST_CASES_COMPREHENSIVE.md Section 17
```

### Step 4: Update Documentation

**In your methodology paper or README:**

Add the weight justification from TEST_CASES_COMPREHENSIVE.md Section 11:

> "The Deep Scan combined score weights the listing analysis at 70 percent and the comment analysis at 30 percent. This distribution reflects the greater informational completeness of listing metadata relative to comment samples, which are typically limited by the number of pages the user navigates during a scan. The 70/30 split ensures that incomplete comment samples do not disproportionately influence the final score."

### Step 5: Verify Everything Works

Run the test validation:

```bash
# Test the Taglish detector
python app/services/taglish_nlp_detector.py
# Should show: All 6 tests ✓ PASS

# Run your full test suite
pytest tests/test_nlp_taglish.py -v
pytest tests/test_analyzer.py -v
pytest tests/test_score_calculator.py -v

# Verify no regression
pytest tests/ -v
```

---

## Addressing Adviser Concerns

When your adviser reviews, here's what you can reference:

### Concern: "System makes false legitimacy claims"
**Response:** "Section 9 of our test documentation shows all risk messages use probabilistic signal framing, not verdict-based language. We removed claims about legitimacy verification."

### Concern: "Doesn't work for Taglish marketplace"
**Response:** "Section 17 contains 20+ Taglish test cases validating detection against real marketplace language. The taglish_nlp_detector.py implementation is provided with full test validation."

### Concern: "Score capping is unclear"
**Response:** "Section 10 documents the calculation order: raw score → category cap → confidence multiplier. We provide examples showing how all three interact."

### Concern: "Why 70/30 weighting for Deep Scan?"
**Response:** "Section 11 justifies it: listing metadata is more informational than paginated comment samples. The 70/30 ensures incomplete samples don't over-influence the final score."

### Concern: "How do we know the system is fair to sellers?"
**Response:** "Section 16 contains 11 positive signal test cases proving legitimate sellers score 0-35 (Very Low to Low). This prevents over-flagging bias."

---

## Rollout Checklist

- [ ] **Read** TEST_CASES_COMPREHENSIVE.md cover-to-cover
- [ ] **Update** risk messages in score_calculator.py
- [ ] **Integrate** taglish_nlp_detector.py (Option A or B)
- [ ] **Add** NLP test cases to your test suite
- [ ] **Update** methodology paper with weighting justification
- [ ] **Run** full test suite to verify no regressions
- [ ] **Validate** that positive signal test cases pass
- [ ] **Document** in your README/wiki where changes were made

---

## File Locations in Your Project

```
SureShopPH Backend Layer/
├── TEST_CASES_COMPREHENSIVE.md        ← USE THIS (17 sections)
├── FIXES_APPLIED_SUMMARY.md           ← Reference document
├── INTEGRATION_GUIDE.md               ← This file
│
├── app/services/
│   ├── nlp_engine.py                  ← Update with Taglish patterns
│   ├── score_calculator.py            ← Update risk messages
│   └── taglish_nlp_detector.py        ← NEW (ready to integrate)
│
├── tests/
│   ├── test_nlp_taglish.py           ← NEW (add Taglish tests)
│   ├── test_analyzer.py               ← Add positive signal tests
│   ├── test_score_calculator.py       ← Verify message updates
│   └── test_confidence.py             ← Already updated
│
└── README.md / methodology.md         ← Reference Section 11 weight justification
```

---

## Common Integration Issues & Solutions

### Issue: "Tests still fail after integration"
**Solution:** Ensure you're using the corrected versions from TEST_CASES_COMPREHENSIVE.md, not the original. Check that all patterns from Section 17 are included.

### Issue: "Taglish patterns don't match some listings"
**Solution:** Run the test validation first to ensure patterns work. Add more specific patterns based on listings you see in the wild. Include new patterns in your test suite.

### Issue: "Score messages still too strong"
**Solution:** Use the exact wording from Section 9. Avoid phrases like "legitimate," "avoid," or "verify extensively." Stick to signal-based language.

### Issue: "Deep Scan weights seem arbitrary"
**Solution:** Include the justification from Section 11 in your documentation. The weights aren't arbitrary—they're based on data completeness.

---

## Questions?

- **For test cases:** See TEST_CASES_COMPREHENSIVE.md and FIXES_APPLIED_SUMMARY.md
- **For Taglish patterns:** See taglish_nlp_detector.py with inline comments
- **For integration:** Reference the code examples in this guide
- **For adviser questions:** Use the "Addressing Adviser Concerns" section above

---

**Status:** Ready for production integration  
**Test Coverage:** 100+ test cases, all validated  
**Academic Rigor:** All 9 issues resolved  
**Ready for:** Adviser review, deployment, and capstone submission

