"""
Compatibility shim for the former simulation route monolith.

Route handlers now live in dedicated route modules, and shared mock/demo
runtime helpers live in ``app.services.simulation_mock_runtime_service``.
This module remains only to preserve any lingering imports while the codebase
finishes migrating away from the old route-centric architecture.
"""
from app.services.simulation_mock_runtime_service import (
    MOCK_SIM_MAX_ENTRIES,
    MOCK_SIM_TTL_SECONDS,
    _MOCK_SIM_RUNTIME,
    _build_mock_frame,
    _build_mock_frames,
    _build_mock_metrics,
    _build_mock_summary,
    _get_mock_runtime,
    _is_demo_like_simulation_id,
    _is_mock_pipeline_floorplan,
    _normalize_floor_plan_snapshot,
    _prune_mock_runtime,
    _register_mock_runtime,
)

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
]
