"""
Application service for starting simulations.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import HTTPException, Request

from app.api.contracts.simulation_contracts import SimulationResponse
from app.core.config import settings
from app.core.metrics import simulations_started_total
from app.core.validation import SimulationConfigSchema
from app.services.audit_log import record_event
from app.services.floor_plan_document_service import (
    build_floor_plan_quality_report,
    build_runtime_geometry_status,
    fetch_floor_plan_doc,
    is_floor_plan_ready_for_runtime,
)
from app.services.frame_ingest import ingest_frame
from app.services.idempotency import (
    build_idempotency_key,
    build_replay_response,
    get_cached_response,
    store_response,
)
from app.services.simulation_mock_runtime_service import (
    _is_mock_pipeline_floorplan,
    _normalize_floor_plan_snapshot,
    _register_mock_runtime,
)
from app.services.simulation_repository import get_simulation_repository

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


class SimulationStartService:
    async def start_simulation(
        self,
        request: Request,
        config: SimulationConfigSchema,
        current_user: dict,
    ) -> SimulationResponse:
        from app.services.floorplan_loader import load_floor_plan_data
        from app.services.mock_simulation import run_mock_simulation
        from app.services.simulation_state import simulation_state_manager
        from app.services.unity_bridge import unity_bridge

        correlation_id = getattr(request.state, "correlation_id", "unknown")
        user_id = str(current_user.get("_id", current_user.get("id", "demo_user")))
        raw_idempotency_key = request.headers.get("Idempotency-Key")
        idempotency_key = build_idempotency_key(request, user_id)
        if idempotency_key:
            cached = get_cached_response(idempotency_key)
            if cached:
                return build_replay_response(cached)

        if not simulation_state_manager.can_start(settings.MAX_CONCURRENT_SIMULATIONS):
            raise HTTPException(status_code=429, detail="Simulation capacity reached, try again later")

        emergency_type_value = config.emergency_type.value if hasattr(config.emergency_type, "value") else str(config.emergency_type)
        hazards = [h.model_dump() if hasattr(h, "model_dump") else h.dict() for h in (config.hazards or [])]
        agent_profiles = [p.model_dump() if hasattr(p, "model_dump") else p.dict() for p in (config.agent_profiles or [])]
        blocked_exits = list(config.blocked_exits or [])
        parameter_overrides = dict(config.parameter_overrides or {})
        ablation = config.ablation.model_dump() if hasattr(config.ablation, "model_dump") else (config.ablation or None)
        max_iterations = config.max_iterations
        realtime = config.realtime
        tags = list(config.tags or [])
        notes = config.notes
        label = config.label
        priority = config.priority
        record_frames = bool(config.record_frames)
        frame_stride = max(1, int(config.frame_stride or 1))
        storage_policy = {
            "store_agents": bool(config.store_agents),
            "store_bottlenecks": bool(config.store_bottlenecks),
            "store_walls": bool(config.store_walls),
            "store_exits": bool(config.store_exits),
            "store_obstacles": bool(config.store_obstacles),
            "store_hazards": bool(config.store_hazards),
        }
        max_runtime_seconds = config.max_runtime_seconds

        if not settings.IS_DEMO_MODE:
            if not config.floor_plan_id:
                raise HTTPException(status_code=422, detail="floor_plan_id is required in production mode")
            if str(config.floor_plan_id).startswith("mock-"):
                raise HTTPException(status_code=422, detail="Mock floor plans are not allowed in production mode")

        floor_plan_data, exits = await load_floor_plan_data(
            config.floor_plan_id,
            config.floor_number,
            config.exits,
            allow_inferred_exits=False,
        )
        floor_plan_doc = await fetch_floor_plan_doc(config.floor_plan_id, user_id) if config.floor_plan_id else None
        if (
            config.floor_plan_id
            and floor_plan_doc
            and (
                not floor_plan_data
                or (
                    len((floor_plan_data or {}).get("detected_walls", []) or []) == 0
                    and len((floor_plan_data or {}).get("boundaries", []) or []) == 0
                )
            )
        ):
            refreshed_floor_plan_data, refreshed_exits = await load_floor_plan_data(
                config.floor_plan_id,
                config.floor_number,
                config.exits,
                allow_inferred_exits=False,
            )
            if refreshed_floor_plan_data:
                floor_plan_data = refreshed_floor_plan_data
            if refreshed_exits:
                exits = refreshed_exits

        snapshot_floor_plan_data = _normalize_floor_plan_snapshot(getattr(config, "floor_plan_snapshot", None))
        if settings.IS_DEMO_MODE and snapshot_floor_plan_data and _is_mock_pipeline_floorplan(floor_plan_data):
            floor_plan_data = snapshot_floor_plan_data
            snapshot_exits = list(snapshot_floor_plan_data.get("exits", []))
            if snapshot_exits:
                exits = snapshot_exits
            logger.info(
                "Using client floor plan snapshot before simulation start (floor_plan_id=%s)",
                config.floor_plan_id,
            )
        elif (
            settings.IS_DEMO_MODE
            and snapshot_floor_plan_data
            and floor_plan_data
            and str((floor_plan_data or {}).get("pipeline") or "").strip().lower() in {"", "mock-fallback", "none"}
        ):
            merged = dict(floor_plan_data)
            for key in (
                "detected_walls",
                "boundaries",
                "boundary_polygon",
                "detected_obstacles",
                "rooms",
                "corridors",
                "open_spaces",
                "building_bounds",
                "image_dimensions",
            ):
                if snapshot_floor_plan_data.get(key):
                    merged[key] = snapshot_floor_plan_data.get(key)
            if snapshot_floor_plan_data.get("pipeline"):
                merged["pipeline"] = snapshot_floor_plan_data.get("pipeline")
            floor_plan_data = merged
            snapshot_exits = list(snapshot_floor_plan_data.get("exits", []))
            if snapshot_exits:
                exits = snapshot_exits
        elif (
            not settings.IS_DEMO_MODE
            and snapshot_floor_plan_data
            and _is_mock_pipeline_floorplan(floor_plan_data)
        ):
            raise HTTPException(status_code=422, detail="Client snapshot fallback is disabled in production mode")

        quality_report = build_floor_plan_quality_report(floor_plan_doc, floor_plan_data, exits)
        runtime_geometry = build_runtime_geometry_status(floor_plan_data, exits)
        if not settings.IS_DEMO_MODE:
            if not floor_plan_doc:
                raise HTTPException(status_code=422, detail="Floor plan not found for production simulation")
            if not is_floor_plan_ready_for_runtime(quality_report):
                raise HTTPException(
                    status_code=422,
                    detail={
                        "code": "floor_plan_not_ready",
                        "message": "Floor plan is not simulation-ready",
                        "quality_report": quality_report,
                    },
                )
        if not runtime_geometry.get("valid"):
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "floor_plan_geometry_invalid",
                    "message": "Simulation requires uploaded geometry (walls/boundaries) and usable exits",
                    "geometry": runtime_geometry,
                    "quality_report": quality_report,
                },
            )

        simulation = {
            "user_id": user_id,
            "tenant_id": "global",
            "floor_plan_id": config.floor_plan_id,
            "floor_number": config.floor_number,
            "num_agents": config.num_agents,
            "emergency_type": emergency_type_value,
            "panic_level": config.panic_level,
            "exits": config.exits,
            "hazards": hazards,
            "agent_profiles": agent_profiles,
            "blocked_exits": blocked_exits,
            "parameter_overrides": parameter_overrides,
            "ablation": ablation,
            "max_iterations": max_iterations,
            "realtime": realtime,
            "seed": config.seed,
            "tags": tags,
            "notes": notes,
            "label": label,
            "priority": priority,
            "record_frames": record_frames,
            "frame_stride": frame_stride,
            "storage_policy": storage_policy,
            "max_runtime_seconds": max_runtime_seconds,
            "floor_plan_quality_report": quality_report,
            "floor_plan_simulation_ready": bool(quality_report.get("simulation_ready")),
            "detector_mode": (floor_plan_data or {}).get("detector_mode"),
            "detector_health": (floor_plan_data or {}).get("detector_health"),
            "fallback_reason": (floor_plan_data or {}).get("fallback_reason"),
            "floor_plan_model_bundle_version": (floor_plan_data or {}).get("model_bundle_version"),
            "status": "running",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

        try:
            repository = await get_simulation_repository()
            simulation_id = await repository.create(simulation)
        except HTTPException:
            raise
        except Exception as exc:
            if not settings.IS_DEMO_MODE:
                logger.error("Simulation create failed in production mode: %s", exc, exc_info=True)
                raise HTTPException(status_code=503, detail="Database unavailable")
            logger.warning("Simulation create fell back to demo persistence: %s", exc, extra={"correlation_id": correlation_id})
            simulation_id = f"mock-{uuid.uuid4().hex[:12]}"

        simulation_state_manager.register_simulation(
            simulation_id,
            status="running",
            metadata={"user_id": user_id, "num_agents": config.num_agents, "emergency_type": emergency_type_value},
        )

        _safe_audit(
            "simulation_started",
            actor=user_id,
            metadata={
                "simulation_id": simulation_id,
                "floor_plan_id": config.floor_plan_id,
                "floor_number": config.floor_number,
                "num_agents": config.num_agents,
                "emergency_type": emergency_type_value,
                "panic_level": config.panic_level,
                "seed": config.seed,
            },
        )

        simulations_started_total.labels(emergency_type=emergency_type_value).inc()
        from app.core.metrics import simulation_agents_total

        simulation_agents_total.observe(config.num_agents)
        logger.info(
            "Started simulation %s",
            simulation_id,
            extra={
                "correlation_id": correlation_id,
                "simulation_id": simulation_id,
                "user_id": user_id,
                "num_agents": config.num_agents,
                "emergency_type": emergency_type_value,
            },
        )

        _register_mock_runtime(
            simulation_id,
            num_agents=config.num_agents,
            emergency_type=emergency_type_value,
            floor_number=config.floor_number,
            exits=exits,
            floor_plan_data=floor_plan_data,
        )

        boundary_payload = config.boundary.model_dump() if getattr(config, "boundary", None) else self._derive_boundary_payload(floor_plan_data)
        unity_connected = simulation_id in unity_bridge.unity_connections
        if unity_connected:
            try:
                if floor_plan_data:
                    await unity_bridge._send_floor_plan_to_unity(simulation_id)
                await unity_bridge.start_simulation(
                    simulation_id,
                    {
                        "schema_version": 1,
                        "num_agents": config.num_agents,
                        "emergency_type": emergency_type_value,
                        "panic_level": config.panic_level,
                        "floor_number": config.floor_number or 1,
                        "seed": config.seed,
                        "exits": exits,
                        "hazards": hazards,
                        "agent_profiles": agent_profiles,
                        "blocked_exits": blocked_exits,
                        "parameter_overrides": parameter_overrides,
                        "ablation": ablation,
                        "max_iterations": max_iterations,
                        "realtime": realtime,
                        "record_frames": record_frames,
                        "frame_stride": frame_stride,
                        "storage_policy": storage_policy,
                        "max_runtime_seconds": max_runtime_seconds,
                        "tags": tags,
                        "label": label,
                        "priority": priority,
                        "boundary": boundary_payload,
                    },
                )
                logger.info("Sent start command to Unity for simulation %s", simulation_id)
            except Exception as exc:
                logger.warning("Could not send to Unity, falling back to mock: %s", exc)
                unity_connected = False

        frame_counter = 0

        async def send_updates(frame_data):
            nonlocal frame_counter
            frame_counter += 1
            if not record_frames:
                return
            if frame_stride > 1 and frame_counter % frame_stride != 0:
                return
            frame_data.setdefault("type", "simulation_update")
            frame_data.setdefault("simulation_id", simulation_id)
            if storage_policy.get("store_walls") and not frame_data.get("walls") and floor_plan_data:
                frame_data["walls"] = floor_plan_data.get("detected_walls") or floor_plan_data.get("boundaries") or []
            if storage_policy.get("store_exits") and not frame_data.get("exits"):
                frame_data["exits"] = exits
            if not storage_policy.get("store_agents"):
                frame_data["agents"] = []
            if not storage_policy.get("store_bottlenecks"):
                frame_data["bottlenecks"] = []
            if not storage_policy.get("store_obstacles"):
                frame_data.pop("obstacles", None)
            if not storage_policy.get("store_hazards"):
                frame_data["hazard_state"] = None
                frame_data["hazards"] = []
            if not storage_policy.get("store_walls"):
                frame_data.pop("walls", None)
            if not storage_policy.get("store_exits"):
                frame_data.pop("exits", None)
                frame_data.pop("exit_usage", None)
                frame_data.pop("exit_evac_counts", None)
            logger.info(
                "Broadcasting frame for %s: %s agents, %s walls, %s exits",
                simulation_id,
                len(frame_data.get("agents", [])),
                len(frame_data.get("walls", [])),
                len(frame_data.get("exits", [])),
            )
            await ingest_frame(simulation_id, frame_data)

        import asyncio

        try:
            logger.info(
                "Creating simulation task for %s with %s exits, %s agents",
                simulation_id,
                len(exits),
                config.num_agents,
            )
            task = asyncio.create_task(
                run_mock_simulation(
                    simulation_id,
                    config.num_agents,
                    emergency_type_value,
                    send_updates,
                    floor_number=config.floor_number or 1,
                    exits=exits,
                    floor_plan_data=floor_plan_data,
                    seed=config.seed,
                    hazards=hazards,
                    agent_profiles=agent_profiles,
                    blocked_exits=blocked_exits,
                    parameter_overrides=parameter_overrides,
                    ablation=ablation,
                    realtime=realtime if realtime is not None else True,
                    max_iterations=max_iterations or 1000,
                    max_runtime_seconds=max_runtime_seconds,
                )
            )
            logger.info("Simulation task created for %s. Task running: %s", simulation_id, not task.done())
        except Exception as exc:
            logger.error("Failed to start simulation task: %s", exc, exc_info=True)

        response_payload = {
            "id": simulation_id,
            "status": "running",
            "created_at": simulation["created_at"],
        }
        if idempotency_key:
            store_response(
                idempotency_key,
                200,
                response_payload,
                {"Idempotency-Key": raw_idempotency_key or idempotency_key},
                {"path": request.url.path},
            )
        return SimulationResponse(**response_payload)

    @staticmethod
    def _derive_boundary_payload(data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not data:
            return None
        polygon = data.get("boundary_polygon") or []
        points = []
        if polygon:
            for point in polygon:
                if isinstance(point, dict):
                    points.append({"x": float(point.get("x", 0.0)), "y": float(point.get("y", 0.0))})
        if not points:
            bounds = data.get("building_bounds") or {}
            if bounds:
                min_x = float(bounds.get("min_x", 0.0))
                max_x = float(bounds.get("max_x", 0.0))
                min_y = float(bounds.get("min_y", 0.0))
                max_y = float(bounds.get("max_y", 0.0))
                points = [
                    {"x": min_x, "y": min_y},
                    {"x": max_x, "y": min_y},
                    {"x": max_x, "y": max_y},
                    {"x": min_x, "y": max_y},
                ]
        if not points:
            return None
        min_x = min(p["x"] for p in points)
        max_x = max(p["x"] for p in points)
        min_z = min(p["y"] for p in points)
        max_z = max(p["y"] for p in points)
        return {"points": points, "min_x": min_x, "max_x": max_x, "min_z": min_z, "max_z": max_z}


simulation_start_service = SimulationStartService()
