"""
Application service for floor-plan upload and ingestion.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import aiofiles
from bson import ObjectId
from fastapi import HTTPException, Request, UploadFile

from app.core.config import settings
from app.core.metrics import file_upload_size_bytes, file_uploads_total
from app.core.validation import FloorSchema
from app.services.audit_log import record_event
from app.services.floor_plan_repository import get_floor_plan_repository
from app.services.floor_plan_document_service import (
    extract_detected_elements,
    is_usable_detected_elements,
    normalize_processing_options,
)
from app.services.floorplan_cache import (
    get_cached_processing as get_cached_floorplan_processing,
    make_cache_key as make_floorplan_cache_key,
    store_cached_processing as store_cached_floorplan_processing,
)
from app.services.idempotency import (
    build_idempotency_key,
    build_replay_response,
    get_cached_response,
    store_response,
)

logger = logging.getLogger(__name__)


def _safe_audit(
    action: str,
    actor: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    severity: str = "info",
) -> None:
    try:
        record_event(action=action, actor=actor, metadata=metadata, severity=severity)
    except Exception:
        pass


class SimulationUploadService:
    async def upload_floor_plan(
        self,
        request: Request,
        *,
        file: Optional[UploadFile],
        metadata: Optional[str],
        current_user: dict,
    ) -> Dict[str, Any]:
        correlation_id = getattr(request.state, "correlation_id", "unknown")
        user_id = str(current_user.get("_id", current_user.get("id", "demo_user")))
        raw_idempotency_key = request.headers.get("Idempotency-Key")
        idempotency_key = None
        if not getattr(request.state, "skip_idempotency", False):
            idempotency_key = build_idempotency_key(request, user_id)
            if idempotency_key:
                cached = get_cached_response(idempotency_key)
                if cached:
                    return build_replay_response(cached)

        building_name = "Building"
        floors = []
        file_size = None
        saved_path = None
        filename = "plan.json"
        file_type = "unknown"
        file_hash = None
        detected_elements: Dict[str, Any] = {}
        processing_options: Dict[str, Any] = normalize_processing_options({})

        try:
            logger.info(
                "Upload request received: file=%s, metadata=%s",
                file.filename if file else None,
                metadata is not None,
                extra={"correlation_id": correlation_id},
            )

            if file is None:
                (
                    building_name,
                    floors,
                    filename,
                    file_type,
                    file_size,
                    file_hash,
                    saved_path,
                    detected_elements,
                    processing_options,
                ) = await self._handle_json_upload(request, correlation_id, processing_options)
            else:
                (
                    building_name,
                    floors,
                    filename,
                    file_type,
                    file_size,
                    file_hash,
                    saved_path,
                    detected_elements,
                    processing_options,
                ) = await self._handle_file_upload(
                    file=file,
                    metadata=metadata,
                    correlation_id=correlation_id,
                    processing_options=processing_options,
                )
        except HTTPException:
            raise
        except Exception as exc:
            error_type = type(exc).__name__
            error_msg = str(exc)
            logger.error(
                "Error processing upload: %s: %s",
                error_type,
                error_msg,
                extra={"correlation_id": correlation_id},
                exc_info=True,
            )
            try:
                file_uploads_total.labels(file_type=file_type or "unknown", status="error").inc()
            except Exception:
                pass
            raise HTTPException(status_code=500, detail=f"Upload failed: {error_type}: {error_msg}")

        floor_plan, floor_plan_id = await self._persist_floor_plan(
            correlation_id=correlation_id,
            user_id=user_id,
            file=file,
            filename=filename,
            saved_path=saved_path,
            file_size=file_size,
            file_hash=file_hash,
            building_name=building_name,
            floors=floors,
            detected_elements=detected_elements,
            processing_options=processing_options,
        )

        processing_metadata = self._build_processing_metadata(detected_elements)
        _safe_audit(
            "floor_plan_uploaded",
            actor=user_id,
            metadata={
                "floor_plan_id": floor_plan_id,
                "building_name": building_name,
                "file_type": file_type,
                "file_size": file_size,
                "file_hash": file_hash,
                "processing_options": normalize_processing_options(processing_options or {}),
                "processing": {
                    "processed": processing_metadata.get("processed", False),
                    "wall_count": processing_metadata.get("wall_count"),
                    "exit_count": processing_metadata.get("exit_count"),
                    "obstacle_count": processing_metadata.get("obstacle_count"),
                    "quality": processing_metadata.get("quality"),
                },
            },
        )

        response_payload = {
            "id": floor_plan_id,
            "filename": filename,
            "building_name": building_name,
            "floors": floors,
            "file_path": saved_path,
            "file_hash": file_hash,
            "detected_walls": detected_elements.get("walls", []) if detected_elements else [],
            "detected_exits": detected_elements.get("exits", []) if detected_elements else [],
            "detected_obstacles": detected_elements.get("obstacles", []) if detected_elements else [],
            "boundaries": detected_elements.get("boundaries", []) if detected_elements else [],
            "boundary_polygon": detected_elements.get("boundary_polygon", []) if detected_elements else [],
            "boundary_area": detected_elements.get("boundary_area") if detected_elements else None,
            "rooms": detected_elements.get("rooms", []) if detected_elements else [],
            "corridors": detected_elements.get("corridors", []) if detected_elements else [],
            "open_spaces": detected_elements.get("open_spaces", []) if detected_elements else [],
            "doors": detected_elements.get("doors", []) if detected_elements else [],
            "building_bounds": detected_elements.get("building_bounds", {}) if detected_elements else {},
            "image_dimensions": detected_elements.get("image_dimensions", {}) if detected_elements else {},
            "quality": detected_elements.get("quality", {}) if detected_elements else {},
            "pipeline": detected_elements.get("pipeline", "unknown") if detected_elements else "unknown",
            "processing_time_ms": detected_elements.get("processing_time_ms") if detected_elements else None,
            "processing_options": normalize_processing_options(processing_options or {}),
            "detector_mode": detected_elements.get("detector_mode", "auto") if detected_elements else "auto",
            "detector_health": detected_elements.get("detector_health", "poor") if detected_elements else "poor",
            "fallback_reason": detected_elements.get("fallback_reason") if detected_elements else None,
            "quality_report": detected_elements.get("quality_report", {}) if detected_elements else {},
            "model_bundle_version": detected_elements.get("model_bundle_version") if detected_elements else None,
            "simulation_ready": bool(detected_elements.get("simulation_ready")) if detected_elements else False,
            "processing_metadata": processing_metadata,
            "revision": 1,
            "message": "Floor plan uploaded successfully",
        }

        if idempotency_key:
            store_response(
                idempotency_key,
                200,
                response_payload,
                {"Idempotency-Key": raw_idempotency_key or idempotency_key},
                {"path": request.url.path},
            )

        return response_payload

    async def _handle_json_upload(
        self,
        request: Request,
        correlation_id: str,
        processing_options: Dict[str, Any],
    ):
        try:
            try:
                body = await request.json()
            except Exception:
                form_data = await request.form()
                metadata_str = form_data.get("metadata")
                if metadata_str:
                    body = json.loads(metadata_str)
                else:
                    raise HTTPException(status_code=400, detail="No file or JSON data provided")

            building_name = body.get("buildingName") or "Building"
            floors_data = body.get("floors", [])
            if isinstance(body.get("processingOptions"), dict):
                processing_options = normalize_processing_options(body.get("processingOptions") or {})

            if not floors_data:
                floors_data = [{"floorNumber": 1, "name": "Floor 1", "exits": []}]

            floors = self._normalize_floors(floors_data, correlation_id)
            if not floors:
                floors = [{"floorNumber": 1, "name": "Floor 1", "exits": []}]

            filename = body.get("fileName", "plan.json")
            file_type = "json"
            serialized_body = json.dumps(body, sort_keys=True)
            file_size = len(serialized_body.encode("utf-8"))
            file_hash = hashlib.sha256(serialized_body.encode("utf-8")).hexdigest()
            saved_path = None
            detected_elements: Dict[str, Any] = {}
            return (
                building_name,
                floors,
                filename,
                file_type,
                file_size,
                file_hash,
                saved_path,
                detected_elements,
                processing_options,
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(
                "Error parsing JSON upload: %s",
                exc,
                extra={"correlation_id": correlation_id},
                exc_info=True,
            )
            raise HTTPException(status_code=400, detail=f"Invalid JSON payload for floor plan: {str(exc)}")

    async def _handle_file_upload(
        self,
        *,
        file: UploadFile,
        metadata: Optional[str],
        correlation_id: str,
        processing_options: Dict[str, Any],
    ):
        file_ext = os.path.splitext(file.filename or "")[1].lower() if file.filename else ""
        allowed_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp", ".json", ".pdf"]

        content_type_allowed = file.content_type in settings.ALLOWED_FILE_TYPES if file.content_type else False
        extension_allowed = file_ext in allowed_extensions
        if not content_type_allowed and not extension_allowed:
            file_uploads_total.labels(file_type=file.content_type or "unknown", status="rejected").inc()
            raise HTTPException(
                status_code=400,
                detail=(
                    f"File type not allowed. Allowed types: {', '.join(settings.ALLOWED_FILE_TYPES)} "
                    f"or extensions: {', '.join(allowed_extensions)}"
                ),
            )

        file_content = await file.read()
        file_size = len(file_content)
        file_type = file.content_type or "unknown"
        file_hash = hashlib.sha256(file_content).hexdigest()
        if file_size > settings.MAX_UPLOAD_SIZE:
            file_uploads_total.labels(file_type=file_type, status="too_large").inc()
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE / 1024 / 1024:.1f}MB",
            )

        building_name = "Building"
        floors = []
        if metadata:
            building_name, floors, processing_options = self._parse_upload_metadata(
                metadata,
                correlation_id,
                processing_options,
            )

        upload_dir = self._resolve_upload_dir(correlation_id)
        safe_filename = os.path.basename(file.filename or "uploaded_file").replace("..", "").replace("/", "").replace("\\", "")
        if not safe_filename:
            safe_filename = "uploaded_file"
        try:
            file_id = str(ObjectId())
        except Exception:
            file_id = str(uuid.uuid4())
        saved_path = os.path.join(upload_dir, f"{file_id}_{safe_filename}")
        os.makedirs(os.path.dirname(saved_path), exist_ok=True)

        try:
            async with aiofiles.open(saved_path, "wb") as handle:
                await handle.write(file_content)
            logger.info("File saved to: %s", saved_path, extra={"correlation_id": correlation_id})
        except Exception as exc:
            logger.error("Failed to save file: %s", exc, extra={"correlation_id": correlation_id})
            raise HTTPException(status_code=500, detail=f"Failed to save file: {str(exc)}")

        detected_elements = await self._detect_floor_plan(
            correlation_id=correlation_id,
            file_hash=file_hash,
            processing_options=processing_options,
            file_type=file_type,
            saved_path=saved_path,
            filename=safe_filename,
        )

        try:
            file_upload_size_bytes.observe(file_size)
            file_uploads_total.labels(file_type=file_type, status="success").inc()
        except Exception as metrics_error:
            logger.warning("Failed to track metrics: %s", metrics_error, extra={"correlation_id": correlation_id})

        return (
            building_name,
            floors,
            safe_filename,
            file_type,
            file_size,
            file_hash,
            saved_path,
            detected_elements,
            processing_options,
        )

    def _parse_upload_metadata(
        self,
        metadata: str,
        correlation_id: str,
        processing_options: Dict[str, Any],
    ):
        building_name = "Building"
        floors = []
        try:
            meta = json.loads(metadata)
            building_name = meta.get("buildingName") or building_name
            floors_data = meta.get("floors", [])
            if isinstance(meta.get("processingOptions"), dict):
                processing_options = normalize_processing_options(meta.get("processingOptions") or {})
            if floors_data:
                floors = self._normalize_floors(floors_data, correlation_id)
        except json.JSONDecodeError as exc:
            logger.warning("Invalid JSON in metadata: %s, using defaults", exc, extra={"correlation_id": correlation_id})
        except Exception as exc:
            logger.warning("Error parsing metadata: %s, using defaults", exc, extra={"correlation_id": correlation_id})
        return building_name, floors, processing_options

    def _normalize_floors(self, floors_data: Any, correlation_id: str):
        floors = []
        for floor_data in floors_data or []:
            try:
                floor_obj = FloorSchema(**floor_data)
                floors.append(floor_obj.model_dump() if hasattr(floor_obj, "model_dump") else floor_obj.dict())
            except Exception as exc:
                logger.warning("Invalid floor data: %s, skipping", exc, extra={"correlation_id": correlation_id})
        return floors

    def _resolve_upload_dir(self, correlation_id: str) -> str:
        try:
            upload_dir = settings.UPLOAD_DIR
            if not os.path.isabs(upload_dir):
                upload_dir = os.path.join(os.getcwd(), upload_dir)
            try:
                os.makedirs(upload_dir, exist_ok=True)
            except OSError as exc:
                if getattr(exc, "errno", None) == 30 or "Read-only file system" in str(exc):
                    upload_dir = "/tmp/uploads"
                    os.makedirs(upload_dir, exist_ok=True)
                    logger.warning(
                        "Primary upload directory is read-only, using fallback: %s",
                        upload_dir,
                        extra={"correlation_id": correlation_id},
                    )
                else:
                    raise
            logger.info("Upload directory: %s", upload_dir, extra={"correlation_id": correlation_id})
            return upload_dir
        except Exception as exc:
            logger.error("Failed to create upload directory: %s", exc, extra={"correlation_id": correlation_id})
            raise HTTPException(status_code=500, detail=f"Failed to create upload directory: {str(exc)}")

    async def _detect_floor_plan(
        self,
        *,
        correlation_id: str,
        file_hash: str,
        processing_options: Dict[str, Any],
        file_type: str,
        saved_path: str,
        filename: str,
    ) -> Dict[str, Any]:
        cache_key = make_floorplan_cache_key(file_hash, processing_options)
        detected_elements = get_cached_floorplan_processing(cache_key) if cache_key else None
        is_image_upload = (file_type or "").startswith("image/") or os.path.splitext(filename or "")[1].lower() in {
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".webp",
            ".bmp",
            ".tif",
            ".tiff",
        }
        if not is_usable_detected_elements(detected_elements, is_image_upload):
            detected_elements = None

        if not detected_elements:
            cached_doc = None
            try:
                repository = await get_floor_plan_repository()
                cached_doc = await repository.find_by_hash(
                    file_hash,
                    normalize_processing_options(processing_options or {}),
                )
            except Exception:
                cached_doc = None

            if cached_doc:
                candidate_elements = extract_detected_elements(cached_doc)
                if is_usable_detected_elements(candidate_elements, is_image_upload):
                    detected_elements = candidate_elements
                try:
                    from app.core.metrics import floorplan_processing_cache_total

                    floorplan_processing_cache_total.labels(
                        source="database",
                        status="hit" if detected_elements else "stale",
                    ).inc()
                except Exception:
                    pass
            else:
                try:
                    from app.core.metrics import floorplan_processing_cache_total

                    floorplan_processing_cache_total.labels(source="database", status="miss").inc()
                except Exception:
                    pass

        if not detected_elements:
            from app.services.floorplan_service import process_floor_plan_image

            detected_elements = process_floor_plan_image(file_type, saved_path, processing_options)

        if detected_elements:
            store_cached_floorplan_processing(cache_key, detected_elements)
        return detected_elements or {}

    async def _persist_floor_plan(
        self,
        *,
        correlation_id: str,
        user_id: str,
        file: Optional[UploadFile],
        filename: str,
        saved_path: Optional[str],
        file_size: Optional[int],
        file_hash: Optional[str],
        building_name: str,
        floors: Any,
        detected_elements: Dict[str, Any],
        processing_options: Dict[str, Any],
    ):
        floor_plan = {
            "user_id": user_id,
            "tenant_id": "global",
            "filename": filename,
            "file_path": saved_path,
            "file_size": file_size,
            "file_hash": file_hash,
            "content_type": (file.content_type if file else "application/json") or "application/octet-stream",
            "building_name": building_name,
            "floors": floors,
            "detected_walls": detected_elements.get("walls", []),
            "detected_exits": detected_elements.get("exits", []),
            "detected_obstacles": detected_elements.get("obstacles", []),
            "boundaries": detected_elements.get("boundaries", []),
            "boundary_polygon": detected_elements.get("boundary_polygon", []),
            "boundary_area": detected_elements.get("boundary_area"),
            "rooms": detected_elements.get("rooms", []),
            "corridors": detected_elements.get("corridors", []),
            "open_spaces": detected_elements.get("open_spaces", []),
            "doors": detected_elements.get("doors", []),
            "building_bounds": detected_elements.get("building_bounds", {}),
            "image_dimensions": detected_elements.get("image_dimensions", {}),
            "quality": detected_elements.get("quality", {}),
            "pipeline": detected_elements.get("pipeline", "unknown"),
            "processing_time_ms": detected_elements.get("processing_time_ms"),
            "pipeline_steps": detected_elements.get("pipeline_steps", []),
            "processing_options": normalize_processing_options(processing_options or {}),
            "detector_mode": detected_elements.get("detector_mode", "auto"),
            "detector_health": detected_elements.get("detector_health", "poor"),
            "fallback_reason": detected_elements.get("fallback_reason"),
            "quality_report": detected_elements.get("quality_report", {}),
            "model_bundle_version": detected_elements.get("model_bundle_version"),
            "simulation_ready": bool(detected_elements.get("simulation_ready")),
            "revision": 1,
            "manual_exit_events": [],
            "processing_metadata": {
                "processed": detected_elements.get("processed", False),
                "wall_count": detected_elements.get("wall_count", 0),
                "exit_count": detected_elements.get("exit_count", 0),
                "obstacle_count": detected_elements.get("obstacle_count", 0),
                "room_count": detected_elements.get("room_count", 0),
                "corridor_count": detected_elements.get("corridor_count", 0),
                "open_space_count": detected_elements.get("open_space_count", 0),
                "door_count": detected_elements.get("door_count", 0),
                "image_dimensions": detected_elements.get("image_dimensions", {}),
                "building_bounds": detected_elements.get("building_bounds", {}),
                "boundary_polygon": detected_elements.get("boundary_polygon", []),
                "boundary_area": detected_elements.get("boundary_area"),
                "quality": detected_elements.get("quality", {}),
                "pipeline": detected_elements.get("pipeline", "unknown"),
                "processing_time_ms": detected_elements.get("processing_time_ms"),
                "pipeline_steps": detected_elements.get("pipeline_steps", []),
                "detector_mode": detected_elements.get("detector_mode", "auto"),
                "detector_health": detected_elements.get("detector_health", "poor"),
                "fallback_reason": detected_elements.get("fallback_reason"),
                "quality_report": detected_elements.get("quality_report", {}),
                "model_bundle_version": detected_elements.get("model_bundle_version"),
                "simulation_ready": bool(detected_elements.get("simulation_ready")),
            },
            "created_at": datetime.now(timezone.utc),
        }
        floor_plan["updated_at"] = floor_plan["created_at"]

        try:
            repository = await get_floor_plan_repository()
            floor_plan_id = await repository.create(floor_plan)
        except Exception as exc:
            if not settings.IS_DEMO_MODE:
                logger.error("Database unavailable while saving floor plan in production mode: %s", exc, exc_info=True)
                raise HTTPException(status_code=503, detail="Database unavailable")
            logger.warning(
                "Database unavailable, using mock ID: %s",
                exc,
                extra={"correlation_id": correlation_id},
                exc_info=True,
            )
            floor_plan_id = f"mock-{uuid.uuid4().hex[:12]}"

        return floor_plan, floor_plan_id

    @staticmethod
    def _build_processing_metadata(detected_elements: Dict[str, Any]) -> Dict[str, Any]:
        if not detected_elements:
            return {}
        return {
            "processed": detected_elements.get("processed", False),
            "wall_count": detected_elements.get("wall_count", len(detected_elements.get("walls", []))),
            "exit_count": detected_elements.get("exit_count", len(detected_elements.get("exits", []))),
            "obstacle_count": detected_elements.get("obstacle_count", len(detected_elements.get("obstacles", []))),
            "room_count": detected_elements.get("room_count", 0),
            "corridor_count": detected_elements.get("corridor_count", 0),
            "open_space_count": detected_elements.get("open_space_count", 0),
            "door_count": detected_elements.get("door_count", 0),
            "boundary_count": len(detected_elements.get("boundaries", [])),
            "boundary_area": detected_elements.get("boundary_area"),
            "image_dimensions": detected_elements.get("image_dimensions", {}),
            "building_bounds": detected_elements.get("building_bounds", {}),
            "quality": detected_elements.get("quality", {}),
            "pipeline": detected_elements.get("pipeline", "unknown"),
            "processing_time_ms": detected_elements.get("processing_time_ms"),
            "pipeline_steps": detected_elements.get("pipeline_steps", []),
            "detector_mode": detected_elements.get("detector_mode", "auto"),
            "detector_health": detected_elements.get("detector_health", "poor"),
            "fallback_reason": detected_elements.get("fallback_reason"),
            "quality_report": detected_elements.get("quality_report", {}),
            "model_bundle_version": detected_elements.get("model_bundle_version"),
            "simulation_ready": bool(detected_elements.get("simulation_ready")),
        }


simulation_upload_service = SimulationUploadService()
