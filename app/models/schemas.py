"""Pydantic schemas for all request and response bodies."""
from __future__ import annotations
from typing import Any, List, Optional, Literal, Dict
from pydantic import BaseModel, Field


# ---------- Shared ----------

class DataQuality(BaseModel):
    missing: List[str] = Field(default_factory=list)
    # Optional map of field_name -> "high" | "medium" | "low" reported by the
    # content script. Used by the backend to weight confidence-aware scoring.
    field_confidence: Dict[str, str] = Field(default_factory=dict)


# ---------- Listing requests ----------

class ShopeeListing(BaseModel):
    platform: Literal["shopee"]
    url: str
    product_name: Optional[str] = None
    price: Optional[float] = None
    sold_count: Optional[str] = None
    rating: Optional[float] = None
    rating_count: Optional[int] = None
    seller_name: Optional[str] = None
    shop_age: Optional[str] = None
    response_rate: Optional[float] = None
    image_count: int = 0
    description: Optional[str] = None
    specifications: Optional[Dict[str, Any]] = None
    is_shopee_mall: bool = False
    data_quality: DataQuality = Field(default_factory=DataQuality)


class LazadaListing(BaseModel):
    platform: Literal["lazada"]
    url: str
    product_name: Optional[str] = None
    price: Optional[float] = None
    sold_count: Optional[str] = None
    rating: Optional[float] = None
    rating_count: Optional[int] = None
    seller_name: Optional[str] = None
    seller_rating: Optional[str] = None
    seller_badges: Optional[List[str]] = None
    image_count: int = 0
    description: Optional[str] = None
    description_image_count: int = 0
    specifications: Optional[Dict[str, Any]] = None
    is_lazmall: bool = False
    data_quality: DataQuality = Field(default_factory=DataQuality)


class FacebookListing(BaseModel):
    platform: Literal["facebook"]
    url: str
    listing_url: Optional[str] = None
    product_name: Optional[str] = None
    price: Optional[float] = None
    price_is_variant: bool = False
    seller_name: Optional[str] = None
    condition: Optional[str] = None
    location: Optional[str] = None
    listing_date: Optional[str] = None
    image_count: int = 0
    description: Optional[str] = None
    sold_count: Optional[Any] = None
    rating: Optional[Any] = None
    rating_count: Optional[Any] = None
    seller_rating: Optional[Any] = None
    response_rate: Optional[Any] = None
    data_quality: DataQuality = Field(default_factory=DataQuality)


# Discriminated union — accepts any of the three
ListingPayload = ShopeeListing | LazadaListing | FacebookListing


# ---------- Comments request ----------

class CommentItem(BaseModel):
    text: str
    date: Optional[str] = None
    rating_stars: Optional[float] = None


class CommentsPayload(BaseModel):
    platform: Literal["shopee", "lazada", "facebook"]
    comments: List[CommentItem] = Field(default_factory=list)
    page_number: int = 1
    total_pages: int = 1


# ---------- Deep scan ----------

class DeepPayload(BaseModel):
    listing: ListingPayload
    comments: CommentsPayload


# ---------- URL safety ----------

class UrlPayload(BaseModel):
    url: str


# ---------- Reports ----------

class ReportPayload(BaseModel):
    listing_url: str
    report_type: str
    description: Optional[str] = None


# ---------- Auth ----------

import re as _re

ACTIVATION_KEY_RE = _re.compile(
    r'^[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$'
)


class ActivateRequest(BaseModel):
    activation_key: str

    @classmethod
    def __get_validators__(cls):
        yield from super().__get_validators__()

    def model_post_init(self, __context):
        key = self.activation_key.strip().upper()
        if not ACTIVATION_KEY_RE.match(key):
            raise ValueError(
                "activation_key must be in the format XXXX-XXXX-XXXX-XXXX-XXXX "
                "(uppercase letters and digits, e.g. SSPH-PYSP-4B3R-ZZD5-6JRP)"
            )
        object.__setattr__(self, 'activation_key', key)


class ActivateResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Admin ----------

class VerifyListingPayload(BaseModel):
    listing_id: str
    verified: bool = True


class AdminLogPayload(BaseModel):
    action: str
    details: Optional[Dict[str, Any]] = None


# ---------- Responses ----------

class ConfidenceBlock(BaseModel):
    level: str
    percentage: int
    fields_present: int
    total_fields: int
    confidence_message: str = ""
    could_not_retrieve: List[str]
    not_available_on_platform: List[str]


class ScoreBreakdown(BaseModel):
    seller_attributes: int
    listing_metadata: int
    textual_nlp: int
    url_domain: int = 0


class FlagDetail(BaseModel):
    code: str
    category: str
    severity: str
    label: str
    tip: str
    explanation: str = ""
    triggered_by: Optional[str] = None


class ScoreBreakdownItem(BaseModel):
    score: int
    max: int = 25
    label: str
    description: str = ""
    summary: str = ""


class PositiveSignal(BaseModel):
    message: str
    impact: str


class CommentSummaryDetail(BaseModel):
    total_analyzed: int
    duplicate_count: int
    generic_count: int
    clustered_dates: bool
    avg_length: float
    summary_message: str
    five_star_pct: int = 0
    rated_count: int = 0
    avg_rating: Optional[float] = None
    no_text_count: int = 0
    rating_diversity: bool = True



class ScanCompleteness(BaseModel):
    level: str
    description: str


class ProductNotice(BaseModel):
    title: str = "Product Notice"
    message: str
    severity: Literal["info", "caution", "warning"] = "info"
    indicators: List[str] = Field(default_factory=list)
    recommended_action: str = ""
    recommended_actions: List[str] = Field(default_factory=list)
    disclaimer: str


class PlatformSignals(BaseModel):
    is_mall: bool = False
    has_badges: bool = False
    badge_list: List[str] = Field(default_factory=list)


class ListingAnalysisResponse(BaseModel):
    risk_score: int
    risk_level: str
    risk_color: str
    risk_message: str
    flags: List[str]
    flag_details: List[FlagDetail] = Field(default_factory=list)
    positive_signals: List[PositiveSignal] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    recommendations_total: int = 0
    verify_checklist: List[str] = Field(default_factory=list)
    checklist_total: int = 0
    confidence: ConfidenceBlock
    score_breakdown: ScoreBreakdown
    score_breakdown_details: Dict[str, ScoreBreakdownItem] = Field(default_factory=dict)
    product_notice: Optional[ProductNotice] = None
    platform_signals: PlatformSignals
    scan_completeness: Optional[ScanCompleteness] = None
    scan_mode_note: Optional[str] = None
    closing_line: str = ""
    risk_message_source: Literal["groq", "rule_based"] = "rule_based"
    scan_timestamp: str
    scanned_at_iso: Optional[str] = None


class CommentsAnalysisResponse(BaseModel):
    bot_likelihood: float
    fake_review_likelihood: float
    bot_likelihood_pct: int
    fake_review_pct: int
    confidence: str
    comments_analyzed: int
    no_comments_available: bool = False
    pages_analyzed: int
    total_pages: int
    coverage_pct: int
    flags: List[str]
    flag_details: List[FlagDetail] = Field(default_factory=list)
    summary: str = ""
    summary_source: Literal["groq", "fallback_unavailable"] = "fallback_unavailable"
    comment_summary: Optional[CommentSummaryDetail] = None
    recommendations: List[str] = Field(default_factory=list)
    review_diversity_score: int = 100
    review_diversity_explanation: str = "Measures variety in review content and rating distribution. Lower scores may indicate repetitive or uniform reviews."
    pages_coverage_note: Optional[str] = None
    dominant_sentiment: str = "none"
    comment_pattern_summary: str = ""
    small_sample_warning: Optional[str] = None
    small_sample_flag: bool = False
    sample_size_explanation: Optional[str] = None
    comment_weight_note: Optional[str] = None
    scanned_at_iso: Optional[str] = None


class DeepAnalysisResponse(BaseModel):
    listing: ListingAnalysisResponse
    comments: CommentsAnalysisResponse
    combined_risk_score: int
    combined_risk_level: str


class DomainInfo(BaseModel):
    host: Optional[str] = None
    domain_age_days: Optional[int] = None
    creation_date: Optional[str] = None
    expiry_date: Optional[str] = None
    registrar: Optional[str] = None
    country: Optional[str] = None
    ip_address: Optional[str] = None
    privacy_protected: bool = False
    lookup_failed: bool = False
    skip_reason: Optional[str] = None


class UrlSafetyResponse(BaseModel):
    url: str
    risk_score: int
    risk_level: str
    flags: List[str]
    risk_message: str = ""
    flag_details: List[FlagDetail] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    verify_checklist: List[str] = Field(default_factory=list)
    domain_info: Optional[DomainInfo] = None
