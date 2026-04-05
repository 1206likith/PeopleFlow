"""
Floor plan processing facade.
Centralizes image processing and fallback behavior.
"""

import logging
from typing import Dict, Optional, Tuple
from app.services.floorplan_quality import (
    build_floor_plan_quality_report,
    detector_health_from_quality,
)

logger = logging.getLogger(__name__)

_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tif", ".tiff"}
_DETECTION_MODES = {"auto", "traditional", "semantic"}
_NOISE_WARNINGS = {"excessive_diagonal_walls", "low_orthogonal_ratio", "line_storm_artifact"}


def _is_image_payload(file_type: str, file_path: str) -> bool:
    if file_type and file_type.startswith("image/"):
        return True
    if not file_path:
        return False
    try:
        from pathlib import Path
        return Path(file_path).suffix.lower() in _IMAGE_EXTENSIONS
    except Exception:
        return False


def _normalize_mode(options: Dict) -> str:
    mode = str((options or {}).get("mode") or "").strip().lower()
    if mode in _DETECTION_MODES:
        return mode
    if "use_semantic" in (options or {}):
        return "semantic" if bool(options.get("use_semantic")) else "traditional"
    return "auto"


def _semantic_runtime_ready() -> bool:
    """
    Returns True only when the semantic pipeline can actually execute.
    """
    try:
        from app.services.floor_plan_processor import CV2_AVAILABLE as processor_cv2_available, cv2 as processor_cv2
        from app.services.semantic_floorplan import CV2_AVAILABLE as semantic_cv2_available, cv2 as semantic_cv2
    except Exception:
        return False

    return bool(
        processor_cv2_available
        and semantic_cv2_available
        and processor_cv2 is not None
        and semantic_cv2 is not None
    )


def _extract_counts(payload: Dict) -> Tuple[int, int, int]:
    wall_count = int(payload.get("wall_count", len(payload.get("walls", []) or [])) or 0)
    room_count = int(payload.get("room_count", len(payload.get("rooms", []) or [])) or 0)
    exit_count = int(payload.get("exit_count", len(payload.get("exits", []) or [])) or 0)
    return wall_count, room_count, exit_count


def _detection_score(payload: Dict) -> float:
    if not payload:
        return 0.0
    quality = payload.get("quality", {}) or {}
    quality_score = float(quality.get("score", 0.0) or 0.0)
    wall_count, room_count, exit_count = _extract_counts(payload)
    processed_bonus = 0.4 if payload.get("processed") else 0.0
    return processed_bonus + quality_score + min(wall_count / 60.0, 1.0) + min(room_count / 20.0, 0.4) + min(exit_count / 15.0, 0.3)


def _is_high_wall_noise(payload: Dict) -> bool:
    quality = payload.get("quality", {}) or {}
    warnings = set(quality.get("warnings", []) or [])
    wall_count, _, _ = _extract_counts(payload)
    return bool(_NOISE_WARNINGS.intersection(warnings)) and wall_count >= 120


def _needs_retry(payload: Dict) -> bool:
    if not payload:
        return True
    if not payload.get("processed"):
        return True
    wall_count, room_count, exit_count = _extract_counts(payload)
    quality = payload.get("quality", {}) or {}
    quality_score = float(quality.get("score", 0.0) or 0.0)
    warnings = set(quality.get("warnings", []) or [])
    if "excessive_diagonal_walls" in warnings:
        return True
    if wall_count > 600 and "low_orthogonal_ratio" in warnings:
        return True
    if quality_score < 0.55:
        return True
    return wall_count < 12 or (room_count == 0 and quality_score < 0.62) or (exit_count == 0 and wall_count >= 20)


def _resolve_model_bundle_version(detector_mode: str, pipeline: str) -> str:
    if detector_mode == "traditional" or pipeline.startswith("traditional"):
        return "traditional-v1"
    try:
        from modules.ai_engine.registry import get_model

        wall_model = get_model("floorplan_wall_segmentation") or {}
        exit_model = get_model("floorplan_exit_detection") or {}
        wall_version = str(wall_model.get("updated_at") or wall_model.get("path") or "unversioned")
        exit_version = str(exit_model.get("updated_at") or exit_model.get("path") or "unversioned")
        return f"semantic::{wall_version}::{exit_version}"
    except Exception:
        return "semantic-unversioned"


def _augment_detection(
    detected: Dict,
    *,
    detector_mode: str,
    fallback_reason: Optional[str] = None,
) -> Dict:
    detected["fallback_reason"] = fallback_reason
    quality_report = build_floor_plan_quality_report(detected, detected, detected.get("exits", []))
    detected["detector_mode"] = detector_mode
    detected["quality_report"] = quality_report
    detected["simulation_ready"] = bool(quality_report.get("simulation_ready"))
    detected["detector_health"] = detector_health_from_quality(
        float(quality_report.get("quality_score", 0.0)),
        bool(quality_report.get("simulation_ready", False)),
    )
    detected["model_bundle_version"] = _resolve_model_bundle_version(
        detector_mode,
        str(detected.get("pipeline", "unknown")),
    )
    return detected


def process_floor_plan_image(
    file_type: str,
    file_path: str,
    options: Optional[Dict] = None,
) -> Dict:
    """
    Process an uploaded floor plan image and return detected elements.
    Returns a consistent structure even if processing is unavailable.
    """
    if not _is_image_payload(file_type, file_path):
        logger.info("Skipping image processing for non-image file")
        payload = {
            "processed": False,
            "walls": [],
            "exits": [],
            "obstacles": [],
            "pipeline": "none",
            "pipeline_steps": [{"name": "skip_non_image", "duration_ms": 0}],
        }
        return _augment_detection(payload, detector_mode="auto", fallback_reason="non_image_payload")

    try:
        from app.services.floor_plan_processor import floor_plan_processor
        options = options or {}
        requested_mode = _normalize_mode(options)
        semantic_ready = _semantic_runtime_ready()
        fallback_reason: Optional[str] = None

        if requested_mode == "traditional":
            use_semantic = False
        elif requested_mode == "semantic":
            use_semantic = True
        else:
            # auto mode
            use_semantic = semantic_ready
            if not semantic_ready:
                fallback_reason = "semantic_dependencies_missing"

        detected = floor_plan_processor.process_floor_plan(
            file_path,
            use_semantic=use_semantic,
            debug=options.get("debug", False),
            debug_dir=options.get("debug_dir"),
        )
        if not detected.get("processed") and detected.get("processing_error"):
            fallback_reason = str(detected.get("processing_error"))

        if use_semantic and _needs_retry(detected):
            logger.info("Semantic pass was low-confidence, retrying with traditional OpenCV pipeline")
            traditional = floor_plan_processor.process_floor_plan(
                file_path,
                use_semantic=False,
                debug=options.get("debug", False),
                debug_dir=options.get("debug_dir"),
            )
            semantic_wall_count, _, semantic_exit_count = _extract_counts(detected)
            traditional_wall_count, _, traditional_exit_count = _extract_counts(traditional)
            should_use_traditional = False
            if traditional_exit_count > semantic_exit_count:
                should_use_traditional = True
            elif semantic_exit_count == 0:
                should_use_traditional = True
            elif _is_high_wall_noise(detected) and traditional_wall_count <= max(1500, semantic_wall_count // 2):
                should_use_traditional = True
            elif _detection_score(traditional) >= _detection_score(detected):
                should_use_traditional = True

            if should_use_traditional:
                if semantic_exit_count == 0:
                    fallback_reason = "semantic_zero_exits"
                elif _is_high_wall_noise(detected):
                    fallback_reason = "semantic_high_wall_noise"
                else:
                    fallback_reason = "semantic_low_confidence"
                detected = traditional
                detected["pipeline"] = "traditional_retry"
                pipeline_steps = list(detected.get("pipeline_steps", []))
                pipeline_steps.append(
                    {
                        "name": "retry_from_semantic",
                        "duration_ms": 0,
                        "selected": True,
                        "fallback_reason": fallback_reason,
                    }
                )
                detected["pipeline_steps"] = pipeline_steps

        detected = _augment_detection(detected, detector_mode=requested_mode, fallback_reason=fallback_reason)

        logger.info(
            "Processed floor plan: %s walls, %s exits detected",
            detected.get("wall_count", 0),
            detected.get("exit_count", 0),
        )
        try:
            from app.core.metrics import (
                floorplan_processing_total,
                floorplan_processing_duration_seconds,
                floorplan_quality_score,
                floorplan_wall_count,
                floorplan_exit_count,
            )
            pipeline = detected.get("pipeline", "unknown")
            status = "success" if detected.get("processed") else "failed"
            floorplan_processing_total.labels(pipeline=pipeline, status=status).inc()
            processing_ms = detected.get("processing_time_ms")
            if processing_ms is not None:
                floorplan_processing_duration_seconds.labels(pipeline=pipeline).observe(processing_ms / 1000.0)
            quality = detected.get("quality", {}).get("score")
            if quality is not None:
                floorplan_quality_score.observe(float(quality))
            floorplan_wall_count.observe(float(detected.get("wall_count", 0)))
            floorplan_exit_count.observe(float(detected.get("exit_count", 0)))
        except Exception as metrics_error:
            logger.debug("Floor plan metrics skipped: %s", metrics_error)
        return detected
    except ImportError as e:
        logger.warning("OpenCV not available, skipping floor plan processing: %s", e)
    except Exception as e:
        logger.warning("Could not process floor plan image: %s", e, exc_info=True)

    return _augment_detection(
        {"processed": False, "walls": [], "exits": [], "obstacles": [], "pipeline": "none", "pipeline_steps": []},
        detector_mode=_normalize_mode(options or {}),
        fallback_reason="processing_exception",
    )
