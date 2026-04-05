from __future__ import annotations

from typing import Any, Dict, List, Optional


def _as_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return fallback
    return parsed if parsed == parsed else fallback


def count_usable_exits(exits: List[Dict[str, Any]]) -> int:
    usable = 0
    for item in exits or []:
        if not isinstance(item, dict):
            continue
        x = item.get("x")
        y = item.get("y")
        z = item.get("z", y)
        width = item.get("width", item.get("height", 0))
        try:
            coords_ok = all(v == v for v in (float(x), float(z)))
            width_ok = float(width) > 0.2
        except (TypeError, ValueError):
            continue
        if coords_ok and width_ok:
            usable += 1
    return usable


def build_floor_plan_quality_report(
    floor_plan_doc: Optional[Dict[str, Any]] = None,
    floor_plan_data: Optional[Dict[str, Any]] = None,
    exits: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    source = floor_plan_doc or floor_plan_data or {}
    processing_metadata = source.get("processing_metadata", {}) or {}
    quality = source.get("quality") or processing_metadata.get("quality", {}) or {}
    warnings = list(quality.get("warnings", []) or [])

    walls = _as_list(source.get("detected_walls") or source.get("walls"))
    boundaries = _as_list(source.get("boundaries"))
    rooms = _as_list(source.get("rooms"))
    all_exits = exits if exits is not None else source.get("exits") or source.get("detected_exits") or []

    wall_count = len(walls)
    boundary_count = len(boundaries)
    geometry_count = wall_count + boundary_count
    room_count = len(rooms)
    exit_count = len(_as_list(source.get("detected_exits") or source.get("exits")))
    usable_exit_count = count_usable_exits(all_exits)
    processed = bool(source.get("processed", processing_metadata.get("processed", True)))
    quality_score = float(quality.get("score", 0.0) or 0.0)
    pipeline = str(source.get("pipeline") or processing_metadata.get("pipeline") or "unknown")
    fallback_reason = source.get("fallback_reason") or processing_metadata.get("fallback_reason")
    model_bundle_version = source.get("model_bundle_version") or processing_metadata.get("model_bundle_version")

    readiness_reasons: List[str] = []
    if not processed:
        readiness_reasons.append("not_processed")
    if pipeline in {"none", "mock-fallback", ""}:
        readiness_reasons.append("pipeline_unusable")
    if geometry_count <= 0:
        readiness_reasons.append("no_geometry")
    if usable_exit_count <= 0:
        readiness_reasons.append("no_usable_exits")
    if quality_score < 0.45:
        readiness_reasons.append("low_quality_score")
    if fallback_reason:
        readiness_reasons.append(str(fallback_reason))

    simulation_ready = len([reason for reason in readiness_reasons if reason != fallback_reason]) == 0
    if source.get("simulation_ready") is False:
        simulation_ready = False

    return {
        "processed": processed,
        "pipeline": pipeline,
        "quality_score": quality_score,
        "warnings": warnings,
        "wall_count": wall_count,
        "boundary_count": boundary_count,
        "geometry_count": geometry_count,
        "room_count": room_count,
        "exit_count": exit_count,
        "usable_exit_count": usable_exit_count,
        "fallback_reason": fallback_reason,
        "model_bundle_version": model_bundle_version,
        "simulation_ready": simulation_ready,
        "readiness_reasons": readiness_reasons,
    }


def is_floor_plan_ready_for_runtime(quality_report: Dict[str, Any]) -> bool:
    return (
        bool(quality_report.get("simulation_ready"))
        and int(quality_report.get("usable_exit_count", 0)) > 0
        and int(quality_report.get("geometry_count", quality_report.get("wall_count", 0))) > 0
    )


def build_runtime_geometry_status(
    floor_plan_data: Optional[Dict[str, Any]],
    exits: Optional[List[Dict[str, Any]]],
) -> Dict[str, Any]:
    source = floor_plan_data or {}
    walls = _as_list(source.get("detected_walls") or source.get("walls"))
    boundaries = _as_list(source.get("boundaries"))
    usable_exits = count_usable_exits(exits or source.get("exits") or source.get("detected_exits") or [])
    wall_count = len(walls)
    boundary_count = len(boundaries)
    geometry_count = wall_count + boundary_count
    pipeline = str(source.get("pipeline") or "").strip().lower()
    fallback_reason = source.get("fallback_reason")

    reasons: List[str] = []
    if geometry_count <= 0:
        reasons.append("no_geometry")
    if usable_exits <= 0:
        reasons.append("no_usable_exits")
    if pipeline in {"", "none", "mock-fallback"}:
        reasons.append("pipeline_unusable")
    if fallback_reason:
        reasons.append(str(fallback_reason))

    return {
        "valid": geometry_count > 0 and usable_exits > 0 and pipeline not in {"", "none", "mock-fallback"},
        "wall_count": wall_count,
        "boundary_count": boundary_count,
        "geometry_count": geometry_count,
        "usable_exit_count": usable_exits,
        "pipeline": pipeline or "unknown",
        "fallback_reason": fallback_reason,
        "reasons": reasons,
    }


def detector_health_from_quality(score: float, simulation_ready: bool) -> str:
    if simulation_ready and score >= 0.75:
        return "good"
    if simulation_ready and score >= 0.55:
        return "fair"
    return "poor"


def merge_quality_report(payload: Dict[str, Any]) -> Dict[str, Any]:
    report = build_floor_plan_quality_report(payload, payload, payload.get("exits", []))
    payload["quality_report"] = report
    payload["simulation_ready"] = bool(report.get("simulation_ready"))
    payload["detector_health"] = detector_health_from_quality(
        _safe_float(report.get("quality_score"), 0.0),
        bool(report.get("simulation_ready")),
    )
    return payload
