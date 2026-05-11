"""POST /activate and GET /auth/status endpoints."""
from __future__ import annotations
import hashlib
from datetime import datetime, timezone, timedelta

import jwt
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import JWT_SECRET
from app.db.supabase_client import get_supabase
from app.models.schemas import ActivateRequest, ActivateResponse

router = APIRouter(tags=["auth"])

TOKEN_TTL_DAYS = 30
_bearer = HTTPBearer(auto_error=False)


def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.strip().upper().encode()).hexdigest()


def _mint_jwt(user_id: str, token_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "jti": token_id,          # store access_tokens.id to check revocation
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=TOKEN_TTL_DAYS)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def _decode_jwt(token: str) -> dict | None:
    try:
        return jwt.decode(
            token, JWT_SECRET, algorithms=["HS256"],
            options={"verify_aud": False},
        )
    except Exception:
        return None


@router.post("/activate", response_model=ActivateResponse)
async def activate(payload: ActivateRequest):
    if not payload.activation_key or not payload.activation_key.strip():
        raise HTTPException(status_code=400, detail="activation_key is required")

    key_hash = _hash_key(payload.activation_key)
    supabase = get_supabase()

    try:
        result = (
            supabase.table("access_tokens")
            .select("id, user_id, revoked")
            .eq("token_hash", key_hash)
            .single()
            .execute()
        )
    except Exception as e:
        err_str = str(e)
        # Expose the real Supabase error in development so it is diagnosable.
        raise HTTPException(status_code=401, detail=f"Lookup failed: {err_str}")

    row = result.data
    if not row:
        raise HTTPException(status_code=401, detail="Invalid activation key")
    if row.get("revoked"):
        raise HTTPException(status_code=403, detail="Activation key has been revoked")

    token = _mint_jwt(row["user_id"], row["id"])
    return {"access_token": token, "token_type": "bearer"}


@router.get("/auth/status")
async def auth_status(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
):
    """
    Extension calls this on startup / periodically.
    Returns { valid: true } when token is good and the activation key is not revoked.
    Returns { valid: false, reason: "..." } when the extension must re-activate.
    Never raises — always returns 200 so the extension can branch on `valid`.
    """
    if credentials is None or not credentials.credentials:
        return {"valid": False, "reason": "no_token"}

    payload = _decode_jwt(credentials.credentials)
    if payload is None:
        return {"valid": False, "reason": "invalid_token"}

    token_id = payload.get("jti")
    if not token_id:
        # Older token minted before jti was added — force re-activation
        return {"valid": False, "reason": "reactivation_required"}

    supabase = get_supabase()
    try:
        result = (
            supabase.table("access_tokens")
            .select("revoked")
            .eq("id", token_id)
            .single()
            .execute()
        )
        row = result.data
    except Exception:
        # Cannot reach DB — let the token pass so offline use still works
        return {"valid": True, "reason": "db_unreachable"}

    if not row:
        return {"valid": False, "reason": "activation_key_not_found"}
    if row.get("revoked"):
        return {"valid": False, "reason": "activation_key_revoked"}

    return {"valid": True, "reason": "ok"}
