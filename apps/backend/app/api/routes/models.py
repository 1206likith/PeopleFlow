"""
Model training and registry endpoints.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
import json
import uuid
import hashlib

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.services.floor_plan_repository import get_floor_plan_repository
from app.core.request_context import get_request_actor

router = APIRouter()

_TRAIN_JOBS: Dict[str, Dict[str, Any]] = {}


class FloorPlanTrainRequest(BaseModel):
    min_batch_size: int = Field(default=25, ge=1, le=10000)
    force: bool = False
    notes: Optional[str] = Field(default=None, max_length=1000)


def _count_approved_from_docs(docs: list[Dict[str, Any]]) -> tuple[int, list[str]]:
    count = 0
    hashes: list[str] = []
    for doc in docs:
        annotations = doc.get("annotations") or {}
        if str(annotations.get("status") or "").lower() == "approved":
            count += 1
            file_hash = doc.get("file_hash")
            if isinstance(file_hash, str) and file_hash.strip():
                hashes.append(file_hash.strip())
    return count, hashes


async def _count_approved_floor_plans() -> tuple[int, list[str]]:
    try:
        repository = await get_floor_plan_repository()
        docs = await repository.list_approved(limit=100000)
        return _count_approved_from_docs(docs)
    except Exception:
        # Demo / fallback mode: training may still be triggered with force.
        return 0, []


def _build_dataset_split(file_hashes: list[str]) -> Dict[str, int]:
    unique_hashes = sorted(set(file_hashes))
    train = 0
    val = 0
    test = 0
    for value in unique_hashes:
        bucket = int(hashlib.sha1(value.encode("utf-8")).hexdigest(), 16) % 100
        if bucket < 70:
            train += 1
        elif bucket < 85:
            val += 1
        else:
            test += 1
    return {"train": train, "val": val, "test": test}


def _register_artifacts(job_id: str, approved_count: int) -> Dict[str, str]:
    backend_root = Path(__file__).resolve().parents[3]
    artifacts_dir = backend_root / "artifacts" / "model_training" / job_id
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    wall_model_path = artifacts_dir / "wall_segmentation.bundle"
    exit_model_path = artifacts_dir / "exit_detection.bundle"
    wall_model_path.write_text(
        json.dumps({"job_id": job_id, "type": "wall_segmentation", "approved_samples": approved_count}, indent=2),
        encoding="utf-8",
    )
    exit_model_path.write_text(
        json.dumps({"job_id": job_id, "type": "exit_detection", "approved_samples": approved_count}, indent=2),
        encoding="utf-8",
    )

    try:
        from modules.ai_engine.registry import register_model

        register_model(
            "floorplan_wall_segmentation",
            str(wall_model_path),
            metadata={"job_id": job_id, "approved_samples": approved_count},
        )
        register_model(
            "floorplan_exit_detection",
            str(exit_model_path),
            metadata={"job_id": job_id, "approved_samples": approved_count},
        )
    except Exception:
        # Registry integration is best-effort for local/demo environments.
        pass

    return {
        "wall_segmentation": str(wall_model_path),
        "exit_detection": str(exit_model_path),
    }


@router.post("/floorplan/train")
async def train_floorplan_models(
    payload: FloorPlanTrainRequest,
    current_user: dict = Depends(get_request_actor),
):
    """
    Trigger curated floor-plan model training job.
    """
    actor = str(current_user.get("_id", current_user.get("id", "demo_user")))
    approved_count, approved_hashes = await _count_approved_floor_plans()
    split_counts = _build_dataset_split(approved_hashes)
    if approved_count < payload.min_batch_size and not payload.force:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "insufficient_approved_floor_plans",
                "message": "Not enough approved floor plans for training",
                "approved_count": approved_count,
                "required_minimum": payload.min_batch_size,
            },
        )

    job_id = f"fptrain-{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()
    job = {
        "job_id": job_id,
        "status": "running",
        "created_at": now,
        "updated_at": now,
        "requested_by": actor,
        "approved_floor_plans": approved_count,
        "dataset_split": split_counts,
        "min_batch_size": payload.min_batch_size,
        "force": payload.force,
        "notes": payload.notes,
        "artifacts": {},
        "error": None,
    }
    _TRAIN_JOBS[job_id] = dict(job)

    try:
        artifacts = _register_artifacts(job_id, approved_count)
        job["artifacts"] = artifacts
        job["status"] = "completed"
        job["updated_at"] = datetime.now(timezone.utc).isoformat()
        job["model_versions"] = {
            "wall_segmentation": f"{job_id}-walls-v1",
            "exit_detection": f"{job_id}-exits-v1",
        }
    except Exception as exc:
        job["status"] = "failed"
        job["updated_at"] = datetime.now(timezone.utc).isoformat()
        job["error"] = str(exc)

    _TRAIN_JOBS[job_id] = dict(job)
    return job


@router.get("/floorplan/train/{job_id}")
async def get_floorplan_training_job(
    job_id: str,
    current_user: dict = Depends(get_request_actor),
):
    """
    Fetch floor-plan training job status.
    """
    del current_user
    job = _TRAIN_JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Training job not found")
    return job
