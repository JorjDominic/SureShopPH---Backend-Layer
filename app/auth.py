"""JWT verification + profile role checks."""
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import JWT_SECRET
from app.db.supabase_client import get_supabase
from app.logging_config import get_logger

log = get_logger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)


def verify_token(token: str) -> str | None:
    """Decode JWT. Logs the *category* of failure but never the secret/payload."""
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
        return payload.get("sub")
    except jwt.ExpiredSignatureError:
        log.info("auth: token expired")
        return None
    except jwt.InvalidSignatureError:
        log.warning("auth: invalid signature (possible tampering)")
        return None
    except jwt.DecodeError:
        log.warning("auth: malformed token")
        return None
    except Exception as e:  # pragma: no cover - defensive
        log.warning("auth: token verification failed: %s", e.__class__.__name__)
        return None


async def get_user_profile(user_id: str) -> dict | None:
    supabase = get_supabase()
    try:
        result = (
            supabase.table("profiles")
            .select("id, email, role, full_name")
            .eq("id", user_id)
            .single()
            .execute()
        )
        return result.data
    except Exception as e:
        log.info("auth: profile lookup failed for %s: %s", user_id, e.__class__.__name__)
        return None


def is_admin(profile: dict | None) -> bool:
    if not profile:
        return False
    return profile.get("role") == "admin"


async def require_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    user_id = verify_token(credentials.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    profile = await get_user_profile(user_id)
    if not profile:
        # Token is valid but profile row is missing. Reject rather than silently
        # granting "user" — this prevents bypass of role-gated logic in the rare
        # case profile rows are deleted while access tokens remain valid.
        log.warning("auth: token valid but no profile row for user_id=%s", user_id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account profile not found. Please re-activate.",
        )
    return profile


async def require_admin(profile: dict = Depends(require_user)) -> dict:
    if not is_admin(profile):
        raise HTTPException(status_code=403, detail="Admin access required")
    return profile
