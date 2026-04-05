"""
Read-side runtime query service for simulation summaries, frames, analytics, and exports.
"""
from __future__ import annotations

import csv
import io
from dataclasses import asdict
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from app.services.simulation_mock_runtime_service import (
    _build_mock_frame,
    _build_mock_frames,
    _build_mock_metrics,
    _build_mock_summary,
    _get_mock_runtime,
    _is_demo_like_simulation_id,
)
from app.services.simulation_repository import get_simulation_repository
from app.services.simulation_result_repository import get_simulation_result_repository


class SimulationRuntimeQueryService:
    async def get_summary(self, simulation_id: str) -> Dict[str, Any]:
        from app.services.simulation_store import get_latest_frame as get_cached_latest_frame
        from app.services.simulation_store import get_summary

        summary = get_summary(simulation_id)
        if summary:
            return summary

        latest_cached = get_cached_latest_frame(simulation_id)
        if latest_cached:
            stats = latest_cached.get("stats", {}) or {}
            return {
                "simulation_id": simulation_id,
                "timestamp": latest_cached.get("timestamp"),
                "total_agents": stats.get("total_agents", 0),
                "evacuated": stats.get("evacuated", 0),
                "total_time": stats.get("total_time", latest_cached.get("timestamp", 0)),
                "frames_count": int(max(1, latest_cached.get("frame_id", 1) or 1)),
                "final_stats": stats,
                "source": "in_memory",
            }

        if _is_demo_like_simulation_id(simulation_id):
            return _build_mock_summary(simulation_id)

        try:
            repository = await get_simulation_result_repository()
            frame = await repository.get_latest_frame(simulation_id)
            if not frame:
                raise HTTPException(status_code=404, detail="Simulation summary not found")
            return {
                "simulation_id": simulation_id,
                "timestamp": frame.get("timestamp"),
                "final_stats": frame.get("stats"),
            }
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=404, detail="Simulation summary not found")

    async def get_frames(
        self,
        simulation_id: str,
        *,
        limit: int = 200,
        skip: int = 0,
        stride: int = 1,
        from_ts: Optional[float] = None,
        to_ts: Optional[float] = None,
    ) -> Dict[str, Any]:
        limit = max(1, min(limit, 5000))
        skip = max(0, skip)
        stride = max(1, min(stride, 100))
        from app.services.simulation_store import get_frames as get_cached_frames

        def _cached_payload() -> Optional[Dict[str, Any]]:
            cached = get_cached_frames(
                simulation_id,
                limit=limit,
                skip=skip,
                stride=stride,
                from_ts=from_ts,
                to_ts=to_ts,
            )
            if not cached:
                return None
            return {"frames": cached, "count": len(cached)}

        if _is_demo_like_simulation_id(simulation_id):
            cached_payload = _cached_payload()
            if cached_payload:
                return cached_payload

            frames = _build_mock_frames(simulation_id, limit=limit, stride=stride)
            if from_ts is not None or to_ts is not None:
                filtered_frames = []
                for frame in frames:
                    try:
                        ts = float(frame.get("timestamp"))
                    except (TypeError, ValueError):
                        filtered_frames.append(frame)
                        continue
                    if from_ts is not None and ts < float(from_ts):
                        continue
                    if to_ts is not None and ts > float(to_ts):
                        continue
                    filtered_frames.append(frame)
                frames = filtered_frames
            if skip > 0:
                frames = frames[skip:]
            return {"frames": frames, "count": len(frames)}

        try:
            repository = await get_simulation_result_repository()
            frames = await repository.list_frames(
                simulation_id,
                limit=limit,
                skip=skip,
                from_ts=from_ts,
                to_ts=to_ts,
            )
            if stride > 1:
                frames = frames[::stride]
            if frames:
                return {"frames": frames, "count": len(frames)}
            cached_payload = _cached_payload()
            if cached_payload:
                return cached_payload
            return {"frames": frames, "count": len(frames)}
        except Exception:
            cached_payload = _cached_payload()
            if cached_payload:
                return cached_payload
            raise HTTPException(status_code=500, detail="Failed to fetch frames")

    async def get_latest_frame(self, simulation_id: str) -> Dict[str, Any]:
        from app.services.simulation_store import get_latest_frame as get_cached_latest_frame

        if _is_demo_like_simulation_id(simulation_id):
            cached = get_cached_latest_frame(simulation_id)
            if cached:
                return cached
            return _build_mock_frame(simulation_id)
        try:
            repository = await get_simulation_result_repository()
            frame = await repository.get_latest_frame(simulation_id)
            if not frame:
                cached = get_cached_latest_frame(simulation_id)
                if cached:
                    return cached
                raise HTTPException(status_code=404, detail="No frames available")
            return frame
        except HTTPException:
            raise
        except Exception:
            cached = get_cached_latest_frame(simulation_id)
            if cached:
                return cached
            raise HTTPException(status_code=500, detail="Failed to fetch latest frame")

    async def export_frames_csv(self, simulation_id: str, *, limit: int = 2000, stride: int = 1) -> str:
        frames_payload = await self.get_frames(
            simulation_id=simulation_id,
            limit=limit,
            skip=0,
            stride=stride,
        )
        frames = frames_payload.get("frames", [])

        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "timestamp",
                "evacuated",
                "remaining",
                "completion_percentage",
                "bottleneck_count",
                "blocked_exit_count",
                "active_hazard_count",
            ],
        )
        writer.writeheader()
        for frame in frames:
            stats = frame.get("stats", {}) or {}
            hazard_state = frame.get("hazard_state", {}) or {}
            writer.writerow(
                {
                    "timestamp": frame.get("timestamp"),
                    "evacuated": stats.get("evacuated"),
                    "remaining": stats.get("remaining"),
                    "completion_percentage": stats.get("completion_percentage"),
                    "bottleneck_count": len(frame.get("bottlenecks", []) or []),
                    "blocked_exit_count": len(hazard_state.get("blocked_exits", []) or []),
                    "active_hazard_count": len(hazard_state.get("active", []) or []),
                }
            )
        return output.getvalue()

    async def get_timeline(self, simulation_id: str, *, stride: int = 5) -> Dict[str, Any]:
        frames_payload = await self.get_frames(
            simulation_id=simulation_id,
            limit=5000,
            skip=0,
            stride=stride,
        )
        frames = frames_payload.get("frames", [])
        timeline = []
        for frame in frames:
            stats = frame.get("stats", {}) or {}
            timeline.append(
                {
                    "timestamp": frame.get("timestamp"),
                    "evacuated": stats.get("evacuated"),
                    "remaining": stats.get("remaining"),
                    "completion_percentage": stats.get("completion_percentage"),
                }
            )
        return {"points": timeline, "count": len(timeline)}

    async def get_agents(self, simulation_id: str, *, status: Optional[str] = None) -> Dict[str, Any]:
        latest = await self.get_latest_frame(simulation_id)
        agents = latest.get("agents", []) or []
        if status:
            agents = [a for a in agents if a.get("status") == status]
        return {"agents": agents, "count": len(agents)}

    async def get_hazards(self, simulation_id: str) -> Dict[str, Any]:
        latest = await self.get_latest_frame(simulation_id)
        hazards = latest.get("hazards", []) or []
        hazard_state = latest.get("hazard_state", {}) or {}
        return {"hazards": hazards, "hazard_state": hazard_state}

    async def get_exit_usage(self, simulation_id: str) -> Dict[str, Any]:
        from app.services.simulation_store import get_summary

        summary = get_summary(simulation_id)
        if summary:
            return {
                "exit_usage": summary.get("final_stats", {}).get("exit_usage", {}),
                "source": "summary",
            }
        latest = await self.get_latest_frame(simulation_id)
        exit_counts = latest.get("exit_evac_counts") or []
        if exit_counts:
            usage = {item.get("exit_id"): item.get("count", 0) for item in exit_counts if item.get("exit_id")}
            return {"exit_usage": usage, "source": "latest_frame"}
        stats = latest.get("stats", {}) or {}
        if stats.get("exit_usage"):
            return {"exit_usage": stats.get("exit_usage", {}), "source": "latest_frame"}
        exit_usage = latest.get("exit_usage") or []
        if exit_usage:
            queue = {item.get("exit_id"): item.get("queue_length", 0) for item in exit_usage if item.get("exit_id")}
            return {"exit_usage": queue, "source": "latest_frame_queue"}
        return {"exit_usage": {}, "source": "latest_frame"}

    async def get_profile_counts(self, simulation_id: str) -> Dict[str, Any]:
        from app.services.simulation_store import get_summary

        summary = get_summary(simulation_id)
        if summary:
            return {
                "profile_counts": summary.get("final_stats", {}).get("profile_counts", {}),
                "source": "summary",
            }
        latest = await self.get_latest_frame(simulation_id)
        profile_counts = latest.get("profile_counts") or []
        if profile_counts:
            counts = {item.get("profile_id"): item.get("count", 0) for item in profile_counts if item.get("profile_id")}
            return {"profile_counts": counts, "source": "latest_frame"}
        stats = latest.get("stats", {}) or {}
        return {"profile_counts": stats.get("profile_counts", {}), "source": "latest_frame"}

    async def get_metrics(self, simulation_id: str, *, limit: int = 1000, stride: int = 1) -> Dict[str, Any]:
        limit = max(1, min(limit, 10000))
        stride = max(1, min(stride, 100))
        from app.services.simulation_store import get_frames as get_cached_frames

        if _is_demo_like_simulation_id(simulation_id):
            cached_frames = get_cached_frames(simulation_id, limit=limit, stride=stride)
            if cached_frames:
                from app.services.metrics_engine import MetricsEngine

                engine = MetricsEngine()
                for frame in cached_frames:
                    engine.add_frame(frame)
                metrics = engine.calculate_metrics()
                return {
                    "simulation_id": simulation_id,
                    "frame_count": len(cached_frames),
                    "metrics": asdict(metrics),
                    "source": "in_memory",
                }
            return _build_mock_metrics(simulation_id)

        try:
            repository = await get_simulation_result_repository()
            frames = await repository.list_frames(
                simulation_id,
                limit=limit,
                skip=0,
                from_ts=None,
                to_ts=None,
            )
            if not frames:
                raise HTTPException(status_code=404, detail="No frames available for metrics")
            frames = frames[::stride]

            from app.services.metrics_engine import MetricsEngine

            engine = MetricsEngine()
            for frame in frames:
                engine.add_frame(frame)
            metrics = engine.calculate_metrics()

            return {
                "simulation_id": simulation_id,
                "frame_count": len(frames),
                "metrics": asdict(metrics),
            }
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to calculate metrics")

    async def get_survival_score(self, simulation_id: str, *, disaster_type: Optional[str] = None) -> Dict[str, Any]:
        if _is_demo_like_simulation_id(simulation_id):
            from app.services.simulation_store import get_latest_frame as get_cached_latest_frame

            latest = get_cached_latest_frame(simulation_id)
            if latest:
                if not disaster_type:
                    runtime = _get_mock_runtime(simulation_id)
                    disaster_type = runtime.get("emergency_type") or "fire"

                agents = latest.get("agents", [])
                exits = latest.get("exits", [])
                bottlenecks = latest.get("bottlenecks", [])
                simulation_data = {
                    "total_time": latest.get("timestamp", 0.0),
                    "num_agents": len(agents),
                }

                from app.services.survival_score import survival_score_engine

                score = survival_score_engine.calculate_score(
                    simulation_data,
                    agents,
                    exits,
                    bottlenecks,
                    disaster_type or "fire",
                )

                return {
                    "total_score": score.total_score,
                    "grade": score.grade,
                    "component_scores": {
                        "evacuation_time": score.evacuation_time_score,
                        "exit_capacity": score.exit_capacity_score,
                        "bottleneck": score.bottleneck_score,
                        "disaster_resilience": score.disaster_resilience_score,
                        "accessibility": score.accessibility_score,
                    },
                    "factors": score.factors,
                    "recommendations": score.recommendations,
                    "source": "in_memory",
                }

            metrics = _build_mock_metrics(simulation_id)
            return {
                "total_score": metrics.get("total_score"),
                "grade": metrics.get("grade"),
                "component_scores": metrics.get("component_scores", {}),
                "factors": metrics.get("factors", {}),
                "recommendations": metrics.get("recommendations", []),
            }

        try:
            result_repository = await get_simulation_result_repository()
            frame = await result_repository.get_latest_frame(simulation_id)
            if not frame:
                raise HTTPException(status_code=404, detail="No frames available for survival score")

            if not disaster_type:
                try:
                    simulation_repository = await get_simulation_repository()
                    sim_doc = await simulation_repository.get(simulation_id)
                    disaster_type = sim_doc.get("emergency_type") if sim_doc else "fire"
                except Exception:
                    disaster_type = "fire"

            agents = frame.get("agents", [])
            exits = frame.get("exits", [])
            bottlenecks = frame.get("bottlenecks", [])
            simulation_data = {
                "total_time": frame.get("timestamp", 0.0),
                "num_agents": len(agents),
            }

            from app.services.survival_score import survival_score_engine

            score = survival_score_engine.calculate_score(
                simulation_data,
                agents,
                exits,
                bottlenecks,
                disaster_type or "fire",
            )

            return {
                "total_score": score.total_score,
                "grade": score.grade,
                "component_scores": {
                    "evacuation_time": score.evacuation_time_score,
                    "exit_capacity": score.exit_capacity_score,
                    "bottleneck": score.bottleneck_score,
                    "disaster_resilience": score.disaster_resilience_score,
                    "accessibility": score.accessibility_score,
                },
                "factors": score.factors,
                "recommendations": score.recommendations,
            }
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to calculate survival score")


simulation_runtime_query_service = SimulationRuntimeQueryService()
