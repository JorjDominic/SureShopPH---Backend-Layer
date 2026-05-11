"""Admin-only endpoints."""
from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_admin
from app.models.schemas import VerifyListingPayload, AdminLogPayload
from app.rate_limit import rate_limit_admin
from app.db.queries import (
    list_all_reports, verify_high_risk_listing, write_admin_log, list_admin_logs,
)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/reports")
async def admin_reports(admin=Depends(require_admin), _rl=Depends(rate_limit_admin)):
    return {"data": list_all_reports()}


@router.patch("/listings/verify")
async def admin_verify_listing(
    payload: VerifyListingPayload,
    admin=Depends(require_admin),
    _rl=Depends(rate_limit_admin),
):
    row = verify_high_risk_listing(payload.listing_id, admin["id"], payload.verified)
    if row is None:
        raise HTTPException(status_code=404, detail="Listing not found")

    write_admin_log(admin["id"], "verify_listing", {
        "listing_id": payload.listing_id,
        "verified": payload.verified,
    })
    return {"data": row}


@router.get("/logs")
async def admin_get_logs(admin=Depends(require_admin), _rl=Depends(rate_limit_admin)):
    return {"data": list_admin_logs()}


@router.post("/logs")
async def admin_post_log(
    payload: AdminLogPayload,
    admin=Depends(require_admin),
    _rl=Depends(rate_limit_admin),
):
    write_admin_log(admin["id"], payload.action, payload.details)
    return {"status": "logged"}
