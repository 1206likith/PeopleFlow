"""
Upload route extracted from the main simulation router.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile

from app.core.request_context import get_request_actor
from app.services.simulation_upload_service import simulation_upload_service

router = APIRouter()


@router.post("/upload")
async def upload_floor_plan(
    request: Request,
    file: Optional[UploadFile] = File(None),
    metadata: Optional[str] = Form(None),
    current_user: dict = Depends(get_request_actor),
):
    """
    Upload a floor plan image or multi-floor JSON definition.
    Production-grade validation and metrics tracking.
    """
    return await simulation_upload_service.upload_floor_plan(
        request,
        file=file,
        metadata=metadata,
        current_user=current_user,
    )
