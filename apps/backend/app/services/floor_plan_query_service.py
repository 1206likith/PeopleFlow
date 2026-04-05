"""
Read-side query service for floor-plan metadata and diagnostics.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import HTTPException, Response

from app.core.config import settings
from app.services.floor_plan_document_service import (
    build_floor_plan_quality_report,
    filter_removed_detected_exits,
    fetch_floor_plan_doc,
    floor_plan_etag,
    normalize_detected_obstacles,
    normalize_processing_options,
)


class FloorPlanQueryService:
    async def get_exits(
        self,
        floor_plan_id: str,
        *,
        floor_number: Optional[int],
        current_user: dict,
        request: Any = None,
        response: Any = None,
    ) -> Dict[str, Any] | Response:
        user_id = str(current_user.get("_id", current_user.get("id", "demo_user")))
        floor_plan_doc = await fetch_floor_plan_doc(floor_plan_id, user_id)
        if not floor_plan_doc:
            raise HTTPException(status_code=404, detail="Floor plan not found")

        revision = int(floor_plan_doc.get("revision", 1))
        cached = self._apply_etag(
            floor_plan_id=floor_plan_id,
            floor_number=floor_number,
            revision=revision,
            suffix="exits",
            request=request,
            response=response,
        )
        if cached is not None:
            return cached

        from app.services.floorplan_loader import load_floor_plan_data

        manual_exits = floor_plan_doc.get("manual_exits", [])
        detected_exits = filter_removed_detected_exits(
            floor_plan_doc.get("detected_exits", []),
            floor_plan_doc.get("removed_detected_exit_ids", []),
        )
        if floor_number is not None:
            manual_exits = [e for e in manual_exits if e.get("floor_number") in (None, floor_number)]
            detected_exits = [e for e in detected_exits if e.get("floor_number") in (None, floor_number)]

        floor_plan_data, exits = await load_floor_plan_data(
            floor_plan_id,
            floor_number,
            configured_exits=None,
        )

        return {
            "floor_plan_id": floor_plan_id,
            "floor_number": floor_number,
            "manual_exits": manual_exits,
            "detected_exits": detected_exits,
            "exits": exits,
            "building_bounds": floor_plan_data.get("building_bounds") if floor_plan_data else None,
            "revision": revision,
        }

    async def get_metadata(
        self,
        floor_plan_id: str,
        *,
        floor_number: Optional[int],
        current_user: dict,
        request: Any = None,
        response: Any = None,
    ) -> Dict[str, Any] | Response:
        user_id = str(current_user.get("_id", current_user.get("id", "demo_user")))
        floor_plan_doc = await fetch_floor_plan_doc(floor_plan_id, user_id)
        if not floor_plan_doc:
            raise HTTPException(status_code=404, detail="Floor plan not found")

        revision = int(floor_plan_doc.get("revision", 1))
        cached = self._apply_etag(
            floor_plan_id=floor_plan_id,
            floor_number=floor_number,
            revision=revision,
            suffix="metadata",
            request=request,
            response=response,
        )
        if cached is not None:
            return cached

        from app.services.floorplan_loader import load_floor_plan_data

        floor_plan_data, exits = await load_floor_plan_data(
            floor_plan_id,
            floor_number,
            configured_exits=None,
        )

        manual_exits = floor_plan_doc.get("manual_exits", [])
        detected_exits = filter_removed_detected_exits(
            floor_plan_doc.get("detected_exits", []),
            floor_plan_doc.get("removed_detected_exit_ids", []),
        )
        if floor_number is not None:
            manual_exits = [
                e for e in manual_exits
                if (e.get("floor_number") or e.get("floorNumber")) in (None, floor_number)
            ]
            detected_exits = [
                e for e in detected_exits
                if (e.get("floor_number") or e.get("floorNumber")) in (None, floor_number)
            ]

        return {
            "id": floor_plan_id,
            "building_name": floor_plan_doc.get("building_name"),
            "floors": floor_plan_doc.get("floors", []),
            "file_path": floor_plan_doc.get("file_path"),
            "file_size": floor_plan_doc.get("file_size"),
            "content_type": floor_plan_doc.get("content_type"),
            "file_hash": floor_plan_doc.get("file_hash"),
            "detected_walls": floor_plan_doc.get("detected_walls", []),
            "detected_exits": detected_exits,
            "manual_exits": manual_exits,
            "detected_obstacles": (
                floor_plan_data.get("detected_obstacles")
                if floor_plan_data
                else normalize_detected_obstacles(floor_plan_doc.get("detected_obstacles", []))
            ),
            "boundaries": floor_plan_doc.get("boundaries", []),
            "rooms": floor_plan_doc.get("rooms", []),
            "corridors": floor_plan_doc.get("corridors", []),
            "open_spaces": floor_plan_doc.get("open_spaces", []),
            "doors": floor_plan_doc.get("doors", []),
            "building_bounds": floor_plan_doc.get("building_bounds") or (floor_plan_data.get("building_bounds") if floor_plan_data else None),
            "image_dimensions": floor_plan_doc.get("image_dimensions") or (floor_plan_data.get("image_dimensions") if floor_plan_data else None),
            "quality": floor_plan_doc.get("quality") or (floor_plan_data.get("quality") if floor_plan_data else None),
            "pipeline": floor_plan_doc.get("pipeline") or (floor_plan_data.get("pipeline") if floor_plan_data else None),
            "processing_time_ms": floor_plan_doc.get("processing_time_ms") or (floor_plan_data.get("processing_time_ms") if floor_plan_data else None),
            "pipeline_steps": floor_plan_doc.get("pipeline_steps") or (floor_plan_data.get("pipeline_steps") if floor_plan_data else None) or [],
            "processing_options": normalize_processing_options(floor_plan_doc.get("processing_options", {})),
            "detector_mode": floor_plan_doc.get("detector_mode") or (floor_plan_data.get("detector_mode") if floor_plan_data else None),
            "detector_health": floor_plan_doc.get("detector_health") or (floor_plan_data.get("detector_health") if floor_plan_data else None),
            "fallback_reason": floor_plan_doc.get("fallback_reason") or (floor_plan_data.get("fallback_reason") if floor_plan_data else None),
            "quality_report": floor_plan_doc.get("quality_report") or (floor_plan_data.get("quality_report") if floor_plan_data else None) or {},
            "model_bundle_version": floor_plan_doc.get("model_bundle_version") or (floor_plan_data.get("model_bundle_version") if floor_plan_data else None),
            "simulation_ready": (
                floor_plan_doc.get("simulation_ready")
                if floor_plan_doc.get("simulation_ready") is not None
                else (floor_plan_data.get("simulation_ready") if floor_plan_data else None)
            ),
            "processing_metadata": floor_plan_doc.get("processing_metadata", {}),
            "manual_exit_events": floor_plan_doc.get("manual_exit_events", []),
            "revision": revision,
            "floor_number": floor_number,
            "exits": exits,
            "created_at": floor_plan_doc.get("created_at"),
            "updated_at": floor_plan_doc.get("updated_at"),
        }

    async def get_pipeline(
        self,
        floor_plan_id: str,
        *,
        current_user: dict,
        request: Any = None,
        response: Any = None,
    ) -> Dict[str, Any] | Response:
        user_id = str(current_user.get("_id", current_user.get("id", "demo_user")))
        floor_plan_doc = await fetch_floor_plan_doc(floor_plan_id, user_id)
        if not floor_plan_doc:
            raise HTTPException(status_code=404, detail="Floor plan not found")

        revision = int(floor_plan_doc.get("revision", 1))
        cached = self._apply_etag(
            floor_plan_id=floor_plan_id,
            floor_number=None,
            revision=revision,
            suffix="pipeline",
            request=request,
            response=response,
        )
        if cached is not None:
            return cached

        processing_metadata = floor_plan_doc.get("processing_metadata", {})
        return {
            "floor_plan_id": floor_plan_id,
            "pipeline": floor_plan_doc.get("pipeline") or processing_metadata.get("pipeline"),
            "processing_time_ms": floor_plan_doc.get("processing_time_ms") or processing_metadata.get("processing_time_ms"),
            "pipeline_steps": (
                floor_plan_doc.get("pipeline_steps")
                or processing_metadata.get("pipeline_steps")
                or []
            ),
            "quality": floor_plan_doc.get("quality") or processing_metadata.get("quality", {}),
            "image_dimensions": floor_plan_doc.get("image_dimensions") or processing_metadata.get("image_dimensions", {}),
            "building_bounds": floor_plan_doc.get("building_bounds") or processing_metadata.get("building_bounds", {}),
            "processing_options": normalize_processing_options(floor_plan_doc.get("processing_options", {})),
            "detector_mode": floor_plan_doc.get("detector_mode") or processing_metadata.get("detector_mode"),
            "detector_health": floor_plan_doc.get("detector_health") or processing_metadata.get("detector_health"),
            "fallback_reason": floor_plan_doc.get("fallback_reason") or processing_metadata.get("fallback_reason"),
            "quality_report": floor_plan_doc.get("quality_report") or processing_metadata.get("quality_report", {}),
            "model_bundle_version": floor_plan_doc.get("model_bundle_version") or processing_metadata.get("model_bundle_version"),
            "simulation_ready": (
                floor_plan_doc.get("simulation_ready")
                if floor_plan_doc.get("simulation_ready") is not None
                else processing_metadata.get("simulation_ready")
            ),
            "revision": revision,
        }

    async def get_quality_report(
        self,
        floor_plan_id: str,
        *,
        floor_number: Optional[int],
        current_user: dict,
    ) -> Dict[str, Any]:
        user_id = str(current_user.get("_id", current_user.get("id", "demo_user")))
        floor_plan_doc = await fetch_floor_plan_doc(floor_plan_id, user_id)
        if not floor_plan_doc:
            raise HTTPException(status_code=404, detail="Floor plan not found")

        from app.services.floorplan_loader import load_floor_plan_data

        floor_plan_data, exits = await load_floor_plan_data(
            floor_plan_id,
            floor_number,
            configured_exits=None,
            allow_inferred_exits=settings.IS_DEMO_MODE,
        )
        report = floor_plan_doc.get("quality_report") or build_floor_plan_quality_report(
            floor_plan_doc,
            floor_plan_data,
            exits,
        )
        return {
            "floor_plan_id": floor_plan_id,
            "floor_number": floor_number,
            "quality_report": report,
            "detector_mode": floor_plan_doc.get("detector_mode") or (floor_plan_data or {}).get("detector_mode"),
            "detector_health": floor_plan_doc.get("detector_health") or (floor_plan_data or {}).get("detector_health"),
            "fallback_reason": floor_plan_doc.get("fallback_reason") or (floor_plan_data or {}).get("fallback_reason"),
            "model_bundle_version": floor_plan_doc.get("model_bundle_version") or (floor_plan_data or {}).get("model_bundle_version"),
            "simulation_ready": bool(report.get("simulation_ready")),
            "revision": int(floor_plan_doc.get("revision", 1)),
        }

    async def get_annotations(self, floor_plan_id: str, *, current_user: dict) -> Dict[str, Any]:
        user_id = str(current_user.get("_id", current_user.get("id", "demo_user")))
        floor_plan_doc = await fetch_floor_plan_doc(floor_plan_id, user_id)
        if not floor_plan_doc:
            raise HTTPException(status_code=404, detail="Floor plan not found")
        annotations = floor_plan_doc.get("annotations") or {}
        return {
            "floor_plan_id": floor_plan_id,
            "status": annotations.get("status", "new"),
            "walls": annotations.get("walls", []),
            "doors": annotations.get("doors", []),
            "exits": annotations.get("exits", []),
            "rooms": annotations.get("rooms", []),
            "notes": annotations.get("notes"),
            "updated_at": annotations.get("updated_at"),
            "updated_by": annotations.get("updated_by"),
            "revision": int(floor_plan_doc.get("revision", 1)),
        }

    @staticmethod
    def _apply_etag(
        *,
        floor_plan_id: str,
        floor_number: Optional[int],
        revision: int,
        suffix: str,
        request: Any,
        response: Any,
    ) -> Optional[Response]:
        if request is None:
            return None
        etag = floor_plan_etag(floor_plan_id, floor_number, revision, suffix)
        if request.headers.get("if-none-match") == etag:
            return Response(status_code=304)
        if response is not None:
            response.headers["ETag"] = etag
            response.headers["X-Resource-Revision"] = str(revision)
        return None


floor_plan_query_service = FloorPlanQueryService()
