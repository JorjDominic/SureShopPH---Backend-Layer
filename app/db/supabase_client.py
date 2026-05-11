"""Supabase client singleton (service role key — bypasses RLS)."""
from supabase import create_client, Client
from app.config import SUPABASE_URL, SUPABASE_KEY

_supabase: Client | None = None


def get_supabase() -> Client:
    global _supabase
    if _supabase is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set in .env")
        _supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase


def ping() -> bool:
    """Lightweight connectivity check used by /health."""
    try:
        client = get_supabase()
        # head=True + count=exact returns no rows but verifies the table is reachable.
        client.table("profiles").select("id", count="exact", head=True).limit(1).execute()
        return True
    except Exception:
        return False
