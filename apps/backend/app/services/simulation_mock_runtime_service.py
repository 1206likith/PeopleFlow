from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form, Request, Response
from pydantic import ValidationError
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta, timezone
import aiofiles
import os
import logging
import json
import uuid
import time
import math
import hashlib
from bson import ObjectId
from app.api.contracts.simulation_contracts import SimulationResponse
from app.core.config import settings
from app.core.database import get_database
from app.core.request_context import get_request_actor
from app.core.validation import (
    SimulationConfigSchema,
    FloorSchema,
)
from app.core.metrics import (
    simulations_started_total,
    file_uploads_total,
    file_upload_size_bytes
)
from app.services.audit_log import record_event
from app.services.frame_ingest import ingest_frame
from app.services.floor_plan_document_service import (
    build_floor_plan_quality_report as _build_floor_plan_quality_report,
    build_runtime_geometry_status as _runtime_geometry_status,
    count_usable_exits as _count_usable_exits,
    extract_detected_elements as _extract_detected_elements,
    fetch_floor_plan_doc as _fetch_floor_plan_doc,
    floor_plan_etag as _floor_plan_etag,
    is_floor_plan_ready_for_runtime as _is_floor_plan_ready_for_runtime,
    is_usable_detected_elements as _is_usable_detected_elements,
    normalize_processing_options as _normalize_processing_options,
    persist_floor_plan_updates as _persist_floor_plan_updates,
)
from app.services.idempotency import (
    build_idempotency_key,
    get_cached_response,
    store_response,
    build_replay_response,
)
from app.services.floorplan_cache import (
    make_cache_key as make_floorplan_cache_key,
    get_cached_processing as get_cached_floorplan_processing,
    store_cached_processing as store_cached_floorplan_processing,
)

logger = logging.getLogger(__name__)


def _safe_audit(action: str, actor: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None, severity: str = "info") -> None:
    try:
        record_event(action=action, actor=actor, metadata=metadata, severity=severity)
    except Exception:
        pass

MOCK_SIM_TTL_SECONDS = 6 * 3600
MOCK_SIM_MAX_ENTRIES = 2048
_MOCK_SIM_RUNTIME: Dict[str, Dict[str, Any]] = {}


def _is_demo_like_simulation_id(simulation_id: str) -> bool:
    if not settings.IS_DEMO_MODE:
        return False
    return simulation_id.startswith("mock-") or simulation_id.startswith("demo-")


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _mock_seed_for_id(simulation_id: str) -> int:
    digest = hashlib.sha256(simulation_id.encode("utf-8")).hexdigest()[:8]
    return int(digest, 16)


def _prune_mock_runtime() -> None:
    if not _MOCK_SIM_RUNTIME:
        return
    now = time.time()
    expired = [
        key
        for key, runtime in _MOCK_SIM_RUNTIME.items()
        if now - float(runtime.get("created_ts", now)) > MOCK_SIM_TTL_SECONDS
    ]
    for key in expired:
        _MOCK_SIM_RUNTIME.pop(key, None)
    if len(_MOCK_SIM_RUNTIME) <= MOCK_SIM_MAX_ENTRIES:
        return
    ordered = sorted(
        _MOCK_SIM_RUNTIME.items(),
        key=lambda item: float(item[1].get("created_ts", 0)),
    )
    for key, _ in ordered[: max(0, len(_MOCK_SIM_RUNTIME) - MOCK_SIM_MAX_ENTRIES)]:
        _MOCK_SIM_RUNTIME.pop(key, None)


def list_mock_runtime_entries() -> List[Tuple[str, Dict[str, Any]]]:
    _prune_mock_runtime()
    return list(_MOCK_SIM_RUNTIME.items())


def _register_mock_runtime(
    simulation_id: str,
    *,
    num_agents: int,
    emergency_type: str,
    floor_number: Optional[int],
    exits: List[Dict[str, Any]],
    floor_plan_data: Optional[Dict[str, Any]],
) -> None:
    if not simulation_id.startswith("mock-"):
        return
    bounds = (floor_plan_data or {}).get("building_bounds") or {}
    min_x = float(bounds.get("min_x", 0.0))
    max_x = float(bounds.get("max_x", 100.0))
    min_y = float(bounds.get("min_y", 0.0))
    max_y = float(bounds.get("max_y", 100.0))
    if max_x <= min_x:
        max_x = min_x + 100.0
    if max_y <= min_y:
        max_y = min_y + 100.0

    normalized_exits: List[Dict[str, Any]] = []
    for idx, exit_item in enumerate(exits or [], start=1):
        normalized_exits.append({
            "id": str(exit_item.get("id") or f"exit-{idx}"),
            "x": float(exit_item.get("x", min_x)),
            "y": float(exit_item.get("y", min_y)),
            "z": float(exit_item.get("z", exit_item.get("y", min_y))),
            "width": float(exit_item.get("width", 2.0)),
            "capacity": int(exit_item.get("capacity", 100)),
            "name": str(exit_item.get("name") or f"Exit {idx}"),
        })

    if not normalized_exits:
        normalized_exits = [
            {"id": "exit-left", "x": min_x + 2.0, "y": min_y + (max_y - min_y) * 0.5, "z": min_y + (max_y - min_y) * 0.5, "width": 2.0, "capacity": 100, "name": "Left Exit"},
            {"id": "exit-right", "x": max_x - 2.0, "y": min_y + (max_y - min_y) * 0.5, "z": min_y + (max_y - min_y) * 0.5, "width": 2.0, "capacity": 100, "name": "Right Exit"},
        ]

    walls = list((floor_plan_data or {}).get("detected_walls") or [])
    boundaries = list((floor_plan_data or {}).get("boundaries") or [])
    if not walls and boundaries:
        walls = boundaries
    obstacles = list((floor_plan_data or {}).get("detected_obstacles") or [])
    _MOCK_SIM_RUNTIME[simulation_id] = {
        "simulation_id": simulation_id,
        "created_ts": time.time(),
        "num_agents": int(max(1, num_agents)),
        "emergency_type": str(emergency_type or "fire"),
        "floor_number": int(floor_number or 1),
        "bounds": {
            "min_x": min_x,
            "max_x": max_x,
            "min_y": min_y,
            "max_y": max_y,
        },
        "duration_seconds": 120.0,
        "exits": normalized_exits,
        "walls": walls,
        "obstacles": obstacles,
    }
    _prune_mock_runtime()


def _get_mock_runtime(simulation_id: str) -> Dict[str, Any]:
    _prune_mock_runtime()
    runtime = _MOCK_SIM_RUNTIME.get(simulation_id)
    if runtime:
        return runtime

    seed = _mock_seed_for_id(simulation_id)
    min_x = 0.0
    min_y = 0.0
    max_x = 100.0
    max_y = 100.0
    duration = 90.0 + (seed % 60)
    created_ts = time.time() - float(seed % 35)
    num_agents = 80 + int(seed % 120)
    if simulation_id.startswith("demo-"):
        created_ts = time.time() - duration
        num_agents = 100 + int(seed % 40)
    runtime = {
        "simulation_id": simulation_id,
        "created_ts": created_ts,
        "num_agents": num_agents,
        "emergency_type": "fire",
        "floor_number": 1,
        "bounds": {
            "min_x": min_x,
            "max_x": max_x,
            "min_y": min_y,
            "max_y": max_y,
        },
        "duration_seconds": duration,
        "exits": [
            {"id": "exit-left", "x": min_x + 2.0, "y": (min_y + max_y) / 2, "z": (min_y + max_y) / 2, "width": 2.0, "capacity": 100, "name": "Left Exit"},
            {"id": "exit-right", "x": max_x - 2.0, "y": (min_y + max_y) / 2, "z": (min_y + max_y) / 2, "width": 2.0, "capacity": 100, "name": "Right Exit"},
        ],
        "walls": [],
        "obstacles": [],
    }
    _MOCK_SIM_RUNTIME[simulation_id] = runtime
    _prune_mock_runtime()
    return runtime


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return fallback
    return parsed if parsed == parsed else fallback  # NaN guard


def _coerce_bounds_from_snapshot(snapshot: Dict[str, Any]) -> Optional[Dict[str, float]]:
    if not isinstance(snapshot, dict):
        return None
    bounds = snapshot.get("building_bounds")
    if isinstance(bounds, dict):
        min_x = _safe_float(bounds.get("min_x"), 0.0)
        min_y = _safe_float(bounds.get("min_y"), 0.0)
        max_x = _safe_float(bounds.get("max_x"), 0.0)
        max_y = _safe_float(bounds.get("max_y"), 0.0)
        if max_x > min_x and max_y > min_y:
            return {
                "min_x": min_x,
                "min_y": min_y,
                "max_x": max_x,
                "max_y": max_y,
                "width": _safe_float(bounds.get("width"), max_x - min_x),
                "height": _safe_float(bounds.get("height"), max_y - min_y),
            }
    dims = snapshot.get("image_dimensions")
    if isinstance(dims, dict):
        width = _safe_float(dims.get("width"), 0.0)
        height = _safe_float(dims.get("height"), 0.0)
        if width > 0 and height > 0:
            return {
                "min_x": 0.0,
                "min_y": 0.0,
                "max_x": width,
                "max_y": height,
                "width": width,
                "height": height,
            }
    return None


def _coerce_segment_list(items: Any, *, limit: int) -> List[Dict[str, Any]]:
    if not isinstance(items, list):
        return []
    output: List[Dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        x1 = _safe_float(item.get("x1"), float("nan"))
        y1 = _safe_float(item.get("y1"), float("nan"))
        x2 = _safe_float(item.get("x2"), float("nan"))
        y2 = _safe_float(item.get("y2"), float("nan"))
        if not all(v == v for v in (x1, y1, x2, y2)):
            continue
        length = _safe_float(item.get("length"), ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5)
        output.append({
            "x1": x1,
            "y1": y1,
            "x2": x2,
            "y2": y2,
            "length": length,
            "type": str(item.get("type", "internal")),
            "thickness": _safe_float(item.get("thickness"), 2.0),
        })
        if len(output) >= limit:
            break
    return output


def _coerce_rect_list(items: Any, *, limit: int, y_key: str = "y") -> List[Dict[str, Any]]:
    if not isinstance(items, list):
        return []
    output: List[Dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        x = _safe_float(item.get("x"), float("nan"))
        y = _safe_float(item.get(y_key, item.get("y")), float("nan"))
        width = _safe_float(item.get("width"), float("nan"))
        height = _safe_float(item.get("height"), float("nan"))
        if not all(v == v for v in (x, y, width, height)):
            continue
        if width <= 0 or height <= 0:
            continue
        output.append({
            "x": x,
            "y": y,
            "z": y,
            "width": width,
            "height": height,
        })
        if len(output) >= limit:
            break
    return output


def _coerce_exits_list(items: Any, bounds: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    from app.services.floorplan_loader import normalize_exits

    if not isinstance(items, list):
        return []
    exits: List[Dict[str, Any]] = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue
        x = _safe_float(item.get("x"), float("nan"))
        y = _safe_float(item.get("y", item.get("z")), float("nan"))
        if not all(v == v for v in (x, y)):
            continue
        width = max(0.5, min(80.0, _safe_float(item.get("width"), 2.0)))
        exits.append({
            "id": str(item.get("id") or f"snapshot-exit-{index}"),
            "name": str(item.get("name") or f"Snapshot Exit {index}"),
            "x": x,
            "y": y,
            "z": _safe_float(item.get("z"), y),
            "width": width,
            "height": max(0.5, min(80.0, _safe_float(item.get("height"), width))),
            "capacity": max(1, int(round(_safe_float(item.get("capacity"), width * 12)))),
            "is_emergency": bool(item.get("is_emergency", True)),
            "is_accessible": bool(item.get("is_accessible", True)),
            "source": str(item.get("source") or "client_snapshot"),
        })
        if len(exits) >= 300:
            break
    return normalize_exits(exits, bounds)


def _normalize_floor_plan_snapshot(snapshot: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(snapshot, dict):
        return None

    bounds = _coerce_bounds_from_snapshot(snapshot)
    detected_walls = _coerce_segment_list(snapshot.get("detected_walls"), limit=4000)
    boundaries = _coerce_segment_list(snapshot.get("boundaries"), limit=1200)
    rooms = _coerce_rect_list(snapshot.get("rooms"), limit=1200, y_key="y")
    corridors = _coerce_rect_list(snapshot.get("corridors"), limit=400, y_key="y")
    open_spaces = _coerce_rect_list(snapshot.get("open_spaces"), limit=400, y_key="y")
    obstacles = _coerce_rect_list(snapshot.get("detected_obstacles"), limit=1200, y_key="z")
    exits_source = snapshot.get("exits") if isinstance(snapshot.get("exits"), list) else snapshot.get("detected_exits")
    exits = _coerce_exits_list(exits_source, bounds)

    if not detected_walls and not boundaries and not exits and not rooms:
        return None

    normalized: Dict[str, Any] = {
        "detected_walls": detected_walls,
        "boundaries": boundaries,
        "boundary_polygon": snapshot.get("boundary_polygon") if isinstance(snapshot.get("boundary_polygon"), list) else [],
        "detected_obstacles": obstacles,
        "rooms": rooms,
        "corridors": corridors,
        "open_spaces": open_spaces,
        "exits": exits,
        "detected_exits": exits,
        "pipeline": str(snapshot.get("pipeline") or "client-snapshot"),
        "processing_time_ms": snapshot.get("processing_time_ms"),
        "processing_metadata": snapshot.get("processing_metadata") if isinstance(snapshot.get("processing_metadata"), dict) else {},
        "image_dimensions": snapshot.get("image_dimensions") if isinstance(snapshot.get("image_dimensions"), dict) else {},
    }
    if bounds:
        normalized["building_bounds"] = bounds
    return normalized


def _is_mock_pipeline_floorplan(floor_plan_data: Optional[Dict[str, Any]]) -> bool:
    if not floor_plan_data:
        return True
    pipeline = str((floor_plan_data or {}).get("pipeline") or "").strip().lower()
    if pipeline in {"", "mock-fallback", "none"}:
        return True
    wall_count = len((floor_plan_data or {}).get("detected_walls") or [])
    exit_count = len((floor_plan_data or {}).get("exits") or [])
    return wall_count == 0 and exit_count == 0


def _build_mock_frame(simulation_id: str, elapsed_override: Optional[float] = None) -> Dict[str, Any]:
    runtime = _get_mock_runtime(simulation_id)
    now = time.time()
    elapsed = float(elapsed_override if elapsed_override is not None else max(0.0, now - float(runtime.get("created_ts", now))))
    duration = float(runtime.get("duration_seconds", 120.0))
    progress = _clamp(elapsed / max(1.0, duration), 0.0, 1.0)
    num_agents = int(runtime.get("num_agents", 100))
    evacuated = int(round(num_agents * (progress ** 1.08)))
    remaining = max(0, num_agents - evacuated)
    completion = round((evacuated / max(1, num_agents)) * 100.0, 2)
    frame_id = max(1, int(elapsed * 2.0))

    bounds = runtime.get("bounds", {})
    min_x = float(bounds.get("min_x", 0.0))
    max_x = float(bounds.get("max_x", 100.0))
    min_y = float(bounds.get("min_y", 0.0))
    max_y = float(bounds.get("max_y", 100.0))
    span_x = max(1.0, max_x - min_x)
    span_y = max(1.0, max_y - min_y)

    exits = list(runtime.get("exits", []))
    walls = list(runtime.get("walls", []))
    max_agents_render = 240
    active_agents = min(remaining, max_agents_render)
    seed = _mock_seed_for_id(simulation_id)

    def _unit(agent_index: int, salt: float) -> float:
        value = math.sin((seed * 0.013) + (agent_index + 1) * (salt * 0.731))
        return (value + 1.0) * 0.5

    def _project_point_to_segment(
        px: float,
        py: float,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
    ) -> Tuple[float, float, float]:
        ax = px - x1
        ay = py - y1
        bx = x2 - x1
        by = y2 - y1
        len_sq = bx * bx + by * by
        if len_sq <= 1e-9:
            return x1, y1, math.sqrt(ax * ax + ay * ay)
        t = (ax * bx + ay * by) / len_sq
        t = _clamp(t, 0.0, 1.0)
        qx = x1 + t * bx
        qy = y1 + t * by
        dx = px - qx
        dy = py - qy
        return qx, qy, math.sqrt(dx * dx + dy * dy)

    agents: List[Dict[str, Any]] = []
    wall_influence = max(1.2, min(span_x, span_y) * 0.04)
    wall_candidates = walls[:120]
    for i in range(active_agents):
        spawn_x = min_x + span_x * _clamp(0.08 + _unit(i, 2.1) * 0.84, 0.03, 0.97)
        spawn_y = min_y + span_y * _clamp(0.08 + _unit(i, 3.7) * 0.84, 0.03, 0.97)

        if exits:
            exit_index = int(_unit(i, 5.9) * len(exits)) % len(exits)
            target_exit = exits[exit_index]
            target_x = float(target_exit.get("x", max_x - 2.0))
            target_y = float(target_exit.get("z", target_exit.get("y", (min_y + max_y) * 0.5)))
            target_exit_id = str(target_exit.get("id", f"exit-{exit_index + 1}"))
        else:
            target_x = max_x - 2.0
            target_y = min_y + span_y * 0.5
            target_exit_id = "exit-right"

        personal_progress = _clamp(progress * (0.75 + _unit(i, 7.1) * 0.5), 0.0, 1.0)
        dx = target_x - spawn_x
        dy = target_y - spawn_y
        direct_dist = max(1e-6, math.sqrt(dx * dx + dy * dy))
        perp_x = -dy / direct_dist
        perp_y = dx / direct_dist

        lane_offset = (_unit(i, 11.3) - 0.5) * min(span_x, span_y) * 0.18
        sway = math.sin((elapsed * 0.85) + (i * 0.41)) * min(span_x, span_y) * 0.014 * (1.0 - personal_progress)
        lateral = lane_offset * (1.0 - personal_progress) + sway

        x = spawn_x + dx * personal_progress + perp_x * lateral
        y = spawn_y + dy * personal_progress + perp_y * lateral

        if wall_candidates:
            for wall in wall_candidates:
                try:
                    x1 = float(wall.get("x1", 0.0))
                    y1 = float(wall.get("y1", 0.0))
                    x2 = float(wall.get("x2", 0.0))
                    y2 = float(wall.get("y2", 0.0))
                except (TypeError, ValueError):
                    continue
                qx, qy, dist = _project_point_to_segment(x, y, x1, y1, x2, y2)
                if dist >= wall_influence:
                    continue
                push = (wall_influence - dist) * 0.88
                nx = x - qx
                ny = y - qy
                norm = math.sqrt(nx * nx + ny * ny)
                if norm <= 1e-6:
                    nx = perp_x
                    ny = perp_y
                    norm = max(1e-6, math.sqrt(nx * nx + ny * ny))
                x += (nx / norm) * push
                y += (ny / norm) * push

        x = _clamp(x, min_x + 1.0, max_x - 1.0)
        y = _clamp(y, min_y + 1.0, max_y - 1.0)

        panic_level = _clamp(0.18 + progress * 0.56 + (_unit(i, 13.7) - 0.5) * 0.28, 0.0, 1.0)
        status = "moving"
        if progress < 0.08 and _unit(i, 17.9) < 0.22:
            status = "waiting"

        agents.append({
            "agent_id": i + 1,
            "x": round(x, 3),
            "y": round(y, 3),
            "z": round(y, 3),
            "speed": round(0.75 + _unit(i, 19.1) * 0.95, 3),
            "status": status,
            "panic_level": round(panic_level, 3),
            "target_exit": target_exit_id,
        })
    exit_evac_counts: List[Dict[str, Any]] = []
    if exits:
        weight_total = sum(range(1, len(exits) + 1))
        assigned = 0
        for idx, exit_item in enumerate(exits, start=1):
            if idx == len(exits):
                count = max(0, evacuated - assigned)
            else:
                count = int(round(evacuated * (idx / max(1, weight_total))))
                assigned += count
            exit_evac_counts.append({"exit_id": str(exit_item.get("id", f"exit-{idx}")), "count": int(count)})

    profile_counts = [
        {"profile_id": "staff", "count": max(0, int(round(remaining * 0.18)))},
        {"profile_id": "visitor", "count": max(0, int(round(remaining * 0.66)))},
        {"profile_id": "mobility_limited", "count": max(0, remaining - int(round(remaining * 0.18)) - int(round(remaining * 0.66)))},
    ]

    return {
        "simulation_id": simulation_id,
        "timestamp": round(elapsed, 3),
        "frame_id": frame_id,
        "agents": agents,
        "exits": exits,
        "walls": list(runtime.get("walls", [])),
        "obstacles": list(runtime.get("obstacles", [])),
        "bottlenecks": [],
        "hazards": [],
        "hazard_state": {
            "active": [{"type": runtime.get("emergency_type", "fire"), "intensity": round(_clamp(0.3 + progress * 0.5, 0.0, 1.0), 3)}],
            "blocked_exits": [],
        },
        "collision_events": 0,
        "wall_penetration_count": 0,
        "nav_debug": {
            "pathfinding_enabled": False,
            "grid_resolution": None,
            "blocked_exit_count": 0,
            "stuck_events": 0,
        },
        "exit_evac_counts": exit_evac_counts,
        "profile_counts": profile_counts,
        "stats": {
            "total_agents": num_agents,
            "evacuated": evacuated,
            "remaining": remaining,
            "completion_percentage": completion,
            "total_time": round(elapsed, 3),
            "exit_usage": {item.get("exit_id"): item.get("count", 0) for item in exit_evac_counts},
            "profile_counts": {item.get("profile_id"): item.get("count", 0) for item in profile_counts},
        },
    }


def _build_mock_frames(simulation_id: str, limit: int = 200, stride: int = 1) -> List[Dict[str, Any]]:
    runtime = _get_mock_runtime(simulation_id)
    now = time.time()
    elapsed = max(0.0, now - float(runtime.get("created_ts", now)))
    frame_step_seconds = 0.5 * max(1, stride)
    max_points = max(1, min(limit, 240))
    frames = []
    for idx in range(max_points):
        offset = (max_points - 1 - idx) * frame_step_seconds
        frame_elapsed = max(0.0, elapsed - offset)
        frames.append(_build_mock_frame(simulation_id, elapsed_override=frame_elapsed))
    return frames


def _build_mock_summary(simulation_id: str) -> Dict[str, Any]:
    frame = _build_mock_frame(simulation_id)
    stats = frame.get("stats", {}) or {}
    return {
        "simulation_id": simulation_id,
        "timestamp": frame.get("timestamp"),
        "total_agents": stats.get("total_agents", 0),
        "evacuated": stats.get("evacuated", 0),
        "total_time": stats.get("total_time", frame.get("timestamp", 0)),
        "frames_count": int(max(1, frame.get("frame_id", 1))),
        "final_stats": stats,
    }


def _build_mock_metrics(simulation_id: str) -> Dict[str, Any]:
    summary = _build_mock_summary(simulation_id)
    stats = summary.get("final_stats", {}) or {}
    completion = float(stats.get("completion_percentage", 0.0))
    score = round(45.0 + completion * 0.55, 2)
    grade = "A" if score >= 90 else "B" if score >= 75 else "C"
    return {
        "simulation_id": simulation_id,
        "frame_count": int(summary.get("frames_count", 0)),
        "metrics": {
            "completion_percentage": completion,
            "evacuated": int(stats.get("evacuated", 0)),
            "remaining": int(stats.get("remaining", 0)),
            "total_time": float(stats.get("total_time", 0.0)),
        },
        "total_score": score,
        "grade": grade,
        "component_scores": {
            "evacuation_time": round(max(0.0, min(100.0, 100.0 - float(stats.get("total_time", 0.0)) * 0.6)), 2),
            "exit_capacity": 78.0,
            "bottleneck": 82.0,
            "disaster_resilience": 76.0,
            "accessibility": 74.0,
        },
        "factors": {
            "profile_counts": stats.get("profile_counts", {}),
            "exit_usage": stats.get("exit_usage", {}),
        },
        "recommendations": [
            "Increase signed guidance near secondary exits.",
            "Keep corridor obstacles minimized during evacuation.",
        ],
    }


__all__ = [
    "MOCK_SIM_MAX_ENTRIES",
    "MOCK_SIM_TTL_SECONDS",
    "_MOCK_SIM_RUNTIME",
    "_build_mock_frame",
    "_build_mock_frames",
    "_build_mock_metrics",
    "_build_mock_summary",
    "_get_mock_runtime",
    "_is_demo_like_simulation_id",
    "_is_mock_pipeline_floorplan",
    "_normalize_floor_plan_snapshot",
    "_prune_mock_runtime",
    "_register_mock_runtime",
    "list_mock_runtime_entries",
]
