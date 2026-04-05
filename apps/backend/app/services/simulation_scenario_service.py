"""
Application service for multi-run scenario orchestration.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, Optional

from fastapi import HTTPException, Request
from fastapi.encoders import jsonable_encoder

from app.core.validation import SimulationConfigSchema
from app.services.audit_log import record_event
from app.services.idempotency import (
    build_idempotency_key,
    build_replay_response,
    get_cached_response,
    store_response,
)
from app.services.simulation_repository import get_simulation_repository


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


SimulationStarter = Callable[[Request, SimulationConfigSchema, dict], Awaitable[Any]]


class SimulationScenarioApplicationService:
    async def start_scenario(
        self,
        request: Request,
        scenario: Any,
        current_user: dict,
        *,
        start_simulation_fn: SimulationStarter,
    ) -> Dict[str, Any]:
        if not scenario.runs:
            raise HTTPException(status_code=400, detail="Scenario requires at least one run")

        user_id = str(current_user.get("_id", current_user.get("id", "demo_user")))
        raw_idempotency_key = request.headers.get("Idempotency-Key")
        idempotency_key = build_idempotency_key(request, user_id)
        if idempotency_key:
            cached = get_cached_response(idempotency_key)
            if cached:
                return build_replay_response(cached)

        base_data = jsonable_encoder(scenario.base_config) if scenario.base_config else {}
        scenario_id = f"scenario-{uuid.uuid4().hex[:10]}"
        created_at = datetime.now(timezone.utc)
        simulations = []
        request.state.skip_idempotency = True

        for idx, run in enumerate(scenario.runs, start=1):
            config = self._build_run_config(base_data, run)
            response = await start_simulation_fn(request, config, current_user)
            simulation_id = response.id
            simulations.append(
                {
                    "run_index": idx,
                    "simulation_id": simulation_id,
                    "floor_plan_id": run.floor_plan_id,
                    "floor_number": run.floor_number,
                }
            )
            await self._attach_scenario_metadata(
                simulation_id=simulation_id,
                scenario_id=scenario_id,
                scenario_name=scenario.name,
                run_index=idx,
            )

        response_payload = {
            "scenario_id": scenario_id,
            "scenario_name": scenario.name,
            "created_at": created_at,
            "runs": len(simulations),
            "simulations": simulations,
        }

        _safe_audit(
            "simulation_scenario_started",
            actor=user_id,
            metadata={
                "scenario_id": scenario_id,
                "scenario_name": scenario.name,
                "runs": len(simulations),
            },
        )

        if idempotency_key:
            store_response(
                idempotency_key,
                200,
                response_payload,
                {"Idempotency-Key": raw_idempotency_key or idempotency_key},
                {"path": request.url.path},
            )

        return response_payload

    def _build_run_config(self, base_data: Dict[str, Any], run: Any) -> SimulationConfigSchema:
        data = dict(base_data)
        data["floor_plan_id"] = run.floor_plan_id

        def _maybe_assign(key: str, value: Any) -> None:
            if value is not None:
                data[key] = value

        _maybe_assign("floor_number", run.floor_number)
        _maybe_assign("num_agents", run.num_agents)
        _maybe_assign("emergency_type", run.emergency_type)
        _maybe_assign("panic_level", run.panic_level)
        if run.exits:
            data["exits"] = run.exits
        if run.hazards:
            data["hazards"] = run.hazards
        if run.agent_profiles:
            data["agent_profiles"] = run.agent_profiles
        if run.blocked_exits:
            data["blocked_exits"] = run.blocked_exits
        if run.parameter_overrides:
            data["parameter_overrides"] = run.parameter_overrides
        if run.ablation is not None:
            data["ablation"] = run.ablation
        _maybe_assign("max_iterations", run.max_iterations)
        _maybe_assign("realtime", run.realtime)
        _maybe_assign("seed", run.seed)
        if run.tags:
            data["tags"] = run.tags
        _maybe_assign("notes", run.notes)
        _maybe_assign("label", run.label)
        _maybe_assign("priority", run.priority)
        _maybe_assign("record_frames", run.record_frames)
        _maybe_assign("frame_stride", run.frame_stride)
        _maybe_assign("store_agents", run.store_agents)
        _maybe_assign("store_bottlenecks", run.store_bottlenecks)
        _maybe_assign("store_walls", run.store_walls)
        _maybe_assign("store_exits", run.store_exits)
        _maybe_assign("store_obstacles", run.store_obstacles)
        _maybe_assign("store_hazards", run.store_hazards)
        _maybe_assign("max_runtime_seconds", run.max_runtime_seconds)

        if data.get("num_agents") is None:
            raise HTTPException(status_code=400, detail="num_agents required for each scenario run")
        if data.get("panic_level") is None:
            data["panic_level"] = 0.5

        return SimulationConfigSchema(**data)

    async def _attach_scenario_metadata(
        self,
        *,
        simulation_id: str,
        scenario_id: str,
        scenario_name: Optional[str],
        run_index: int,
    ) -> None:
        try:
            repository = await get_simulation_repository()
            await repository.update_fields(
                simulation_id,
                {"scenario_id": scenario_id, "scenario_name": scenario_name, "scenario_run": run_index},
                upsert=simulation_id.startswith("mock-"),
            )
        except Exception:
            pass


simulation_scenario_application_service = SimulationScenarioApplicationService()
