"""
Application service for floor-plan mutation workflows.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
import os
import uuid

from fastapi import HTTPException

from app.core.config import settings
from app.services.audit_log import record_event
from app.services.floor_plan_document_service import (
    build_floor_plan_quality_report,
    filter_removed_detected_exits,
    fetch_floor_plan_doc,
    normalize_removed_detected_exit_ids,
    normalize_processing_options,
    persist_floor_plan_updates,
)


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


class FloorPlanMutationService:
    @staticmethod
    def _user_id(current_user: dict) -> str:
        return str(current_user.get("_id", current_user.get("id", "demo_user")))

    async def reprocess(self, floor_plan_id: str, payload: Any, *, current_user: dict) -> Dict[str, Any]:
        user_id = self._user_id(current_user)
        floor_plan_doc = await fetch_floor_plan_doc(floor_plan_id, user_id)
        if not floor_plan_doc:
            raise HTTPException(status_code=404, detail="Floor plan not found")
        if not settings.IS_DEMO_MODE and floor_plan_id.startswith("mock-"):
            raise HTTPException(status_code=422, detail="Mock floor plans are not allowed in production")

        file_path = floor_plan_doc.get("file_path")
        if not file_path:
            raise HTTPException(status_code=400, detail="Floor plan has no source file for reprocessing")
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Source file not found for reprocessing")

        existing_options = normalize_processing_options(floor_plan_doc.get("processing_options", {}))
        merged_options = normalize_processing_options(
            {
                **existing_options,
                "mode": payload.mode,
                "debug": payload.debug,
                "profile": payload.profile,
            }
        )

        from app.services.floorplan_service import process_floor_plan_image

        detected = process_floor_plan_image(
            floor_plan_doc.get("content_type", "application/octet-stream"),
            file_path,
            merged_options,
        )
        quality_report = detected.get("quality_report") or build_floor_plan_quality_report(
            None,
            detected,
            detected.get("exits", []),
        )
        revision = int(floor_plan_doc.get("revision", 0)) + 1
        updates = {
            "detected_walls": detected.get("walls", []),
            "detected_exits": detected.get("exits", []),
            "detected_obstacles": detected.get("obstacles", []),
            "boundaries": detected.get("boundaries", []),
            "boundary_polygon": detected.get("boundary_polygon", []),
            "boundary_area": detected.get("boundary_area"),
            "rooms": detected.get("rooms", []),
            "corridors": detected.get("corridors", []),
            "open_spaces": detected.get("open_spaces", []),
            "doors": detected.get("doors", []),
            "building_bounds": detected.get("building_bounds", {}),
            "image_dimensions": detected.get("image_dimensions", {}),
            "quality": detected.get("quality", {}),
            "pipeline": detected.get("pipeline", "unknown"),
            "processing_time_ms": detected.get("processing_time_ms"),
            "pipeline_steps": detected.get("pipeline_steps", []),
            "processing_options": merged_options,
            "detector_mode": detected.get("detector_mode", merged_options.get("mode", "auto")),
            "detector_health": detected.get("detector_health", "poor"),
            "fallback_reason": detected.get("fallback_reason"),
            "quality_report": quality_report,
            "model_bundle_version": detected.get("model_bundle_version"),
            "simulation_ready": bool(detected.get("simulation_ready", quality_report.get("simulation_ready"))),
            "revision": revision,
            "updated_at": datetime.now(timezone.utc),
            "processing_metadata": {
                **floor_plan_doc.get("processing_metadata", {}),
                "processed": detected.get("processed", False),
                "wall_count": detected.get("wall_count", len(detected.get("walls", []) or [])),
                "exit_count": detected.get("exit_count", len(detected.get("exits", []) or [])),
                "obstacle_count": detected.get("obstacle_count", len(detected.get("obstacles", []) or [])),
                "room_count": detected.get("room_count", len(detected.get("rooms", []) or [])),
                "corridor_count": detected.get("corridor_count", len(detected.get("corridors", []) or [])),
                "open_space_count": detected.get("open_space_count", len(detected.get("open_spaces", []) or [])),
                "door_count": detected.get("door_count", len(detected.get("doors", []) or [])),
                "image_dimensions": detected.get("image_dimensions", {}),
                "building_bounds": detected.get("building_bounds", {}),
                "boundary_polygon": detected.get("boundary_polygon", []),
                "boundary_area": detected.get("boundary_area"),
                "quality": detected.get("quality", {}),
                "pipeline": detected.get("pipeline", "unknown"),
                "processing_time_ms": detected.get("processing_time_ms"),
                "pipeline_steps": detected.get("pipeline_steps", []),
                "detector_mode": detected.get("detector_mode", merged_options.get("mode", "auto")),
                "detector_health": detected.get("detector_health", "poor"),
                "fallback_reason": detected.get("fallback_reason"),
                "quality_report": quality_report,
                "model_bundle_version": detected.get("model_bundle_version"),
                "simulation_ready": bool(detected.get("simulation_ready", quality_report.get("simulation_ready"))),
            },
        }
        await persist_floor_plan_updates(floor_plan_id, user_id, updates)

        return {
            "floor_plan_id": floor_plan_id,
            "revision": revision,
            "pipeline": updates["pipeline"],
            "detector_mode": updates["detector_mode"],
            "detector_health": updates["detector_health"],
            "fallback_reason": updates.get("fallback_reason"),
            "quality_report": quality_report,
            "model_bundle_version": updates.get("model_bundle_version"),
            "simulation_ready": updates["simulation_ready"],
        }

    async def save_annotations(self, floor_plan_id: str, payload: Any, *, current_user: dict) -> Dict[str, Any]:
        user_id = self._user_id(current_user)
        floor_plan_doc = await fetch_floor_plan_doc(floor_plan_id, user_id)
        if not floor_plan_doc:
            raise HTTPException(status_code=404, detail="Floor plan not found")

        existing = floor_plan_doc.get("annotations") or {}
        next_annotations = {
            "status": payload.status or existing.get("status", "new"),
            "walls": payload.walls,
            "doors": payload.doors,
            "exits": payload.exits,
            "rooms": payload.rooms,
            "notes": payload.notes,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": user_id,
        }
        revision = int(floor_plan_doc.get("revision", 0)) + 1
        updates = {
            "annotations": next_annotations,
            "revision": revision,
            "updated_at": datetime.now(timezone.utc),
        }
        await persist_floor_plan_updates(floor_plan_id, user_id, updates)
        return {
            "floor_plan_id": floor_plan_id,
            "annotations": next_annotations,
            "revision": revision,
        }

    async def add_exits(
        self,
        floor_plan_id: str,
        payload: Any,
        *,
        floor_number: Optional[int],
        current_user: dict,
        merge: Optional[bool] = None,
    ) -> Dict[str, Any]:
        user_id = self._user_id(current_user)
        floor_plan_doc = await fetch_floor_plan_doc(floor_plan_id, user_id)
        if not floor_plan_doc:
            raise HTTPException(status_code=404, detail="Floor plan not found")

        should_merge = payload.merge if merge is None else merge
        raw_exits = []
        for idx, exit_item in enumerate(payload.exits, start=1):
            exit_dict = exit_item.model_dump() if hasattr(exit_item, "model_dump") else exit_item.dict()
            exit_dict["source"] = "manual"
            if floor_number is not None:
                exit_dict["floor_number"] = floor_number
            if not exit_dict.get("id"):
                exit_dict["id"] = f"manual-exit-{uuid.uuid4().hex[:8]}"
            if not exit_dict.get("name"):
                exit_dict["name"] = f"Manual Exit {idx}"
            raw_exits.append(exit_dict)

        bounds = floor_plan_doc.get("building_bounds") or floor_plan_doc.get("processing_metadata", {}).get("building_bounds")
        boundaries = floor_plan_doc.get("boundaries", [])

        from app.services.floorplan_loader import load_floor_plan_data, merge_exits, normalize_exits, snap_exits_to_boundaries

        if payload.snap_to_boundary:
            normalized = snap_exits_to_boundaries(raw_exits, boundaries, bounds)
        else:
            normalized = normalize_exits(raw_exits, bounds)

        existing_manual = floor_plan_doc.get("manual_exits", []) if should_merge else []
        merged_manual = merge_exits([existing_manual, normalized])
        revision = int(floor_plan_doc.get("revision", 0)) + 1
        manual_events = list(floor_plan_doc.get("manual_exit_events", []))
        manual_events.append(
            {
                "action": "add" if should_merge else "replace",
                "exit_ids": [e.get("id") for e in normalized],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "floor_number": floor_number,
            }
        )

        updates = {
            "manual_exits": merged_manual,
            "processing_metadata": {
                **floor_plan_doc.get("processing_metadata", {}),
                "manual_exit_count": len(merged_manual),
            },
            "manual_exit_events": manual_events,
            "revision": revision,
            "updated_at": datetime.now(timezone.utc),
        }
        await persist_floor_plan_updates(floor_plan_id, user_id, updates)

        _safe_audit(
            "floor_plan_exits_updated",
            actor=user_id,
            metadata={
                "floor_plan_id": floor_plan_id,
                "action": "add" if should_merge else "replace",
                "exit_ids": [e.get("id") for e in normalized],
                "floor_number": floor_number,
                "revision": revision,
            },
        )

        floor_plan_data, exits = await load_floor_plan_data(
            floor_plan_id,
            floor_number,
            configured_exits=None,
        )

        return {
            "floor_plan_id": floor_plan_id,
            "manual_exits": merged_manual,
            "exits": exits,
            "building_bounds": floor_plan_data.get("building_bounds") if floor_plan_data else None,
            "revision": revision,
        }

    async def delete_exit(
        self,
        floor_plan_id: str,
        exit_id: str,
        *,
        current_user: dict,
    ) -> Dict[str, Any]:
        user_id = self._user_id(current_user)
        floor_plan_doc = await fetch_floor_plan_doc(floor_plan_id, user_id)
        if not floor_plan_doc:
            raise HTTPException(status_code=404, detail="Floor plan not found")

        existing_manual = floor_plan_doc.get("manual_exits", [])
        filtered = [e for e in existing_manual if e.get("id") != exit_id]
        removed_detected_exit_ids = normalize_removed_detected_exit_ids(
            floor_plan_doc.get("removed_detected_exit_ids", []),
        )
        detected_exits = filter_removed_detected_exits(
            floor_plan_doc.get("detected_exits", []),
            removed_detected_exit_ids,
        )
        detected_exists = any(str(e.get("id")) == exit_id for e in detected_exits if isinstance(e, dict))
        if len(filtered) == len(existing_manual) and not detected_exists:
            raise HTTPException(status_code=404, detail="Exit not found")

        removed_detected = False
        if len(filtered) == len(existing_manual) and detected_exists:
            removed_detected = True
            removed_detected_exit_ids = normalize_removed_detected_exit_ids(
                [*removed_detected_exit_ids, exit_id],
            )

        revision = int(floor_plan_doc.get("revision", 0)) + 1
        manual_events = list(floor_plan_doc.get("manual_exit_events", []))
        manual_events.append(
            {
                "action": "delete_detected" if removed_detected else "delete",
                "exit_ids": [exit_id],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
            }
        )

        updates = {
            "manual_exits": filtered,
            "removed_detected_exit_ids": removed_detected_exit_ids,
            "processing_metadata": {
                **floor_plan_doc.get("processing_metadata", {}),
                "manual_exit_count": len(filtered),
            },
            "manual_exit_events": manual_events,
            "revision": revision,
            "updated_at": datetime.now(timezone.utc),
        }
        await persist_floor_plan_updates(floor_plan_id, user_id, updates)

        _safe_audit(
            "floor_plan_exit_deleted",
            actor=user_id,
            metadata={
                "floor_plan_id": floor_plan_id,
                "exit_id": exit_id,
                "exit_source": "detected" if removed_detected else "manual",
                "revision": revision,
            },
        )

        return {
            "floor_plan_id": floor_plan_id,
            "removed_exit_id": exit_id,
            "manual_exits": filtered,
            "removed_detected_exit_ids": removed_detected_exit_ids,
            "revision": revision,
        }


floor_plan_mutation_service = FloorPlanMutationService()
