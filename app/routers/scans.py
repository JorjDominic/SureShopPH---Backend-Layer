"""GET /scans/history and GET /listings/high-risk."""
from fastapi import APIRouter, Depends, Query

from app.auth import require_user
from app.db.queries import get_scan_history, get_high_risk_listings

router = APIRouter(tags=["scans"])


@router.get("/scans/history")
async def scans_history(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user=Depends(require_user),
):
    result = get_scan_history(user["id"], limit=limit, offset=offset)
    return {**result, "limit": limit, "offset": offset}


@router.get("/listings/high-risk")
async def listings_high_risk(
    limit: int = Query(100, ge=1, le=500),
    user=Depends(require_user),
):
    return {"data": get_high_risk_listings(limit=limit)}
