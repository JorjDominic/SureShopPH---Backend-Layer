"""
Taglish & Mixed-Language NLP Pattern Detection

This module provides pattern-based detection for Taglish (Filipino-English code-mixing)
descriptions commonly found in Philippine e-commerce listings. It complements the English-based
NLP detection with Filipino language patterns that reflect real marketplace language.

Implementation note: These patterns are validated against the comprehensive test cases 
documented in TEST_CASES_COMPREHENSIVE.md Section 17.
"""

import re
from typing import List, Dict, Tuple
from enum import Enum

class NLPCategory(Enum):
    URGENCY = "urgency"
    PAYMENT_PRESSURE = "payment_pressure"
    OVER_PROMISING = "over_promising"
    VAGUE_BRANDING = "vague_branding"
    GENERIC_POSITIVE = "generic_positive"  # No flag


class TaglishPatternDetector:
    """
    Detects NLP signals in mixed-language (Taglish) e-commerce descriptions.
    
    Validates against real marketplace language from Shopee, Lazada, and Facebook
    in the Philippine market.
    """
    
    # URGENCY PATTERNS - Flag: +10pts
    URGENCY_PATTERNS = [
        # Tagalog urgency markers
        r'\bbili\s+na\b',                    # "bili na" = buy now
        r'\bhuli\s+na\b',                    # "huli na" = last chance
        r'\bpaubos\s+na\b',                  # "paubos na" = running out
        r'\bmabilis\s+maubos',               # "mabilis maubos" = sells out fast
        r'\blimited\s+lang',                 # "limited lang" = limited only
        r'\blimited\s+stocks',               # "limited stocks"
        r'\blimited\s+pieces',               # "limited pieces"
        r'\blimited\s+na',                   # "limited na" = limited already
        r'\bkonti\s+na\s+lang',              # "konti na lang" = very few left
        r'\bsoled?\s+out',                   # "sold out"
        r'\blast\s+pieces?',                 # "last piece(s)"
        r'\brush',                           # "rush"
        r'\bflash\s+sale',                   # "flash sale"
        r'\bbefore\s+out\s+of\s+stock',      # "before out of stock"
        r'\bgrabi\s+bilis',                  # "grabi bilis" = very fast
    ]
    
    # PAYMENT PRESSURE PATTERNS - Flag: +10pts
    PAYMENT_PRESSURE_PATTERNS = [
        # Cash/payment restrictions
        r'\bgcash\s+muna\b',                 # "GCash muna" = GCash first
        r'\bpaymaya\s+muna\b',               # "PayMaya muna"
        r'\bgcash\s+lang\b',                 # "GCash lang" = GCash only
        r'\bpaymaya\s+lang\b',               # "PayMaya lang"
        r'\bcod\s+lang\b',                   # "COD lang" = COD only
        r'\bcod\s+only\b',                   # "COD only"
        r'\bdownpayment\s+first\b',          # "downpayment first"
        r'\bdownpayment\s+required\b',       # "downpayment required"
        r'\bbayad\s+agad\b',                 # "bayad agad" = pay immediately
        r'\bbayad\s+muna\b',                 # "bayad muna" = pay first
        r'\bfull\s+payment\s+required\b',    # "full payment required"
        r'\bno\s+refunds?\b',                # "no refund(s)"
        r'\bwalang\s+returns?\b',            # "walang returns" = no returns
        r'\bwalang\s+cancel\b',              # "walang cancel" = no cancellation
        r'\bno\s+cancel\b',                  # "no cancel"
        r'\bwalang\s+installment',           # "walang installment" = no installment
        r'\bno\s+installment',               # "no installment"
        r'\bno\s+checking\b',                # "no checking" = no inspection
        r'\bno\s+inspection\b',              # "no inspection"
        r'\bdirect\s+transfer\s+only\b',     # "direct transfer only"
    ]
    
    # OVER-PROMISING PATTERNS - Flag: +10pts
    OVER_PROMISING_PATTERNS = [
        # Legitimacy claims
        r'\b100%\s+legit\b',                 # "100% legit"
        r'\b100%\s+original\b',              # "100% original"
        r'\blegit\s+po\b',                   # "legit po"
        r'\blegit\s+talaga\b',               # "legit talaga"
        r'\boriginal\s+na\s+original\b',     # "original na original"
        r'\boriginal\s+talaga\b',            # "original talaga"
        r'\b100%\s+authentic\b',             # "100% authentic"
        r'\bauthenticated?\s+po\b',          # "authentic po"
        r'\bguaranteed?\b',                  # "guarantee(d)"
        r'\bno\s+issues?\b',                 # "no issues"
        r'\bwalang\s+issues?\b',             # "walang issues"
        r'\bsealed?\b',                      # "seal(ed)"
        r'\bbrand\s+new\s+sealed\b',         # "brand new sealed"
        r'\bcertified?\s+authentic\b',       # "certified authentic"
        r'\bproven\s+quality\b',             # "proven quality"
        r'\b\d{2,3}%\s+(?:legit|original|authentic)\b',  # "200% legit", "150% authentic"
        r'\bbest\s+quality',                 # "best quality"
        r'\bpremium\s+quality',              # "premium quality"
        r'\bfactory\s+sealed',               # "factory sealed"
    ]
    
    # VAGUE BRANDING PATTERNS - Flag: +5pts
    VAGUE_BRANDING_PATTERNS = [
        r'\bgeneric\b',                      # "generic"
        r'\bno\s+brand\b',                   # "no brand"
        r'\bwalang\s+brand\b',               # "walang brand"
        r'\bchinese\s+brand\b',              # "chinese brand"
        r'\blocal\s+brand\b',                # "local brand"
        r'\bno\s+name\s+brand\b',            # "no name brand"
        r'\bbrand\?\s+hindi\s+importante',   # "brand? hindi importante" = brand not important
        r'\bmurang[\s-]mura',                # "murang-mura" = very cheap
        r'\bwalang\s+brand\s+pero',          # "walang brand pero" = no brand but
        r'\borigin\s+hindi\s+importante',    # "origin hindi importante" = origin not important
        r'\bchinese\s+pero\s+okay',          # "chinese pero okay"
        r'\borigin\s+unclear\b',             # "origin unclear"
        r'\bunknown\s+brand\b',              # "unknown brand"
    ]
    
    # LEGITIMATE POSITIVE PHRASES - No flag (validation)
    LEGITIMATE_POSITIVE_PATTERNS = [
        r'\bfast\s+delivery\b',              # "fast delivery"
        r'\bgood\s+quality\b',               # "good quality"
        r'\bsulit\s+(?:lang\s+)?(?:yan|ito)\b',  # "sulit yan/ito" = good value
        r'\bsatisfaction\s+guaranteed?\b',   # "satisfaction guarantee(d)"
        r'\btrusted\s+(?:ng|of)\s+\w+',      # "trusted ng/of customers"
        r'\b7-day\s+return',                 # "7-day return"
        r'\bwarranty\s+card',                # "warranty card"
        r'\bpinili\s+personally\b',          # "pinili personally" = chosen personally
        r'\bkumpleto\s+(?:ang\s+)?package',  # "kumpleto ang package" = complete package
        r'\bupdated\s+stocks?\b',            # "updated stocks"
        r'\bshop\s+voucher\b',               # "shop voucher"
        r'\bpromo\s+code\b',                 # "promo code"
        r'\bfree\s+shipping',                # "free shipping"
    ]

    @staticmethod
    def detect_patterns(text: str) -> Dict[str, List[Dict]]:
        """
        Detect NLP signals in mixed-language text.
        
        Args:
            text: Description text to analyze (may be Tagalog, English, or Taglish mix)
            
        Returns:
            Dictionary mapping category names to list of detected patterns with details
            {
                'urgency': [{'pattern': 'bili na', 'points': 10, 'text_sample': '...'}],
                'payment_pressure': [...],
                'over_promising': [...],
                'vague_branding': [...],
                'legitimate': [...]
            }
        """
        if not text or len(text.strip()) < 20:
            return {
                'urgency': [],
                'payment_pressure': [],
                'over_promising': [],
                'vague_branding': [],
                'legitimate': []
            }
        
        text_lower = text.lower()
        results = {
            'urgency': [],
            'payment_pressure': [],
            'over_promising': [],
            'vague_branding': [],
            'legitimate': []
        }
        
        # Check urgency patterns
        for pattern in TaglishPatternDetector.URGENCY_PATTERNS:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                results['urgency'].append({
                    'pattern': match.group(),
                    'points': 10,
                    'span': match.span(),
                    'category': NLPCategory.URGENCY.value
                })
        
        # Check payment pressure patterns
        for pattern in TaglishPatternDetector.PAYMENT_PRESSURE_PATTERNS:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                results['payment_pressure'].append({
                    'pattern': match.group(),
                    'points': 10,
                    'span': match.span(),
                    'category': NLPCategory.PAYMENT_PRESSURE.value
                })
        
        # Check over-promising patterns
        for pattern in TaglishPatternDetector.OVER_PROMISING_PATTERNS:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                results['over_promising'].append({
                    'pattern': match.group(),
                    'points': 10,
                    'span': match.span(),
                    'category': NLPCategory.OVER_PROMISING.value
                })
        
        # Check vague branding patterns
        for pattern in TaglishPatternDetector.VAGUE_BRANDING_PATTERNS:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                results['vague_branding'].append({
                    'pattern': match.group(),
                    'points': 5,
                    'span': match.span(),
                    'category': NLPCategory.VAGUE_BRANDING.value
                })
        
        # Check legitimate patterns (no flag, for validation)
        for pattern in TaglishPatternDetector.LEGITIMATE_POSITIVE_PATTERNS:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                results['legitimate'].append({
                    'pattern': match.group(),
                    'points': 0,
                    'span': match.span(),
                    'category': NLPCategory.GENERIC_POSITIVE.value
                })
        
        return results

    @staticmethod
    def calculate_nlp_score(text: str) -> Tuple[int, List[str]]:
        """
        Calculate NLP-based risk score contribution (0-35pts max per scoring rules).
        
        Args:
            text: Description text to analyze
            
        Returns:
            Tuple of (score_contribution, list_of_flags)
            score_contribution: Points added to risk score (0-35)
            list_of_flags: List of human-readable flag descriptions
        """
        if not text or len(text.strip()) < 20:
            return (10, ["Missing or too short description"])
        
        patterns = TaglishPatternDetector.detect_patterns(text)
        
        score = 0
        flags = []
        
        # Track if legitimate signals are present
        has_legitimate = bool(patterns['legitimate'])
        
        # Only add points if flag categories are triggered
        if patterns['urgency']:
            score += 10
            flags.append(f"Urgency language detected ({len(patterns['urgency'])} instance(s))")
        
        if patterns['payment_pressure']:
            score += 10
            flags.append(f"Payment pressure signals detected ({len(patterns['payment_pressure'])} instance(s))")
        
        if patterns['over_promising']:
            score += 10
            flags.append(f"Over-promising language detected ({len(patterns['over_promising'])} instance(s))")
        
        if patterns['vague_branding']:
            score += 5
            flags.append(f"Vague branding mentioned ({len(patterns['vague_branding'])} instance(s))")
        
        # Cap at 35 points max for text/NLP category
        score = min(score, 35)
        
        # If legitimate signals present and no major flags, override to 0
        if has_legitimate and not flags:
            score = 0
        
        return (score, flags)


# Test cases demonstrating the pattern detector
if __name__ == "__main__":
    test_cases = [
        # Should detect urgency + over-promising
        ("Legit po ito! Bili na bago maubusan!", ['urgency', 'over_promising']),
        # Should detect payment pressure
        ("GCash muna bago mag-ship, no cancel ha", ['payment_pressure']),
        # Should detect multiple categories
        ("Brand new sealed, 100% original guaranteed, limited na", ['over_promising', 'urgency']),
        # Should NOT flag - legitimate
        ("Fast delivery, good quality, sulit ang presyo", []),
        # Should detect vague branding
        ("Murang-mura, quality naman kahit walang brand", ['vague_branding']),
        # Should detect urgency + payment pressure
        ("GCash lang ang option, downpayment required agad. Hindi kami nag-accept ng refunds", 
         ['payment_pressure']),
    ]
    
    print("=" * 80)
    print("TAGLISH NLP PATTERN DETECTION - TEST VALIDATION")
    print("=" * 80)
    
    for text, expected_categories in test_cases:
        score, flags = TaglishPatternDetector.calculate_nlp_score(text)
        patterns = TaglishPatternDetector.detect_patterns(text)
        
        detected_categories = [k for k, v in patterns.items() if v and k != 'legitimate']
        
        print(f"\nText: {text}")
        print(f"Expected categories: {expected_categories}")
        print(f"Detected categories: {detected_categories}")
        print(f"Score contribution: {score}pts")
        print(f"Flags: {flags}")
        
        # Validation
        match = set(detected_categories) == set(expected_categories)
        status = "✓ PASS" if match else "✗ FAIL"
        print(f"Validation: {status}")
