"""
Experiment artifact and publication bundle discovery API.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from app.core.request_context import get_request_actor
from app.services.experiment_artifact_service import experiment_artifact_service

router = APIRouter()


@router.get("/artifacts")
async def get_experiment_artifact_catalog(current_user: dict = Depends(get_request_actor)):
    """Get canonical catalog of experiment outputs, indexes, and publication bundles."""
    del current_user
    try:
        return experiment_artifact_service.build_catalog()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Experiment artifact catalog failed: {str(exc)}")


@router.get("/artifacts/records")
async def list_experiment_artifact_records(current_user: dict = Depends(get_request_actor)):
    """List lightweight experiment artifact summaries for reports, benchmarks, and exports."""
    del current_user
    try:
        return experiment_artifact_service.list_experiment_artifacts()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Experiment artifact listing failed: {str(exc)}")


@router.get("/artifacts/records/{artifact_id:path}/download")
async def download_experiment_artifact_record(
    artifact_id: str,
    kind: str = Query(default="artifact", pattern="^(artifact|manifest)$"),
    current_user: dict = Depends(get_request_actor),
):
    """Download an experiment artifact payload or its manifest."""
    del current_user
    try:
        path = experiment_artifact_service.resolve_experiment_artifact_download(artifact_id, kind=kind)
        return FileResponse(path=str(path), filename=path.name)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Experiment artifact download failed: {str(exc)}")


@router.get("/artifacts/records/{artifact_id:path}")
async def get_experiment_artifact_record(artifact_id: str, current_user: dict = Depends(get_request_actor)):
    """Get the full canonical record for a single experiment artifact."""
    del current_user
    try:
        return experiment_artifact_service.get_experiment_artifact(artifact_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Experiment artifact lookup failed: {str(exc)}")


@router.get("/publication-bundles")
async def list_publication_bundles(current_user: dict = Depends(get_request_actor)):
    """List publication-ready paper bundles as canonical artifact records."""
    del current_user
    try:
        return experiment_artifact_service.list_publication_bundles()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Publication bundle listing failed: {str(exc)}")


@router.get("/publication-bundles/{bundle_id}")
async def get_publication_bundle(bundle_id: str, current_user: dict = Depends(get_request_actor)):
    """Get a publication bundle manifest and canonical record by bundle id."""
    del current_user
    try:
        return experiment_artifact_service.get_publication_bundle(bundle_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Publication bundle lookup failed: {str(exc)}")


@router.get("/publication-bundles/{bundle_id}/download")
async def download_publication_bundle_manifest(
    bundle_id: str,
    kind: str = Query(default="manifest", pattern="^(manifest)$"),
    current_user: dict = Depends(get_request_actor),
):
    """Download a publication bundle manifest."""
    del current_user
    try:
        path = experiment_artifact_service.resolve_publication_bundle_download(bundle_id, kind=kind)
        return FileResponse(path=str(path), filename=path.name)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Publication bundle download failed: {str(exc)}")
