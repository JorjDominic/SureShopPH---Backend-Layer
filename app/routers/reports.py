"""POST /reports — submit a false positive or fraud report."""
from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_user
from app.models.schemas import ReportPayload
from app.db.queries import insert_user_report

router = APIRouter(tags=["reports"])


@router.post("/reports")
async def submit_report(payload: ReportPayload, user=Depends(require_user)):
    row = insert_user_report(
        user["id"],
        payload.listing_url,
        payload.report_type,
        payload.description,
    )
    if row is None:
        raise HTTPException(status_code=500, detail="Failed to submit report")
    return {"data": row}
