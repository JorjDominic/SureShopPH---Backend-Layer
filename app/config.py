"""Application configuration loaded from .env."""
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
JWT_SECRET = os.getenv("JWT_SECRET", "")

APP_NAME = "SureShopPH Backend"
APP_VERSION = "1.1.0"

# ---------- CORS ----------
# Comma-separated list of allowed origins. Use "*" only for local dev.
# In production, list extension origin (chrome-extension://<id>) and frontends.
_raw_origins = os.getenv(
    "CORS_ALLOW_ORIGINS",
    "http://localhost,http://localhost:3000,http://localhost:5173,http://127.0.0.1",
).strip()
CORS_ALLOW_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]
# Regex form is needed for chrome-extension://* (env: CORS_ALLOW_ORIGIN_REGEX)
CORS_ALLOW_ORIGIN_REGEX = os.getenv(
    "CORS_ALLOW_ORIGIN_REGEX",
    r"^chrome-extension://[a-z0-9]+$",
)

# ---------- Request limits ----------
# Maximum body size for analyze endpoints (default 1 MB)
MAX_REQUEST_BYTES = int(os.getenv("MAX_REQUEST_BYTES", str(1 * 1024 * 1024)))

# ---------- Scoring thresholds ----------
HIGH_RISK_PERSIST_THRESHOLD = int(os.getenv("HIGH_RISK_PERSIST_THRESHOLD", "60"))

# Risk band boundaries (inclusive lower, inclusive upper).
# Single source of truth — referenced by score_calculator.band() and deep.py.
RISK_BANDS = [
    (76, 100, "High", "red"),
    (51, 75, "Medium", "orange"),
    (26, 50, "Low", "yellow"),
    (0, 25, "Very Low", "green"),
]

# Deep-scan blend weights (must sum to 1.0)
DEEP_LISTING_WEIGHT = float(os.getenv("DEEP_LISTING_WEIGHT", "0.7"))
DEEP_COMMENTS_WEIGHT = float(os.getenv("DEEP_COMMENTS_WEIGHT", "0.3"))

# Confidence-aware scoring: trust multipliers applied per extracted field.
CONFIDENCE_TRUST = {
    "high": 1.0,
    "medium": 0.7,
    "low": 0.4,
}

# Confidence field sets per platform
CONFIDENCE_FIELDS = {
    "shopee": ["price", "shop_age", "rating", "rating_count", "description", "response_rate"],
    "lazada": ["price", "shop_age", "seller_rating", "rating", "rating_count", "description"],
    "facebook": ["price", "shop_age", "condition", "description"],
}

# Fields the platform never exposes
NOT_AVAILABLE = {
    "shopee": [],
    "lazada": [],
    "facebook": ["sold_count", "rating", "rating_count", "seller_rating", "response_rate"],
}

# Market price baselines (very rough, used to flag below-market)
DEFAULT_PRICE_BASELINE = int(os.getenv("DEFAULT_PRICE_BASELINE", "200"))

# ---------- Logging ----------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


# ---------- Startup validation ----------
def validate_env() -> None:
    """Raise at boot if any required env var is blank.

    Called from `main.lifespan` so the server refuses to start instead of
    failing on the first request with a cryptic DB or JWT error.
    """
    required = {
        "SUPABASE_URL": SUPABASE_URL,
        "SUPABASE_KEY": SUPABASE_KEY,
        "JWT_SECRET": JWT_SECRET,
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}. "
            "Set them in your .env file before starting the server."
        )
