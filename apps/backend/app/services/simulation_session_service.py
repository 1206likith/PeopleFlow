"""
Canonical session-oriented simulation orchestration for v3.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
import hashlib
import uuid
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Request

from app.api.contracts.simulation_session_contracts import (
    SimulationControlCommandSchema,
    SimulationSessionConfigSchema,
)
from app.core.config import settings
from app.core.request_context import get_request_actor
from app.services.frame_ingest import ingest_frame
from app.services.simulation_projection_service import SimulationProjectionService
from app.services.simulation_result_repository import get_simulation_result_repository
from app.services.simulation_session_repository import get_simulation_session_repository
from app.services.simulation_session_store import (
    append_session_event,
    clear_session_runtime,
    get_session_analysis,
    get_session_events,
    save_session_analysis,
)
from app.services.simulation_state import simulation_state_manager
from app.services.simulation_store import clear_frames, clear_summary, get_frames, get_latest_frame, save_summary
from app.sim.simulation_kernel import SimulationKernel

logger = logging.getLogger(__name__)


@dataclass
class SessionRuntimeHandle:
    kernel: Optional[SimulationKernel] = None
    task: Optional[asyncio.Task[Any]] = None
    frames: List[Dict[str, Any]] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    previous_frame: Optional[Dict[str, Any]] = None
    last_bottleneck_frame: int = 0


_SESSION_RUNTIMES: Dict[str, SessionRuntimeHandle] = {}


class SimulationSessionService:
    def __init__(self) -> None:
        self.projection = SimulationProjectionService()

    async def create_session(self, request: Request, config: SimulationSessionConfigSchema) -> Dict[str, Any]:
        config_payload = config.model_dump()
        if config_payload.get("seed") is None:
            config_payload["seed"] = self._stable_seed_hint(config_payload)

        now = datetime.now(timezone.utc)
        session_doc = {
            "id": f"session-{uuid.uuid4().hex[:12]}",
            "config": config_payload,
            "state": {
                "status": "draft",
                "connection_state": "idle",
                "started_at": None,
                "updated_at": now,
                "completed_at": None,
                "frame_count": 0,
                "event_count": 0,
                "latest_frame_id": None,
                "latest_timestamp": None,
                "latest_error": None,
            },
            "created_at": now,
            "updated_at": now,
            "analysis_available": False,
            "replay_available": False,
            "status_timeline": [self._timeline_entry("draft", 0.0, {"reason": "session_created"})],
            "provenance": {
                "engine": "peopleflow-simulation-kernel-v3",
                "engine_mode": config_payload.get("mode"),
                "seed": config_payload.get("seed"),
                "created_by": self._actor_id(request),
                "created_path": request.url.path,
                "schema_version": "peopleflow-simulation-session-v3",
            },
        }

        repository = await get_simulation_session_repository()
        await repository.create(session_doc)
        return self._normalize_session_doc(session_doc)

    async def list_sessions(self, *, skip: int = 0, limit: int = 20) -> Dict[str, Any]:
        repository = await get_simulation_session_repository()
        docs = await repository.list(skip=max(0, skip), limit=max(1, min(limit, 200)))
        sessions = [self._normalize_session_doc(doc) for doc in docs]
        return {"sessions": sessions, "total": len(sessions)}

    async def get_session(self, session_id: str) -> Dict[str, Any]:
        repository = await get_simulation_session_repository()
        doc = await repository.get(session_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Simulation session not found")
        normalized = self._normalize_session_doc(doc)
        normalized["recent_events"] = get_session_events(session_id)[-24:]
        return normalized

    async def control_session(
        self,
        request: Request,
        session_id: str,
        command: SimulationControlCommandSchema,
    ) -> Dict[str, Any]:
        repository = await get_simulation_session_repository()
        session_doc = await repository.get(session_id)
        if not session_doc:
            raise HTTPException(status_code=404, detail="Simulation session not found")

        action = command.action
        if action == "start":
            if not simulation_state_manager.can_start(settings.MAX_CONCURRENT_SIMULATIONS):
                raise HTTPException(status_code=429, detail="Simulation capacity reached, try again later")
            try:
                await self._queue_start_runtime(request, session_id, session_doc)
            except Exception as exc:
                logger.exception("Failed to start simulation session %s", session_id)
                await self._mark_start_error(session_id, str(exc))
                raise HTTPException(status_code=409, detail=f"Failed to start simulation session: {exc}") from exc
        elif action == "pause":
            if simulation_state_manager.pause_simulation(session_id):
                await self._transition_state(session_id, "paused", title="Session paused")
        elif action == "resume":
            if simulation_state_manager.resume_simulation(session_id):
                await self._transition_state(session_id, "running", title="Session resumed")
        elif action == "stop":
            if simulation_state_manager.request_stop(session_id):
                await self._transition_state(session_id, "stopping", title="Session stopping")
        elif action == "reset":
            await self._reset_session(session_id)
        else:
            runtime = _SESSION_RUNTIMES.get(session_id)
            if not runtime:
                raise HTTPException(status_code=409, detail="Session is not running")
            runtime.kernel.apply_command(command.model_dump())
            event_type = "exit_closed" if action == "close_exit" else "exit_opened" if action == "open_exit" else "state_change"
            self._record_event(
                session_id,
                event_type,
                float(runtime.kernel.engine.time),
                int(runtime.kernel.engine.frame_id),
                title=action.replace("_", " ").title(),
                message=command.message or f"Applied runtime action: {action}",
                data=command.model_dump(exclude_none=True),
            )

        doc = await repository.get(session_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Simulation session not found")
        normalized = self._normalize_session_doc(doc)
        normalized["recent_events"] = get_session_events(session_id)[-24:]
        return normalized

    async def get_stream_descriptor(self, session_id: str) -> Dict[str, Any]:
        session = await self.get_session(session_id)
        latest_frame = get_latest_frame(session_id)
        return {
            "session_id": session_id,
            "websocket_path": f"/ws/{session_id}",
            "latest_frame": latest_frame,
            "recent_events": get_session_events(session_id)[-40:],
            "connection_state": dict(session.get("state") or {}).get("connection_state", "idle"),
        }

    async def get_analysis(self, session_id: str) -> Dict[str, Any]:
        cached = get_session_analysis(session_id)
        if cached:
            return cached

        session_doc = await self._require_session(session_id)
        frames = get_frames(session_id, limit=4000, skip=0, stride=1)
        events = get_session_events(session_id)
        analysis = self.projection.build_analysis_snapshot(session_doc, frames, events)
        save_session_analysis(session_id, analysis)
        return analysis

    async def get_replay_slice(self, session_id: str, *, offset: int = 0, limit: int = 180) -> Dict[str, Any]:
        await self._require_session(session_id)
        frames = get_frames(session_id, limit=4000, skip=0, stride=1)
        events = get_session_events(session_id)
        return self.projection.build_replay_slice(session_id, frames, events, offset=offset, limit=limit)

    async def _require_session(self, session_id: str) -> Dict[str, Any]:
        repository = await get_simulation_session_repository()
        doc = await repository.get(session_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Simulation session not found")
        return doc

    async def _queue_start_runtime(self, request: Request, session_id: str, session_doc: Dict[str, Any]) -> None:
        existing = _SESSION_RUNTIMES.get(session_id)
        if existing and existing.task and not existing.task.done():
            return

        clear_session_runtime(session_id)
        clear_frames(session_id)
        clear_summary(session_id)
        try:
            result_repository = await get_simulation_result_repository()
            await result_repository.delete_frames(session_id)
        except Exception:
            pass

        runtime = SessionRuntimeHandle()
        _SESSION_RUNTIMES[session_id] = runtime
        await self._transition_state(session_id, "starting", title="Session starting", reset_counters=True)
        runtime.task = asyncio.create_task(
            self._bootstrap_and_run_session(request, session_id),
            name=f"simulation-session-{session_id}",
        )

    async def _bootstrap_and_run_session(self, request: Request, session_id: str) -> None:
        runtime = _SESSION_RUNTIMES.get(session_id)
        if not runtime:
            return

        try:
            session_doc = await self._require_session(session_id)
            config = deepcopy(dict(session_doc.get("config") or {}))
            floor_plan_data = await self._load_floor_plan_data(config)
            kernel = SimulationKernel(session_id, config)
            await asyncio.to_thread(kernel.initialize, floor_plan_data)

            runtime.kernel = kernel
            simulation_state_manager.register_simulation(
                session_id,
                status="running",
                metadata={
                    "user_id": self._actor_id(request),
                    "num_agents": config.get("num_agents"),
                    "emergency_type": config.get("emergency_type"),
                },
            )
            await self._transition_state(session_id, "running", title="Session started", reset_counters=True)

            for hazard in config.get("hazards") or []:
                hazard_data = hazard if isinstance(hazard, dict) else {}
                self._record_event(
                    session_id,
                    "hazard_activation",
                    0.0,
                    0,
                    title="Hazard activated",
                    message=f"{hazard_data.get('type', config.get('emergency_type', 'hazard'))} source active",
                    data=hazard_data,
                )
            for exit_id in config.get("blocked_exits") or []:
                self._record_event(
                    session_id,
                    "exit_closed",
                    0.0,
                    0,
                    title="Exit blocked",
                    message=f"Exit {exit_id} starts blocked for this session.",
                    data={"exit_id": exit_id},
                )

            await self._run_session(session_id)
        except asyncio.CancelledError:
            raise
        except HTTPException as exc:
            await self._mark_start_error(session_id, str(exc.detail))
            _SESSION_RUNTIMES.pop(session_id, None)
        except Exception as exc:
            logger.exception("Simulation session %s failed during startup", session_id)
            await self._mark_start_error(session_id, str(exc))
            _SESSION_RUNTIMES.pop(session_id, None)

    async def _mark_start_error(self, session_id: str, reason: str) -> None:
        simulation_state_manager.mark_completed(session_id, "error")
        await self._transition_state(
            session_id,
            "error",
            title="Session failed to start",
            latest_error=reason,
        )

    async def _run_session(self, session_id: str) -> None:
        repository = await get_simulation_session_repository()
        session_doc = await self._require_session(session_id)
        runtime = _SESSION_RUNTIMES.get(session_id)
        if not runtime or runtime.kernel is None:
            return

        config = dict(session_doc.get("config") or {})
        max_runtime_seconds = float(config.get("max_runtime_seconds") or 180.0)
        dt = 0.2

        try:
            while True:
                if simulation_state_manager.is_stop_requested(session_id):
                    simulation_state_manager.mark_completed(session_id, "stopped")
                    await self._transition_state(session_id, "stopped", title="Session stopped")
                    break

                if simulation_state_manager.is_paused(session_id):
                    await asyncio.sleep(0.1)
                    continue

                raw_frame = await asyncio.to_thread(runtime.kernel.step, dt)
                frame = self.projection.build_frame(
                    session_id,
                    session_doc,
                    raw_frame,
                    previous_frame=runtime.previous_frame,
                )
                runtime.previous_frame = frame
                runtime.frames.append(frame)
                await ingest_frame(session_id, frame, broadcast=True)

                if frame.get("bottlenecks") and (int(frame.get("frame_id") or 0) - runtime.last_bottleneck_frame) >= 12:
                    runtime.last_bottleneck_frame = int(frame.get("frame_id") or 0)
                    self._record_event(
                        session_id,
                        "bottleneck",
                        float(frame.get("timestamp") or 0.0),
                        int(frame.get("frame_id") or 0),
                        title="Bottleneck detected",
                        message="Queue pressure exceeded the live bottleneck threshold.",
                        data={"bottlenecks": frame.get("bottlenecks", [])},
                    )

                if len(runtime.frames) % 5 == 0 or runtime.kernel.is_complete():
                    analysis = self.projection.build_analysis_snapshot(session_doc, runtime.frames, runtime.events)
                    save_session_analysis(session_id, analysis)
                    save_summary(
                        session_id,
                        {
                            "simulation_id": session_id,
                            "timestamp": frame.get("timestamp"),
                            "total_agents": analysis.get("total_agents"),
                            "evacuated": analysis.get("evacuated"),
                            "total_time": analysis.get("simulation_time"),
                            "frames_count": len(runtime.frames),
                            "final_stats": dict(frame.get("stats") or {}),
                            "source": "simulation_session_v3",
                        },
                    )
                    await repository.update_fields(
                        session_id,
                        {
                            "analysis_available": True,
                            "replay_available": True,
                            "state": {
                                **dict((await repository.get(session_id) or {}).get("state") or {}),
                                "status": simulation_state_manager.get_status(session_id) or "running",
                                "connection_state": "streaming",
                                "updated_at": datetime.now(timezone.utc),
                                "frame_count": len(runtime.frames),
                                "event_count": len(runtime.events),
                                "latest_frame_id": frame.get("frame_id"),
                                "latest_timestamp": frame.get("timestamp"),
                            },
                        },
                    )

                if runtime.kernel.is_complete():
                    simulation_state_manager.mark_completed(session_id, "completed")
                    await self._transition_state(session_id, "completed", title="Session completed")
                    self._record_event(
                        session_id,
                        "run_completed",
                        float(frame.get("timestamp") or 0.0),
                        int(frame.get("frame_id") or 0),
                        title="Simulation complete",
                        message="Evacuation reached completion criteria.",
                        data={"completion_percentage": dict(frame.get("stats") or {}).get("completion_percentage")},
                    )
                    break

                if float(frame.get("timestamp") or 0.0) >= max_runtime_seconds:
                    simulation_state_manager.mark_completed(session_id, "time_limit")
                    await self._transition_state(session_id, "time_limit", title="Session reached time limit")
                    break

                if config.get("mode") == "studio":
                    await asyncio.sleep(0.05)
                else:
                    await asyncio.sleep(0)

        except asyncio.CancelledError:
            simulation_state_manager.mark_completed(session_id, "stopped")
            await self._transition_state(session_id, "stopped", title="Session cancelled")
            raise
        except Exception as exc:
            logger.exception("Simulation session %s failed", session_id)
            simulation_state_manager.mark_completed(session_id, "error")
            self._record_event(
                session_id,
                "run_error",
                float(getattr(runtime.kernel.engine, "time", 0.0)),
                int(getattr(runtime.kernel.engine, "frame_id", 0)),
                title="Simulation error",
                message=str(exc),
                data={"error_type": type(exc).__name__},
                severity="error",
            )
            await self._transition_state(session_id, "error", title="Session failed", latest_error=str(exc))
        finally:
            latest = runtime.frames[-1] if runtime.frames else get_latest_frame(session_id)
            if latest:
                analysis = self.projection.build_analysis_snapshot(session_doc, runtime.frames or [latest], runtime.events)
                save_session_analysis(session_id, analysis)
                save_summary(
                    session_id,
                    {
                        "simulation_id": session_id,
                        "timestamp": latest.get("timestamp"),
                        "total_agents": analysis.get("total_agents"),
                        "evacuated": analysis.get("evacuated"),
                        "total_time": analysis.get("simulation_time"),
                        "frames_count": analysis.get("frame_count"),
                        "final_stats": dict(latest.get("stats") or {}),
                        "source": "simulation_session_v3",
                    },
                )
                try:
                    final_doc = await repository.get(session_id)
                    await repository.update_fields(
                        session_id,
                        {
                            "analysis_available": True,
                            "replay_available": True,
                            "state": {
                                **dict((final_doc or {}).get("state") or {}),
                                "frame_count": len(runtime.frames),
                                "event_count": len(runtime.events),
                                "latest_frame_id": latest.get("frame_id"),
                                "latest_timestamp": latest.get("timestamp"),
                                "updated_at": datetime.now(timezone.utc),
                            },
                        },
                    )
                except Exception:
                    logger.warning("Failed to persist final session metadata for %s", session_id)
            _SESSION_RUNTIMES.pop(session_id, None)

    async def _reset_session(self, session_id: str) -> None:
        runtime = _SESSION_RUNTIMES.get(session_id)
        if runtime and runtime.task and not runtime.task.done():
            simulation_state_manager.request_stop(session_id)
            runtime.task.cancel()
            try:
                await runtime.task
            except BaseException:
                pass
        _SESSION_RUNTIMES.pop(session_id, None)

        clear_session_runtime(session_id)
        clear_frames(session_id)
        clear_summary(session_id)
        try:
            result_repository = await get_simulation_result_repository()
            await result_repository.delete_frames(session_id)
        except Exception:
            pass

        repository = await get_simulation_session_repository()
        await repository.update_fields(
            session_id,
            {
                "analysis_available": False,
                "replay_available": False,
                "state": self._state_payload(status="draft", frame_count=0, event_count=0, latest_frame_id=None, latest_timestamp=None),
                "status_timeline": [self._timeline_entry("draft", 0.0, {"reason": "session_reset"})],
            },
            upsert=False,
        )

    async def _load_floor_plan_data(self, config: Dict[str, Any]) -> Dict[str, Any]:
        from app.services.floorplan_loader import load_floor_plan_data

        floor_plan_ref = config.get("floor_plan_ref")
        floor_number = config.get("floor_number")
        floor_plan_data: Dict[str, Any] = {}
        exits: List[Dict[str, Any]] = []

        if floor_plan_ref:
            floor_plan_data, exits = await load_floor_plan_data(
                floor_plan_ref,
                floor_number,
                config.get("exits"),
                allow_inferred_exits=False,
            )

        snapshot = config.get("floor_plan_snapshot") or {}
        if snapshot:
            merged = dict(floor_plan_data or {})
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
                "hazards",
                "pipeline",
                "processing_metadata",
            ):
                if snapshot.get(key):
                    merged[key] = snapshot.get(key)
            snapshot_exits = list(snapshot.get("exits") or [])
            if snapshot_exits:
                exits = snapshot_exits
            floor_plan_data = merged

        if not floor_plan_data and not snapshot:
            raise HTTPException(status_code=422, detail="Session requires floor_plan_ref or floor_plan_snapshot")

        if exits and not floor_plan_data.get("exits"):
            floor_plan_data["exits"] = exits

        return floor_plan_data

    async def _transition_state(
        self,
        session_id: str,
        status: str,
        *,
        title: str,
        latest_error: Optional[str] = None,
        reset_counters: bool = False,
    ) -> None:
        repository = await get_simulation_session_repository()
        existing = await repository.get(session_id)
        if not existing:
            return
        state = dict(existing.get("state") or {})
        now = datetime.now(timezone.utc)
        if reset_counters:
            state["frame_count"] = 0
            state["event_count"] = len(get_session_events(session_id))
            state["latest_frame_id"] = None
            state["latest_timestamp"] = None
        state.update(
            {
                "status": status,
                "connection_state": "connecting" if status == "starting" else "streaming" if status in {"running", "paused", "stopping"} else "idle",
                "updated_at": now,
                "latest_error": latest_error,
            }
        )
        if status == "running" and not state.get("started_at"):
            state["started_at"] = now
        if status in {"completed", "stopped", "error", "time_limit"}:
            state["completed_at"] = now

        timeline = list(existing.get("status_timeline") or [])
        last_timestamp = float(dict(existing.get("state") or {}).get("latest_timestamp") or 0.0)
        timeline.append(self._timeline_entry(status, last_timestamp, {"title": title}))
        await repository.update_fields(session_id, {"state": state, "status_timeline": timeline})
        self._record_event(
            session_id,
            "state_change",
            last_timestamp,
            int(state.get("latest_frame_id") or 0),
            title=title,
            message=f"Session state is now {status}.",
            data={"status": status},
        )

    def _record_event(
        self,
        session_id: str,
        event_type: str,
        timestamp: float,
        frame_id: int,
        *,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        severity: str = "info",
    ) -> None:
        event = {
            "event_id": f"evt-{uuid.uuid4().hex[:10]}",
            "session_id": session_id,
            "type": event_type,
            "timestamp": float(timestamp),
            "frame_id": int(frame_id) if frame_id is not None else None,
            "severity": severity,
            "title": title,
            "message": message,
            "data": data or {},
        }
        append_session_event(session_id, event)
        runtime = _SESSION_RUNTIMES.get(session_id)
        if runtime is not None:
            runtime.events.append(event)

    def _normalize_session_doc(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        normalized = deepcopy(doc)
        if normalized.get("_id") is not None:
            normalized["_id"] = str(normalized["_id"])
        normalized["id"] = str(normalized.get("id") or normalized.get("_id") or "")
        normalized["analysis_available"] = bool(normalized.get("analysis_available"))
        normalized["replay_available"] = bool(normalized.get("replay_available"))
        return normalized

    def _actor_id(self, request: Request) -> str:
        actor = get_request_actor(request)
        return str(actor.get("id") or "web-dashboard")

    def _stable_seed_hint(self, config_payload: Dict[str, Any]) -> int:
        source = f"{config_payload.get('floor_plan_ref')}:{config_payload.get('emergency_type')}:{config_payload.get('mode')}:{config_payload.get('num_agents')}"
        return int(hashlib.sha256(source.encode("utf-8")).hexdigest()[:8], 16) % 1_000_000

    def _timeline_entry(self, status: str, timestamp: float, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {
            "status": status,
            "timestamp": float(timestamp),
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
        }

    def _state_payload(
        self,
        *,
        status: str,
        frame_count: int,
        event_count: int,
        latest_frame_id: Optional[Any],
        latest_timestamp: Optional[Any],
        latest_error: Optional[str] = None,
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        return {
            "status": status,
            "connection_state": "connecting" if status == "starting" else "streaming" if status in {"running", "paused", "stopping"} else "idle",
            "started_at": None,
            "updated_at": now,
            "completed_at": now if status in {"completed", "stopped", "error", "time_limit"} else None,
            "frame_count": int(frame_count),
            "event_count": int(event_count),
            "latest_frame_id": latest_frame_id,
            "latest_timestamp": latest_timestamp,
            "latest_error": latest_error,
        }


simulation_session_service = SimulationSessionService()
