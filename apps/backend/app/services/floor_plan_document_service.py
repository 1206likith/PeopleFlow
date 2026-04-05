"""
Shared floor-plan document helpers used by read, mutation, and runtime paths.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from app.core.config import settings
from app.services.floor_plan_repository import get_floor_plan_repository
from app.services.floorplan_quality import (
    build_floor_plan_quality_report as canonical_build_floor_plan_quality_report,
    build_runtime_geometry_status as canonical_build_runtime_geometry_status,
    count_usable_exits as canonical_count_usable_exits,
    is_floor_plan_ready_for_runtime as canonical_is_floor_plan_ready_for_runtime,
)


def _as_float(value: Any) -> Optional[float]:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed == parsed else None


def _bbox_from_points(points: Any) -> Optional[tuple[float, float, float, float]]:
    if not isinstance(points, list) or not points:
        return None

    xs: List[float] = []
    ys: List[float] = []
    for point in points:
        if isinstance(point, dict):
            px = _as_float(point.get("x"))
            py = _as_float(point.get("y"))
        elif isinstance(point, (list, tuple)) and len(point) >= 2:
            px = _as_float(point[0])
            py = _as_float(point[1])
        else:
            continue
        if px is None or py is None:
            continue
        xs.append(px)
        ys.append(py)

    if not xs or not ys:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def normalize_detected_obstacles(obstacles: Optional[List[Any]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []

    for index, obstacle in enumerate(obstacles or []):
        if not isinstance(obstacle, dict):
            continue

        bbox_coords: Optional[tuple[float, float, float, float]] = None
        bbox = obstacle.get("bbox")
        if isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
            x1 = _as_float(bbox[0])
            y1 = _as_float(bbox[1])
            x2 = _as_float(bbox[2])
            y2 = _as_float(bbox[3])
            if None not in (x1, y1, x2, y2):
                bbox_coords = (float(x1), float(y1), float(x2), float(y2))

        if bbox_coords is None:
            x1 = _as_float(obstacle.get("x1"))
            y1 = _as_float(obstacle.get("y1"))
            x2 = _as_float(obstacle.get("x2"))
            y2 = _as_float(obstacle.get("y2"))
            if None not in (x1, y1, x2, y2):
                bbox_coords = (float(x1), float(y1), float(x2), float(y2))

        if bbox_coords is None:
            left = _as_float(obstacle.get("left"))
            top = _as_float(obstacle.get("top"))
            right = _as_float(obstacle.get("right"))
            bottom = _as_float(obstacle.get("bottom"))
            if None not in (left, top, right, bottom):
                bbox_coords = (float(left), float(top), float(right), float(bottom))

        if bbox_coords is None:
            bbox_coords = _bbox_from_points(obstacle.get("points"))

        center = obstacle.get("center")
        center_x = None
        center_z = None
        if isinstance(center, (list, tuple)) and len(center) >= 2:
            center_x = _as_float(center[0])
            center_z = _as_float(center[1])

        width = _as_float(obstacle.get("width"))
        height = _as_float(obstacle.get("height"))
        depth = _as_float(obstacle.get("depth"))
        radius = _as_float(obstacle.get("radius"))

        if bbox_coords is not None:
            x1, y1, x2, y2 = bbox_coords
            bbox_width = abs(x2 - x1)
            bbox_height = abs(y2 - y1)
            center_x = center_x if center_x is not None else (x1 + x2) / 2
            center_z = center_z if center_z is not None else (y1 + y2) / 2
            width = width if width is not None and width > 0 else bbox_width
            height = height if height is not None and height > 0 else bbox_height
            depth = depth if depth is not None and depth > 0 else bbox_height

        raw_x = _as_float(obstacle.get("x"))
        raw_y = _as_float(obstacle.get("y"))
        raw_z = _as_float(obstacle.get("z"))

        if center_x is None:
            center_x = raw_x

        if center_z is None:
            if raw_y is not None and (raw_z is None or (raw_z == 0.0 and raw_y != 0.0)):
                center_z = raw_y
            else:
                center_z = raw_z if raw_z is not None else raw_y

        if radius is not None and radius > 0:
            diameter = radius * 2.0
            width = width if width is not None and width > 0 else diameter
            height = height if height is not None and height > 0 else diameter
            depth = depth if depth is not None and depth > 0 else diameter

        if center_x is None or center_z is None:
            continue

        width = width if width is not None and width > 0 else 1.0
        height = height if height is not None and height > 0 else width
        depth = depth if depth is not None and depth > 0 else height

        normalized.append(
            {
                **obstacle,
                "id": obstacle.get("id", f"obstacle_{index + 1}"),
                "x": float(center_x),
                "y": 0.0,
                "z": float(center_z),
                "width": float(width),
                "height": float(height),
                "depth": float(depth),
                "type": obstacle.get("type", obstacle.get("classification", "obstacle")),
            }
        )

    return normalized


def normalize_removed_detected_exit_ids(values: Optional[List[Any]]) -> List[str]:
    normalized: List[str] = []
    seen = set()
    for value in values or []:
        exit_id = str(value or "").strip()
        if not exit_id or exit_id in seen:
            continue
        seen.add(exit_id)
        normalized.append(exit_id)
    return normalized


def filter_removed_detected_exits(
    detected_exits: Optional[List[Dict[str, Any]]],
    removed_exit_ids: Optional[List[Any]],
) -> List[Dict[str, Any]]:
    removed = set(normalize_removed_detected_exit_ids(removed_exit_ids))
    if not removed:
        return list(detected_exits or [])
    return [
        exit_item
        for exit_item in (detected_exits or [])
        if str((exit_item or {}).get("id") or "").strip() not in removed
    ]


def extract_detected_elements(doc: dict) -> dict:
    if not doc:
        return {}
    metadata = doc.get("processing_metadata", {}) or {}
    walls = doc.get("detected_walls", []) or []
    exits = doc.get("detected_exits", []) or []
    obstacles = normalize_detected_obstacles(doc.get("detected_obstacles", []) or [])
    rooms = doc.get("rooms", []) or []
    corridors = doc.get("corridors", []) or []
    open_spaces = doc.get("open_spaces", []) or []
    doors = doc.get("doors", []) or []
    return {
        "processed": bool(metadata.get("processed", False)),
        "walls": walls,
        "exits": exits,
        "obstacles": obstacles,
        "boundaries": doc.get("boundaries", []) or [],
        "boundary_polygon": doc.get("boundary_polygon", []) or [],
        "boundary_area": doc.get("boundary_area"),
        "rooms": rooms,
        "corridors": corridors,
        "open_spaces": open_spaces,
        "doors": doors,
        "building_bounds": doc.get("building_bounds", {}) or {},
        "image_dimensions": doc.get("image_dimensions", {}) or {},
        "quality": doc.get("quality", {}) or {},
        "pipeline": doc.get("pipeline", metadata.get("pipeline", "cached")),
        "processing_time_ms": doc.get("processing_time_ms"),
        "pipeline_steps": doc.get("pipeline_steps", []) or [{"name": "cache_hit", "duration_ms": 0}],
        "detector_mode": doc.get("detector_mode", metadata.get("detector_mode")),
        "detector_health": doc.get("detector_health", metadata.get("detector_health")),
        "fallback_reason": doc.get("fallback_reason", metadata.get("fallback_reason")),
        "quality_report": doc.get("quality_report", metadata.get("quality_report", {})),
        "model_bundle_version": doc.get("model_bundle_version", metadata.get("model_bundle_version")),
        "simulation_ready": (
            doc.get("simulation_ready")
            if doc.get("simulation_ready") is not None
            else metadata.get("simulation_ready")
        ),
        "wall_count": metadata.get("wall_count", len(walls)),
        "exit_count": metadata.get("exit_count", len(exits)),
        "obstacle_count": metadata.get("obstacle_count", len(obstacles)),
        "room_count": metadata.get("room_count", len(rooms)),
        "corridor_count": metadata.get("corridor_count", len(corridors)),
        "open_space_count": metadata.get("open_space_count", len(open_spaces)),
        "door_count": metadata.get("door_count", len(doors)),
    }


def is_usable_detected_elements(detected: Optional[dict], is_image_upload: bool) -> bool:
    if not detected:
        return False
    if not is_image_upload:
        return True
    pipeline = str(detected.get("pipeline", "") or "").strip().lower()
    processed = bool(detected.get("processed", False))
    wall_count = int(detected.get("wall_count", len(detected.get("walls", []) or [])) or 0)
    room_count = int(detected.get("room_count", len(detected.get("rooms", []) or [])) or 0)
    exit_count = int(detected.get("exit_count", len(detected.get("exits", []) or [])) or 0)

    if pipeline in {"none", "mock-fallback"}:
        return False
    if not processed:
        return False
    if wall_count <= 0 and room_count <= 0 and exit_count <= 0:
        return False
    return True


def normalize_processing_options(raw_options: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    options = dict(raw_options or {})
    mode = str(options.get("mode") or "").strip().lower()
    if mode not in {"auto", "traditional", "semantic"}:
        if "use_semantic" in options:
            mode = "semantic" if bool(options.get("use_semantic")) else "traditional"
        else:
            mode = "auto"
    options["mode"] = mode
    options["use_semantic"] = mode == "semantic"
    return options


def count_usable_exits(exits: List[Dict[str, Any]]) -> int:
    return canonical_count_usable_exits(exits)


def build_floor_plan_quality_report(
    floor_plan_doc: Optional[Dict[str, Any]],
    floor_plan_data: Optional[Dict[str, Any]],
    exits: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    return canonical_build_floor_plan_quality_report(floor_plan_doc, floor_plan_data, exits)


def is_floor_plan_ready_for_runtime(quality_report: Dict[str, Any]) -> bool:
    return canonical_is_floor_plan_ready_for_runtime(quality_report)


def build_runtime_geometry_status(
    floor_plan_data: Optional[Dict[str, Any]],
    exits: Optional[List[Dict[str, Any]]],
) -> Dict[str, Any]:
    return canonical_build_runtime_geometry_status(floor_plan_data, exits)


def floor_plan_etag(
    floor_plan_id: str,
    floor_number: Optional[int],
    revision: int,
    suffix: str,
) -> str:
    floor_key = floor_number if floor_number is not None else "all"
    return f'W/"{floor_plan_id}:{floor_key}:{revision}:{suffix}"'


def _default_mock_bounds() -> Dict[str, float]:
    return {
        "min_x": 0.0,
        "min_y": 0.0,
        "max_x": 100.0,
        "max_y": 100.0,
        "width": 100.0,
        "height": 100.0,
    }


def _build_mock_floor_plan_doc(floor_plan_id: str, user_id: str) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    bounds = _default_mock_bounds()
    boundary_polygon = [
        {"x": bounds["min_x"], "y": bounds["min_y"]},
        {"x": bounds["max_x"], "y": bounds["min_y"]},
        {"x": bounds["max_x"], "y": bounds["max_y"]},
        {"x": bounds["min_x"], "y": bounds["max_y"]},
    ]
    boundary_segments = [
        {"id": "mock-wall-top", "x1": bounds["min_x"], "y1": bounds["min_y"], "x2": bounds["max_x"], "y2": bounds["min_y"]},
        {"id": "mock-wall-right", "x1": bounds["max_x"], "y1": bounds["min_y"], "x2": bounds["max_x"], "y2": bounds["max_y"]},
        {"id": "mock-wall-bottom", "x1": bounds["max_x"], "y1": bounds["max_y"], "x2": bounds["min_x"], "y2": bounds["max_y"]},
        {"id": "mock-wall-left", "x1": bounds["min_x"], "y1": bounds["max_y"], "x2": bounds["min_x"], "y2": bounds["min_y"]},
    ]
    detected_exits = [
        {"id": "mock-exit-left", "name": "Left Exit", "x": bounds["min_x"] + 2, "y": bounds["height"] / 2, "z": bounds["height"] / 2, "width": 2.0, "capacity": 80},
        {"id": "mock-exit-right", "name": "Right Exit", "x": bounds["max_x"] - 2, "y": bounds["height"] / 2, "z": bounds["height"] / 2, "width": 2.0, "capacity": 80},
    ]
    processing_metadata = {
        "processed": False,
        "wall_count": len(boundary_segments),
        "exit_count": len(detected_exits),
        "obstacle_count": 0,
        "room_count": 0,
        "corridor_count": 0,
        "open_space_count": 0,
        "door_count": 0,
        "image_dimensions": {"width": 100.0, "height": 100.0},
        "building_bounds": bounds,
        "boundary_polygon": boundary_polygon,
        "quality": {},
        "pipeline": "mock-fallback",
        "processing_time_ms": None,
        "pipeline_steps": [],
        "detector_mode": "auto",
        "detector_health": "poor",
        "fallback_reason": "mock_fallback",
        "quality_report": {},
        "model_bundle_version": "mock",
        "simulation_ready": False,
    }
    return {
        "_id": floor_plan_id,
        "id": floor_plan_id,
        "tenant_id": "global",
        "user_id": user_id,
        "building_name": "Mock Floor Plan",
        "floors": [{"floorNumber": 1, "name": "Floor 1", "exits": []}],
        "file_path": None,
        "file_size": 0,
        "content_type": "application/octet-stream",
        "file_hash": None,
        "detected_walls": boundary_segments,
        "detected_exits": detected_exits,
        "removed_detected_exit_ids": [],
        "manual_exits": [],
        "detected_obstacles": [],
        "boundaries": boundary_segments,
        "boundary_polygon": boundary_polygon,
        "boundary_area": bounds["width"] * bounds["height"],
        "rooms": [],
        "corridors": [],
        "open_spaces": [],
        "doors": [],
        "building_bounds": bounds,
        "image_dimensions": {"width": 100.0, "height": 100.0},
        "quality": {},
        "pipeline": "mock-fallback",
        "processing_time_ms": None,
        "pipeline_steps": [],
        "processing_options": normalize_processing_options({}),
        "detector_mode": "auto",
        "detector_health": "poor",
        "fallback_reason": "mock_fallback",
        "quality_report": {},
        "model_bundle_version": "mock",
        "simulation_ready": False,
        "processing_metadata": processing_metadata,
        "manual_exit_events": [],
        "revision": 1,
        "created_at": now,
        "updated_at": now,
    }


def _ensure_mock_floor_plan_doc(floor_plan_id: str, user_id: str) -> Dict[str, Any]:
    from app.services.floorplan_store import get_floor_plan, save_floor_plan

    existing = get_floor_plan(floor_plan_id)
    if existing:
        return existing
    seeded = _build_mock_floor_plan_doc(floor_plan_id, user_id)
    save_floor_plan(floor_plan_id, seeded)
    return seeded


async def fetch_floor_plan_doc(floor_plan_id: str, user_id: str) -> Optional[dict]:
    from app.services.floorplan_store import get_floor_plan

    if not floor_plan_id:
        return None
    if floor_plan_id.startswith("mock-"):
        if not settings.IS_DEMO_MODE:
            return None
        return _ensure_mock_floor_plan_doc(floor_plan_id, user_id)

    try:
        repository = await get_floor_plan_repository()
        doc = await repository.get(floor_plan_id)
        if doc:
            return doc
    except Exception:
        if not settings.IS_DEMO_MODE:
            raise HTTPException(status_code=503, detail="Database unavailable")

    doc = get_floor_plan(floor_plan_id)
    if doc:
        return doc
    if floor_plan_id.startswith("mock-"):
        if not settings.IS_DEMO_MODE:
            return None
        return _ensure_mock_floor_plan_doc(floor_plan_id, user_id)
    return None


async def persist_floor_plan_updates(floor_plan_id: str, user_id: str, updates: dict) -> None:
    from app.services.floorplan_loader import invalidate_floorplan_cache
    from app.services.floorplan_store import update_floor_plan

    if floor_plan_id.startswith("mock-"):
        if not settings.IS_DEMO_MODE:
            raise HTTPException(status_code=422, detail="Mock floor plans are not writable in production mode")
        repository = await get_floor_plan_repository()
        if not await repository.get(floor_plan_id):
            seeded = await fetch_floor_plan_doc(floor_plan_id, user_id)
            if seeded:
                await repository.update_fields(floor_plan_id, seeded, upsert=True)
        await repository.update_fields(floor_plan_id, updates, upsert=True)
        invalidate_floorplan_cache(floor_plan_id)
        return

    try:
        repository = await get_floor_plan_repository()
        updated = await repository.update_fields(floor_plan_id, updates, upsert=settings.IS_DEMO_MODE)
        if not updated:
            update_floor_plan(floor_plan_id, updates)
    except Exception:
        if not settings.IS_DEMO_MODE:
            raise HTTPException(status_code=503, detail="Database unavailable")
        update_floor_plan(floor_plan_id, updates)
    finally:
        invalidate_floorplan_cache(floor_plan_id)
