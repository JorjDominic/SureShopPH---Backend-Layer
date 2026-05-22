"""All Supabase database operations."""
from __future__ import annotations
from typing import Any, Dict, List

from app.db.supabase_client import get_supabase
from app.config import HIGH_RISK_PERSIST_THRESHOLD
from app.logging_config import get_logger

log = get_logger(__name__)


def save_scan(user_id: str, payload: Dict[str, Any]) -> None:
    supabase = get_supabase()
    row = {
        "user_id": user_id,
        "platform": payload.get("platform"),
        "url": payload.get("url"),
        "risk_score": payload.get("risk_score"),
        "risk_level": payload.get("risk_level"),
        "flags": payload.get("flags") or [],
        "confidence_level": payload.get("confidence_level"),
        "confidence_pct": payload.get("confidence_pct"),
        "scan_mode": payload.get("scan_mode"),
        # Rich insight data — requires migration 0003
        "notes": payload.get("notes"),
        "raw_data": payload.get("raw_data"),
    }
    try:
        supabase.table("scan_history").insert(row).execute()
    except Exception as e:
        log.warning("save_scan failed: %s", e.__class__.__name__)


def maybe_save_high_risk(payload: Dict[str, Any]) -> None:
    if (payload.get("risk_score") or 0) < HIGH_RISK_PERSIST_THRESHOLD:
        return
    supabase = get_supabase()
    row = {
        "url": payload.get("url"),
        "platform": payload.get("platform"),
        "risk_score": payload.get("risk_score"),
        "risk_level": payload.get("risk_level"),
        "flags": payload.get("flags") or [],
    }
    try:
        supabase.table("high_risk_listings").insert(row).execute()
    except Exception as e:
        log.warning("maybe_save_high_risk failed: %s", e.__class__.__name__)


def get_scan_history(user_id: str, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
    supabase = get_supabase()
    try:
        res = (
            supabase.table("scan_history")
            .select("*", count="exact")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return {"data": res.data or [], "total": res.count or 0}
    except Exception as e:
        log.warning("get_scan_history failed: %s", e.__class__.__name__)
        return {"data": [], "total": 0}


def get_high_risk_listings(limit: int = 100) -> List[Dict[str, Any]]:
    supabase = get_supabase()
    try:
        res = (
            supabase.table("high_risk_listings")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data or []
    except Exception as e:
        log.warning("get_high_risk_listings failed: %s", e.__class__.__name__)
        return []


def insert_user_report(user_id: str, listing_url: str, report_type: str,
                       description: str | None) -> Dict[str, Any] | None:
    supabase = get_supabase()
    row = {
        "user_id": user_id,
        "listing_url": listing_url,
        "report_type": report_type,
        "description": description,
    }
    try:
        res = supabase.table("user_reports").insert(row).execute()
        return (res.data or [None])[0]
    except Exception as e:
        log.warning("insert_user_report failed: %s", e.__class__.__name__)
        return None


def list_all_reports(limit: int = 200) -> List[Dict[str, Any]]:
    supabase = get_supabase()
    try:
        res = (
            supabase.table("user_reports")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data or []
    except Exception as e:
        log.warning("list_all_reports failed: %s", e.__class__.__name__)
        return []


def verify_high_risk_listing(listing_id: str, admin_id: str,
                              verified: bool = True) -> Dict[str, Any] | None:
    supabase = get_supabase()
    try:
        res = (
            supabase.table("high_risk_listings")
            .update({"verified": verified, "verified_by": admin_id})
            .eq("id", listing_id)
            .execute()
        )
        return (res.data or [None])[0]
    except Exception as e:
        log.warning("verify_high_risk_listing failed: %s", e.__class__.__name__)
        return None


def write_admin_log(admin_id: str, action: str,
                    details: Dict[str, Any] | None) -> None:
    supabase = get_supabase()
    try:
        supabase.table("admin_logs").insert({
            "user_id": admin_id,
            "action": action,
            "details": details or {},
        }).execute()
    except Exception as e:
        log.warning("write_admin_log failed (action=%s): %s",
                    action, e.__class__.__name__)


def list_admin_logs(limit: int = 200) -> List[Dict[str, Any]]:
    supabase = get_supabase()
    try:
        res = (
            supabase.table("admin_logs")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data or []
    except Exception as e:
        log.warning("list_admin_logs failed: %s", e.__class__.__name__)
        return []


# ---------- Soft delete on training_data ----------

def soft_delete_training_sample(sample_id: str, admin_id: str) -> Dict[str, Any] | None:
    """Mark a training sample as deleted without removing the row."""
    supabase = get_supabase()
    try:
        res = (
            supabase.table("training_data")
            .update({"deleted_at": "now()", "deleted_by": admin_id})
            .eq("id", sample_id)
            .is_("deleted_at", "null")
            .execute()
        )
        return (res.data or [None])[0]
    except Exception as e:
        log.warning("soft_delete_training_sample failed: %s", e.__class__.__name__)
        return None


# ---------- Model version helpers ----------

def list_model_versions(limit: int = 25) -> List[Dict[str, Any]]:
    supabase = get_supabase()
    try:
        res = (
            supabase.table("model_versions")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data or []
    except Exception as e:
        log.warning("list_model_versions failed: %s", e.__class__.__name__)
        return []


def get_active_model_version() -> Dict[str, Any] | None:
    supabase = get_supabase()
    try:
        res = (
            supabase.table("model_versions")
            .select("*")
            .eq("is_active", True)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        return rows[0] if rows else None
    except Exception as e:
        log.warning("get_active_model_version failed: %s", e.__class__.__name__)
        return None


def set_active_model_version(version_id: str) -> Dict[str, Any] | None:
    """Atomically deactivate all rows and activate the chosen one."""
    supabase = get_supabase()
    try:
        # Deactivate all
        supabase.table("model_versions").update({"is_active": False}).neq("id", version_id).execute()
        res = supabase.table("model_versions").update({"is_active": True}).eq("id", version_id).execute()
        return (res.data or [None])[0]
    except Exception as e:
        log.warning("set_active_model_version failed: %s", e.__class__.__name__)
        return None


def insert_model_version(row: Dict[str, Any]) -> Dict[str, Any] | None:
    supabase = get_supabase()
    try:
        res = supabase.table("model_versions").insert(row).execute()
        return (res.data or [None])[0]
    except Exception as e:
        log.warning("insert_model_version failed: %s", e.__class__.__name__)
        return None
