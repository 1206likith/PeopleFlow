"""
Floor plan loader for simulations.
Resolves exits and processing metadata from stored floor plans.
"""

import logging
import time
from copy import deepcopy
from typing import Dict, List, Optional, Tuple

from bson import ObjectId
from bson.errors import InvalidId

from app.core.config import settings
from app.services.floor_plan_document_service import (
    filter_removed_detected_exits,
    normalize_detected_obstacles,
)
from app.services.floor_plan_repository import get_floor_plan_repository
from app.services.floorplan_quality import build_floor_plan_quality_report
from app.services.floorplan_store import get_floor_plan

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 30
CACHE_MAX_ENTRIES = 128
_FLOORPLAN_CACHE: Dict[Tuple[str, Optional[int]], Tuple[float, Optional[str], Dict, List[Dict]]] = {}


def _cache_get(cache_key: Tuple[str, Optional[int]], signature: Optional[str] = None):
    entry = _FLOORPLAN_CACHE.get(cache_key)
    if not entry:
        return None
    ts, cached_signature, data, exits = entry
    if time.time() - ts > CACHE_TTL_SECONDS:
        _FLOORPLAN_CACHE.pop(cache_key, None)
        return None
    if signature is not None and cached_signature is not None and signature != cached_signature:
        return None
    return deepcopy(data), deepcopy(exits)


def _cache_set(
    cache_key: Tuple[str, Optional[int]],
    data: Dict,
    exits: List[Dict],
    signature: Optional[str] = None,
):
    if len(_FLOORPLAN_CACHE) >= CACHE_MAX_ENTRIES:
        oldest_key = min(_FLOORPLAN_CACHE.items(), key=lambda item: item[1][0])[0]
        _FLOORPLAN_CACHE.pop(oldest_key, None)
    _FLOORPLAN_CACHE[cache_key] = (time.time(), signature, deepcopy(data), deepcopy(exits))


def invalidate_floorplan_cache(floor_plan_id: str) -> None:
    if not floor_plan_id:
        return
    for key in list(_FLOORPLAN_CACHE.keys()):
        if key[0] == floor_plan_id:
            _FLOORPLAN_CACHE.pop(key, None)


def _signature_from_doc(doc: Optional[Dict]) -> Optional[str]:
    if not doc:
        return None
    revision = doc.get("revision")
    if revision is not None:
        return f"rev:{revision}"
    file_hash = doc.get("file_hash")
    if file_hash:
        return f"hash:{file_hash}"
    return None


def _is_valid_objectid(value: Optional[str]) -> bool:
    if not value:
        return False
    if value.startswith("mock") or value.startswith("mock-"):
        return False
    try:
        ObjectId(value)
        return True
    except (InvalidId, ValueError, TypeError):
        return False


def _infer_exits_from_bounds(bounds: Dict) -> List[Dict]:
    if not bounds:
        return []
    min_x = bounds.get("min_x", 0)
    max_x = bounds.get("max_x", 100)
    min_y = bounds.get("min_y", 0)
    max_y = bounds.get("max_y", 100)
    width = max_x - min_x
    height = max_y - min_y
    mid_x = min_x + width / 2
    mid_y = min_y + height / 2

    exits = []
    if width >= height:
        exits = [
            {
                "id": "exit_left",
                "name": "Left Exit",
                "x": min_x + 2,
                "y": mid_y,
                "z": mid_y,
                "width": 2.0,
                "height": 2.0,
                "capacity": 80,
                "is_emergency": True,
                "source": "inferred_bounds",
            },
            {
                "id": "exit_right",
                "name": "Right Exit",
                "x": max_x - 2,
                "y": mid_y,
                "z": mid_y,
                "width": 2.0,
                "height": 2.0,
                "capacity": 80,
                "is_emergency": True,
                "source": "inferred_bounds",
            },
        ]
    else:
        exits = [
            {
                "id": "exit_top",
                "name": "Top Exit",
                "x": mid_x,
                "y": min_y + 2,
                "z": min_y + 2,
                "width": 2.0,
                "height": 2.0,
                "capacity": 80,
                "is_emergency": True,
                "source": "inferred_bounds",
            },
            {
                "id": "exit_bottom",
                "name": "Bottom Exit",
                "x": mid_x,
                "y": max_y - 2,
                "z": max_y - 2,
                "width": 2.0,
                "height": 2.0,
                "capacity": 80,
                "is_emergency": True,
                "source": "inferred_bounds",
            },
        ]
    return exits


def _project_point_to_segment(
    x: float,
    y: float,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
) -> Tuple[float, float, float]:
    A = x - x1
    B = y - y1
    C = x2 - x1
    D = y2 - y1
    len_sq = C * C + D * D
    if len_sq == 0:
        return x1, y1, (A * A + B * B) ** 0.5
    t = (A * C + B * D) / len_sq
    if t < 0:
        px, py = x1, y1
    elif t > 1:
        px, py = x2, y2
    else:
        px, py = x1 + t * C, y1 + t * D
    dx = x - px
    dy = y - py
    return px, py, (dx * dx + dy * dy) ** 0.5


def _boundary_centroid(boundaries: List[Dict]) -> Optional[Tuple[float, float]]:
    if not boundaries:
        return None
    points = []
    for b in boundaries:
        points.append((float(b.get("x1", 0.0)), float(b.get("y1", 0.0))))
        points.append((float(b.get("x2", 0.0)), float(b.get("y2", 0.0))))
    if not points:
        return None
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return (sum(xs) / len(xs), sum(ys) / len(ys))


def _normalize_exits(exits: List[Dict], bounds: Optional[Dict] = None) -> List[Dict]:
    normalized = []
    for i, exit_data in enumerate(exits or []):
        if not isinstance(exit_data, dict):
            continue
        x = exit_data.get("x", 0.0)
        y = exit_data.get("y", 0.0)
        z = exit_data.get("z")
        try:
            if z is None or (float(z) == 0.0 and float(y) != 0.0):
                z = y
        except (TypeError, ValueError):
            z = y
        if z is None:
            z = y
        width = exit_data.get("width", exit_data.get("height", 20.0))
        height = exit_data.get("height")
        if height is None:
            height = width
        capacity = exit_data.get("capacity")
        if capacity is None:
            capacity = max(1, int(width * 5))

        if bounds:
            min_x = bounds.get("min_x", 0)
            max_x = bounds.get("max_x", 100)
            min_y = bounds.get("min_y", 0)
            max_y = bounds.get("max_y", 100)
            x = max(min_x + 1, min(max_x - 1, x))
            z = max(min_y + 1, min(max_y - 1, z))

        normalized.append(
            {
                "id": exit_data.get("id", f"exit_{i+1}"),
                "name": exit_data.get("name", f"Main Exit {i+1}"),
                "x": float(x),
                "y": float(y),
                "z": float(z),
                "width": float(width),
                "height": float(height),
                "capacity": int(capacity),
                "is_emergency": exit_data.get("is_emergency", True),
                "is_accessible": exit_data.get("is_accessible", True),
                "source": exit_data.get("source"),
                "floor_number": exit_data.get("floor_number") or exit_data.get("floorNumber"),
            }
        )
    return normalized


def normalize_exits(exits: List[Dict], bounds: Optional[Dict] = None) -> List[Dict]:
    return _normalize_exits(exits, bounds)


def merge_exits(exit_groups: List[List[Dict]]) -> List[Dict]:
    merged: List[Dict] = []
    seen_ids = set()
    seen_positions = set()

    for group in exit_groups:
        for exit_data in group or []:
            if not isinstance(exit_data, dict):
                continue
            exit_id = exit_data.get("id")
            floor_key = exit_data.get("floor_number") or exit_data.get("floorNumber")
            x = float(exit_data.get("x", 0.0))
            z = float(exit_data.get("z", exit_data.get("y", 0.0)))
            pos_key = (round(x, 1), round(z, 1), floor_key)
            id_key = (exit_id, floor_key) if exit_id else None

            if id_key and id_key in seen_ids:
                continue
            if id_key:
                seen_ids.add(id_key)
            if pos_key in seen_positions:
                continue
            seen_positions.add(pos_key)
            merged.append(exit_data)

    return merged


def snap_exits_to_boundaries(
    exits: List[Dict],
    boundaries: List[Dict],
    bounds: Optional[Dict] = None,
    max_snap_distance: float = 12.0,
    inset: float = 1.0,
) -> List[Dict]:
    if not exits:
        return exits
    if not boundaries:
        return _normalize_exits(exits, bounds)

    centroid = _boundary_centroid(boundaries)
    snapped = []
    for exit_data in exits:
        if not isinstance(exit_data, dict):
            continue
        x = float(exit_data.get("x", 0.0))
        z = float(exit_data.get("z", exit_data.get("y", 0.0)))
        best_point = None
        best_dist = None
        for b in boundaries:
            px, py, dist = _project_point_to_segment(
                x, z,
                float(b.get("x1", 0.0)),
                float(b.get("y1", 0.0)),
                float(b.get("x2", 0.0)),
                float(b.get("y2", 0.0)),
            )
            if best_dist is None or dist < best_dist:
                best_dist = dist
                best_point = (px, py)

        if best_point and best_dist is not None and best_dist <= max_snap_distance:
            nx, nz = best_point
            if centroid:
                cx, cz = centroid
                dx = cx - nx
                dz = cz - nz
                mag = (dx * dx + dz * dz) ** 0.5
                if mag > 1e-6:
                    nx += (dx / mag) * inset
                    nz += (dz / mag) * inset
            exit_data = dict(exit_data)
            exit_data["x"] = nx
            exit_data["z"] = nz
        snapped.append(exit_data)

    return _normalize_exits(snapped, bounds)


async def load_floor_plan_data(
    floor_plan_id: Optional[str],
    floor_number: Optional[int],
    configured_exits: Optional[List[Dict]],
    allow_inferred_exits: Optional[bool] = None,
) -> Tuple[Optional[Dict], List[Dict]]:
    exits = configured_exits or []
    infer_exits = settings.IS_DEMO_MODE if allow_inferred_exits is None else bool(allow_inferred_exits)
    floor_plan_data = None
    cache_key: Optional[Tuple[str, Optional[int]]] = None
    if floor_plan_id:
        cache_key = (floor_plan_id, floor_number)
        cached = _cache_get(cache_key)
        if cached:
            return cached

    def _filter_exits_by_floor(exits_list: List[Dict]) -> List[Dict]:
        if not exits_list:
            return []
        if floor_number is None:
            return exits_list
        filtered = []
        for exit_item in exits_list:
            if not isinstance(exit_item, dict):
                continue
            exit_floor = exit_item.get("floor_number") or exit_item.get("floorNumber")
            if exit_floor is None or exit_floor == floor_number:
                filtered.append(exit_item)
        return filtered

    def _build_floor_plan_payload(floor_plan_doc: Dict) -> Tuple[Optional[Dict], List[Dict]]:
        nonlocal exits
        if not floor_plan_doc:
            return None, exits

        detected_walls = floor_plan_doc.get("detected_walls", [])
        detected_exits = filter_removed_detected_exits(
            floor_plan_doc.get("detected_exits", []),
            floor_plan_doc.get("removed_detected_exit_ids", []),
        )
        manual_exits = floor_plan_doc.get("manual_exits", [])
        detected_obstacles = normalize_detected_obstacles(floor_plan_doc.get("detected_obstacles", []))
        boundaries = floor_plan_doc.get("boundaries", [])
        boundary_polygon = floor_plan_doc.get("boundary_polygon") or floor_plan_doc.get("processing_metadata", {}).get("boundary_polygon", [])

        floors = floor_plan_doc.get("floors", [])
        selected_floor = next(
            (f for f in floors if f.get("floorNumber") == (floor_number or 1)),
            floors[0] if floors else None,
        )
        floor_exits = selected_floor.get("exits", []) if selected_floor else []

        configured_filtered = _filter_exits_by_floor(configured_exits or [])
        manual_filtered = _filter_exits_by_floor(manual_exits or [])
        detected_filtered = _filter_exits_by_floor(detected_exits or [])
        floor_filtered = _filter_exits_by_floor(floor_exits or [])

        # Merge exits in precedence order: configured > manual > detected > floor config
        exit_groups = []
        if configured_filtered:
            for exit_item in configured_filtered:
                if isinstance(exit_item, dict):
                    exit_item.setdefault("source", "configured")
            exit_groups.append(configured_filtered)
        if manual_filtered:
            for exit_item in manual_filtered:
                if isinstance(exit_item, dict):
                    exit_item.setdefault("source", "manual")
            exit_groups.append(manual_filtered)
        if detected_filtered:
            for exit_item in detected_filtered:
                if isinstance(exit_item, dict):
                    exit_item.setdefault("source", "detected")
            exit_groups.append(detected_filtered)
        if floor_filtered:
            for exit_item in floor_filtered:
                if isinstance(exit_item, dict):
                    exit_item.setdefault("source", "floor_config")
            exit_groups.append(floor_filtered)

        exits = merge_exits(exit_groups)

        processing_metadata = floor_plan_doc.get("processing_metadata", {})
        pipeline_steps = (
            floor_plan_doc.get("pipeline_steps")
            or processing_metadata.get("pipeline_steps")
            or []
        )
        building_bounds = (
            floor_plan_doc.get("building_bounds")
            or processing_metadata.get("building_bounds")
        )
        image_dimensions = (
            floor_plan_doc.get("image_dimensions")
            or processing_metadata.get("image_dimensions")
            or {}
        )

        floor_plan_data_local = {
            "detected_walls": detected_walls,
            "detected_exits": detected_exits,
            "manual_exits": manual_exits,
            "detected_obstacles": detected_obstacles,
            "boundaries": boundaries,
            "boundary_polygon": boundary_polygon,
            "processing_metadata": processing_metadata,
            "file_path": floor_plan_doc.get("file_path"),
            "exits": exits,
            "image_dimensions": image_dimensions,
            "rooms": floor_plan_doc.get("rooms") or processing_metadata.get("rooms", []),
            "corridors": floor_plan_doc.get("corridors") or processing_metadata.get("corridors", []),
            "open_spaces": floor_plan_doc.get("open_spaces") or processing_metadata.get("open_spaces", []),
            "doors": floor_plan_doc.get("doors") or processing_metadata.get("doors", []),
            "quality": floor_plan_doc.get("quality") or processing_metadata.get("quality", {}),
            "pipeline": floor_plan_doc.get("pipeline") or processing_metadata.get("pipeline"),
            "processing_time_ms": floor_plan_doc.get("processing_time_ms") or processing_metadata.get("processing_time_ms"),
            "pipeline_steps": pipeline_steps,
            "revision": floor_plan_doc.get("revision"),
            "file_hash": floor_plan_doc.get("file_hash"),
            "processing_options": floor_plan_doc.get("processing_options", {}),
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
        }

        if building_bounds:
            floor_plan_data_local["building_bounds"] = building_bounds
        elif image_dimensions:
            floor_plan_data_local["building_bounds"] = {
                "min_x": 0,
                "min_y": 0,
                "max_x": image_dimensions.get("width", 100),
                "max_y": image_dimensions.get("height", 100),
                "width": image_dimensions.get("width", 100),
                "height": image_dimensions.get("height", 100),
            }

        # Normalize exits with bounds if available
        if floor_plan_data_local.get("building_bounds"):
            exits = normalize_exits(exits, floor_plan_data_local["building_bounds"])
        if not exits and infer_exits and floor_plan_data_local.get("building_bounds"):
            exits = _infer_exits_from_bounds(floor_plan_data_local["building_bounds"])
        floor_plan_data_local["exits"] = exits
        quality_report = floor_plan_data_local.get("quality_report") or build_floor_plan_quality_report(
            floor_plan_doc,
            floor_plan_data_local,
            exits,
        )
        floor_plan_data_local["quality_report"] = quality_report
        floor_plan_data_local["simulation_ready"] = bool(
            floor_plan_data_local.get("simulation_ready", quality_report.get("simulation_ready"))
        )

        logger.info(
            "Loaded floor plan data: %s walls, %s detected exits, %s final exits",
            len(detected_walls),
            len(detected_exits),
            len(exits),
        )

        if cache_key:
            signature = _signature_from_doc(floor_plan_doc)
            _cache_set(cache_key, floor_plan_data_local, exits, signature)
        return floor_plan_data_local, exits

    if not _is_valid_objectid(floor_plan_id):
        if floor_plan_id:
            logger.warning("Invalid floor_plan_id format: %s, treating as mock ID", floor_plan_id)
            floor_plan_doc = get_floor_plan(floor_plan_id)
            if floor_plan_doc:
                return _build_floor_plan_payload(floor_plan_doc)
        return floor_plan_data, exits

    try:
        repository = await get_floor_plan_repository()
        floor_plan_doc = await repository.get(floor_plan_id)
        if not floor_plan_doc:
            return floor_plan_data, exits

        return _build_floor_plan_payload(floor_plan_doc)

    except Exception as e:
        logger.warning("Could not load floor plan data: %s", e, exc_info=True)
        return floor_plan_data, exits
