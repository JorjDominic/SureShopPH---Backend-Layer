"""WHOIS-based domain information lookup for the manual URL checker."""
from __future__ import annotations

import socket
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from urllib.parse import urlparse

# python-whois is an optional dependency; degrade gracefully if unavailable.
try:
    import whois as _whois  # python-whois package
    _WHOIS_AVAILABLE = True
except ImportError:  # pragma: no cover
    _WHOIS_AVAILABLE = False


# Established platforms whose domain info adds no signal value.
_SKIP_DOMAINS = {
    "shopee.ph", "shopee.com.ph", "lazada.com.ph",
    "facebook.com", "m.facebook.com", "web.facebook.com",
    "google.com", "youtube.com",
}

_WHOIS_TIMEOUT_SECONDS = 5


def _extract_host(url: str) -> str:
    """Return the registered hostname from a URL string."""
    try:
        parsed = urlparse(url)
        return (parsed.hostname or "").lower().strip()
    except Exception:
        return ""


def _is_known_platform(host: str) -> bool:
    return any(host == d or host.endswith("." + d) for d in _SKIP_DOMAINS)


def _to_naive_utc(dt: Any) -> Optional[datetime]:
    """Normalise a datetime (or list of datetimes) to a naive UTC datetime."""
    if isinstance(dt, list):
        dt = dt[0] if dt else None
    if not isinstance(dt, datetime):
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _resolve_ip(host: str) -> Optional[str]:
    """Return the IPv4 address for *host*, or None on failure."""
    try:
        return socket.gethostbyname(host)
    except Exception:
        return None


def lookup_domain_info(url: str) -> Dict[str, Any]:
    """
    Perform a WHOIS lookup for *url* and return a structured info dict.

    Keys always present:
        host              str | None
        domain_age_days   int | None
        creation_date     str | None   (ISO-8601 date, UTC)
        expiry_date       str | None   (ISO-8601 date, UTC)
        registrar         str | None
        country           str | None
        ip_address        str | None
        privacy_protected bool
        lookup_failed     bool
        skip_reason       str | None   ("known_platform" | "whois_unavailable" | None)
    """
    result: Dict[str, Any] = {
        "host": None,
        "domain_age_days": None,
        "creation_date": None,
        "expiry_date": None,
        "registrar": None,
        "country": None,
        "ip_address": None,
        "privacy_protected": False,
        "lookup_failed": False,
        "skip_reason": None,
    }

    host = _extract_host(url)
    result["host"] = host or None

    if not host:
        result["lookup_failed"] = True
        return result

    # Resolve IP regardless of WHOIS skip
    result["ip_address"] = _resolve_ip(host)

    if _is_known_platform(host):
        result["skip_reason"] = "known_platform"
        return result

    if not _WHOIS_AVAILABLE:
        result["skip_reason"] = "whois_unavailable"
        result["lookup_failed"] = True
        return result

    try:
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(_WHOIS_TIMEOUT_SECONDS)
        try:
            w = _whois.whois(host)
        finally:
            socket.setdefaulttimeout(old_timeout)

        creation = _to_naive_utc(w.creation_date)
        expiry = _to_naive_utc(w.expiration_date)
        now = datetime.utcnow()

        if creation:
            result["creation_date"] = creation.strftime("%Y-%m-%d")
            result["domain_age_days"] = max(0, (now - creation).days)

        if expiry:
            result["expiry_date"] = expiry.strftime("%Y-%m-%d")

        registrar = w.registrar
        if isinstance(registrar, list):
            registrar = registrar[0] if registrar else None
        result["registrar"] = str(registrar).strip() if registrar else None

        # Country comes from registrant_country or country field
        country = getattr(w, "registrant_country", None) or getattr(w, "country", None)
        if isinstance(country, list):
            country = country[0] if country else None
        result["country"] = str(country).strip() if country else None

        # Heuristic: privacy protection when name/org contains privacy-shield keywords
        name_fields = [
            str(getattr(w, f, "") or "").lower()
            for f in ("name", "org", "registrant_name", "registrant_organization")
        ]
        privacy_keywords = ("privacy", "redacted", "whoisguard", "domains by proxy", "protected")
        result["privacy_protected"] = any(
            kw in field for kw in privacy_keywords for field in name_fields
        )

    except Exception:
        result["lookup_failed"] = True

    return result


def score_domain_age(domain_info: Dict[str, Any]) -> tuple[int, list[str]]:
    """
    Return (score_delta, flags) based on domain age signals.

    Maximum contribution from this function: 20pts (fits inside the 25pt URL cap).
    Not called for known platforms or when lookup failed without useful data.
    """
    score = 0
    flags: list[str] = []

    if domain_info.get("skip_reason") == "known_platform":
        return 0, []

    age = domain_info.get("domain_age_days")

    if age is None:
        # Lookup failed or privacy-protected; treat as minor unknown signal
        if domain_info.get("privacy_protected"):
            score += 5
            flags.append("Domain registration details are privacy-protected")
        elif domain_info.get("lookup_failed") and not domain_info.get("skip_reason"):
            score += 5
            flags.append("Domain registration information could not be retrieved")
        return score, flags

    if age < 30:
        score += 20
        flags.append("Domain registered less than 30 days ago (very new)")
    elif age < 90:
        score += 10
        flags.append("Domain registered less than 90 days ago")
    elif age < 365:
        score += 5
        flags.append("Domain registered less than 1 year ago")

    if domain_info.get("privacy_protected"):
        score += 5
        flags.append("Domain registration details are privacy-protected")

    return score, flags
