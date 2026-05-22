"""Admin-only endpoints for managing fake-review training data and retraining the model."""
from __future__ import annotations
import os
import shutil
import threading
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field, model_validator

from app.auth import require_admin
from app.db.queries import (
    list_model_versions, get_active_model_version, set_active_model_version,
    insert_model_version, soft_delete_training_sample, write_admin_log,
)
from app.db.supabase_client import get_supabase
from app.logging_config import get_logger
from app.rate_limit import rate_limit_admin
from app.services import ml_classifier

router = APIRouter(prefix="/admin", tags=["training"])
log = get_logger(__name__)

# In-memory training job registry. Single-process only — for multi-worker
# deployments swap this for a Redis hash or a `training_jobs` DB table.
_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()


class TrainingSampleIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    # Accept either label:"suspicious"/"credible" (new format) OR
    # is_fake:bool (legacy format from older clients/extension).
    label: Optional[str] = Field(None, pattern="^(suspicious|credible)$")
    is_fake: Optional[bool] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def resolve_label(self) -> "TrainingSampleIn":
        if self.label is None:
            if self.is_fake is None:
                raise ValueError("Either 'label' or 'is_fake' must be provided")
            self.label = "suspicious" if self.is_fake else "credible"
        return self


class TrainingSampleBulkIn(BaseModel):
    samples: List[TrainingSampleIn]


@router.post("/training-data")
async def submit_training_sample(
    payload: TrainingSampleIn,
    admin=Depends(require_admin),
    _rl=Depends(rate_limit_admin),
):
    log.info("training-data POST reached: text_len=%d label=%r notes=%r admin_id=%s",
             len(payload.text), payload.label, payload.notes, admin.get("id"))
    supabase = get_supabase()
    row = {
        "text": payload.text.strip(),
        "label": payload.label,
        "notes": payload.notes,
        "submitted_by": admin["id"],
    }
    try:
        res = supabase.table("training_data").insert(row).execute()
        inserted = (res.data or [None])[0]
    except Exception as e:
        log.error("training-data insert failed: %s %s", e.__class__.__name__, e)
        raise HTTPException(status_code=500, detail=f"Insert failed: {e}")
    write_admin_log(admin["id"], "training_data_insert", {
        "sample_id": (inserted or {}).get("id"),
        "label": payload.label,
    })
    return {"data": inserted}


@router.post("/training-data/bulk")
async def submit_training_samples_bulk(
    payload: TrainingSampleBulkIn,
    admin=Depends(require_admin),
    _rl=Depends(rate_limit_admin),
):
    if not payload.samples:
        raise HTTPException(status_code=400, detail="samples is empty")

    supabase = get_supabase()
    rows = [
        {
            "text": s.text.strip(),
            "label": s.label,
            "notes": s.notes,
            "submitted_by": admin["id"],
        }
        for s in payload.samples
    ]
    try:
        res = supabase.table("training_data").insert(rows).execute()
    except Exception as e:
        log.error("training-data bulk insert failed: %s", e.__class__.__name__)
        raise HTTPException(status_code=500, detail=f"Bulk insert failed: {e}")
    write_admin_log(admin["id"], "training_data_bulk_insert", {
        "count": len(res.data or []),
    })
    return {"inserted": len(res.data or []), "data": res.data}


@router.get("/training-data")
async def list_training_data(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    label: Optional[str] = Query(None),
    include_deleted: bool = Query(False),
    admin=Depends(require_admin),
):
    supabase = get_supabase()
    try:
        q = (
            supabase.table("training_data")
            .select("*", count="exact")
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
        )
        if label is not None:
            q = q.eq("label", label)
        if not include_deleted:
            q = q.is_("deleted_at", "null")
        res = q.execute()
        return {"data": res.data or [], "total": res.count, "limit": limit, "offset": offset}
    except Exception as e:
        log.error("training-data list failed: %s", e.__class__.__name__)
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")


@router.get("/training-data/stats")
async def training_stats(admin=Depends(require_admin)):
    supabase = get_supabase()
    try:
        fake_res = (
            supabase.table("training_data")
            .select("id", count="exact")
            .eq("label", "suspicious")
            .is_("deleted_at", "null")
            .execute()
        )
        real_res = (
            supabase.table("training_data")
            .select("id", count="exact")
            .eq("label", "credible")
            .is_("deleted_at", "null")
            .execute()
        )
        fake_count = fake_res.count or 0
        real_count = real_res.count or 0
        total = fake_count + real_count
        recommended_min = 200
        return {
            "total": total,
            "fake": fake_count,
            "real": real_count,
            "recommended_min": recommended_min,
            "ready_to_train": total >= recommended_min and fake_count > 0 and real_count > 0,
        }
    except Exception as e:
        log.error("training-data stats failed: %s", e.__class__.__name__)
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")


@router.delete("/training-data/{sample_id}")
async def delete_training_sample(
    sample_id: str,
    admin=Depends(require_admin),
    _rl=Depends(rate_limit_admin),
):
    """Soft delete — preserves the row for audit/restore."""
    row = soft_delete_training_sample(sample_id, admin["id"])
    write_admin_log(admin["id"], "training_data_soft_delete", {"sample_id": sample_id})
    return {"deleted": sample_id, "row": row}


def _train_pipeline_sync(rows: List[dict]) -> dict:
    """Heavy training step — runs in threadpool. Returns metrics dict."""
    from sklearn.pipeline import Pipeline
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import cross_val_score, cross_val_predict
    from sklearn.metrics import precision_recall_fscore_support
    import joblib

    texts = [r["text"] for r in rows]
    labels = [1 if r["label"] == "suspicious" else 0 for r in rows]

    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=5000,
            min_df=1,
            sublinear_tf=True,
        )),
        ("clf", LogisticRegression(class_weight="balanced", max_iter=1000)),
    ])

    accuracy: float | None = None
    precision: float | None = None
    recall: float | None = None
    f1: float | None = None

    if len(rows) >= 50:
        try:
            scores = cross_val_score(pipeline, texts, labels, cv=5, scoring="accuracy")
            accuracy = float(scores.mean())
            preds = cross_val_predict(pipeline, texts, labels, cv=5)
            p, r, f, _ = precision_recall_fscore_support(
                labels, preds, average="binary", pos_label=1, zero_division=0,
            )
            precision, recall, f1 = float(p), float(r), float(f)
        except Exception:
            pass

    pipeline.fit(texts, labels)

    os.makedirs(os.path.dirname(ml_classifier.MODEL_PATH), exist_ok=True)
    # Save the active path AND a versioned snapshot for rollback.
    joblib.dump(pipeline, ml_classifier.MODEL_PATH)
    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def _run_training_job(job_id: str, rows: List[dict], admin_id: str) -> None:
    """Full training job — runs in a daemon thread. Updates _jobs as it goes."""
    def _update(**kwargs):
        with _jobs_lock:
            _jobs[job_id].update(kwargs)

    _update(status="running", started_at=datetime.now(timezone.utc).isoformat())
    try:
        metrics = _train_pipeline_sync(rows)

        fake_count = sum(1 for r in rows if r["label"] == "suspicious")
        real_count = len(rows) - fake_count

        version_row = insert_model_version({
            "sample_count": len(rows),
            "fake_count": fake_count,
            "real_count": real_count,
            "accuracy": metrics["accuracy"],
            "precision": metrics["precision"],
            "recall": metrics["recall"],
            "f1": metrics["f1"],
            "trained_by": admin_id,
            "is_active": True,
        })
        if version_row and version_row.get("id"):
            snap_path = os.path.join(
                os.path.dirname(ml_classifier.MODEL_PATH),
                f"fake_review_model_v{version_row['id']}.pkl",
            )
            try:
                shutil.copyfile(ml_classifier.MODEL_PATH, snap_path)
            except Exception as e:
                log.warning("snapshot copy failed: %s", e.__class__.__name__)
            set_active_model_version(version_row["id"])

        ml_classifier.reload_model()

        write_admin_log(admin_id, "train_model", {
            "version_id": (version_row or {}).get("id"),
            "samples": len(rows),
            "accuracy": metrics["accuracy"],
            "f1": metrics["f1"],
        })

        _update(
            status="done",
            finished_at=datetime.now(timezone.utc).isoformat(),
            result={
                "trained": True,
                "sample_count": len(rows),
                "fake": fake_count,
                "real": real_count,
                **metrics,
                "version_id": (version_row or {}).get("id"),
                "model_path": ml_classifier.MODEL_PATH,
            },
        )
    except Exception as e:
        log.exception("Training job %s failed", job_id)
        _update(
            status="failed",
            finished_at=datetime.now(timezone.utc).isoformat(),
            error=f"{e.__class__.__name__}: {e}",
        )


@router.post("/train-model")
async def train_model(
    admin=Depends(require_admin),
    _rl=Depends(rate_limit_admin),
):
    """Queue a training job. Returns immediately with a job_id; poll
    `GET /admin/training-status/{job_id}` for status and result."""
    supabase = get_supabase()
    rows: List[dict] = []
    page = 0
    page_size = 1000
    while True:
        try:
            res = (
                supabase.table("training_data")
                .select("text, label")
                .is_("deleted_at", "null")
                .range(page * page_size, (page + 1) * page_size - 1)
                .execute()
            )
        except Exception as e:
            log.error("training-data fetch failed: %s", e.__class__.__name__)
            raise HTTPException(status_code=500, detail=f"Query failed: {e}")
        batch = res.data or []
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < page_size:
            break
        page += 1

    if len(rows) < 20:
        raise HTTPException(
            status_code=400,
            detail=f"Need at least 20 samples to train, have {len(rows)}",
        )

    fake_count = sum(1 for r in rows if r["label"] == "suspicious")
    real_count = len(rows) - fake_count
    if fake_count == 0 or real_count == 0:
        raise HTTPException(
            status_code=400,
            detail="Need both fake and real samples (at least one of each).",
        )

    job_id = str(uuid.uuid4())
    with _jobs_lock:
        _jobs[job_id] = {
            "status": "queued",
            "queued_at": datetime.now(timezone.utc).isoformat(),
            "sample_count": len(rows),
            "fake": fake_count,
            "real": real_count,
            "queued_by": admin["id"],
        }

    threading.Thread(
        target=_run_training_job,
        args=(job_id, rows, admin["id"]),
        daemon=True,
    ).start()

    return {
        "job_id": job_id,
        "status": "queued",
        "sample_count": len(rows),
        "fake": fake_count,
        "real": real_count,
        "poll_url": f"/admin/training-status/{job_id}",
    }


@router.get("/training-status/{job_id}")
async def get_training_status(job_id: str, admin=Depends(require_admin)):
    """Poll the status of a background training job."""
    with _jobs_lock:
        job = dict(_jobs.get(job_id) or {})
    if not job:
        raise HTTPException(status_code=404, detail="Training job not found")
    return {"job_id": job_id, **job}


@router.get("/training-jobs")
async def list_training_jobs(admin=Depends(require_admin)):
    """List recent training jobs (in-memory; resets on restart)."""
    with _jobs_lock:
        snapshot = [{"job_id": jid, **info} for jid, info in _jobs.items()]
    snapshot.sort(key=lambda j: j.get("queued_at", ""), reverse=True)
    return {"data": snapshot[:50]}


@router.get("/model-stats")
async def model_stats(admin=Depends(require_admin)):
    history = list_model_versions(limit=25)
    active = get_active_model_version()
    return {
        "model_loaded": ml_classifier.is_model_loaded(),
        "model_path": ml_classifier.MODEL_PATH,
        "active_version_id": (active or {}).get("id"),
        "active": active,
        "history": history,
    }


@router.get("/model-versions")
async def get_model_versions(
    admin=Depends(require_admin),
    limit: int = Query(25, ge=1, le=100),
):
    return {"data": list_model_versions(limit=limit), "active": get_active_model_version()}


@router.post("/model-versions/{version_id}/activate")
async def activate_model_version(
    version_id: str,
    admin=Depends(require_admin),
    _rl=Depends(rate_limit_admin),
):
    """Activate a previously trained model snapshot — copies it back to the active path."""
    snap_path = os.path.join(
        os.path.dirname(ml_classifier.MODEL_PATH),
        f"fake_review_model_v{version_id}.pkl",
    )
    if not os.path.exists(snap_path):
        raise HTTPException(
            status_code=404,
            detail="Snapshot file not found on disk for this version",
        )
    try:
        shutil.copyfile(snap_path, ml_classifier.MODEL_PATH)
    except Exception as e:
        log.exception("activate snapshot copy failed")
        raise HTTPException(status_code=500, detail=f"Could not activate: {e}")

    row = set_active_model_version(version_id)
    ml_classifier.reload_model()
    write_admin_log(admin["id"], "model_version_activate", {"version_id": version_id})
    return {"activated": True, "version": row}
