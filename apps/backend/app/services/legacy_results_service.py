"""
Compatibility service for legacy `/results/*` routes.
"""
from __future__ import annotations

from typing import Any, Dict, List

from fastapi import HTTPException

from app.core.config import settings
from app.services.simulation_mock_runtime_service import _build_mock_summary
from app.services.simulation_repository import get_simulation_repository
from app.services.simulation_result_repository import get_simulation_result_repository


class LegacyResultsService:
    async def get_frames(self, simulation_id: str, *, skip: int, limit: int) -> Dict[str, Any]:
        if simulation_id.startswith("mock-"):
            if not settings.IS_DEMO_MODE:
                raise HTTPException(status_code=404, detail="Simulation not found")
            return {"frames": [], "total": 0}

        simulation_repository = await get_simulation_repository()
        simulation = await simulation_repository.get(simulation_id)
        if not simulation:
            if not settings.IS_DEMO_MODE:
                raise HTTPException(status_code=503, detail="Database unavailable")
            return {"frames": [], "total": 0}

        result_repository = await get_simulation_result_repository()
        frames = await result_repository.list_frames(
            simulation_id,
            limit=limit,
            skip=skip,
            from_ts=None,
            to_ts=None,
        )
        return {"frames": frames, "total": len(frames)}

    async def get_summary(self, simulation_id: str) -> Dict[str, Any]:
        if simulation_id.startswith("demo-"):
            if not settings.IS_DEMO_MODE:
                raise HTTPException(status_code=404, detail="Simulation not found")
            evacuated = 95 if "1" in simulation_id else (190 if "2" in simulation_id else 145)
            total_time = 120 if "1" in simulation_id else (180 if "2" in simulation_id else 95)
            return {
                "simulation_id": simulation_id,
                "total_agents": 100 if "1" in simulation_id else (200 if "2" in simulation_id else 150),
                "evacuated": evacuated,
                "total_time": total_time,
                "bottlenecks": [],
                "frames_count": 0,
            }

        if simulation_id.startswith("mock-"):
            if not settings.IS_DEMO_MODE:
                raise HTTPException(status_code=404, detail="Simulation not found")
            from app.services.simulation_store import get_latest_frame, get_summary

            cached_summary = get_summary(simulation_id)
            if cached_summary:
                final_stats = cached_summary.get("final_stats", {}) or {}
                return {
                    "simulation_id": simulation_id,
                    "total_agents": int(cached_summary.get("total_agents", 0) or 0),
                    "evacuated": int(cached_summary.get("evacuated", 0) or 0),
                    "total_time": float(cached_summary.get("total_time", 0) or 0),
                    "bottlenecks": [],
                    "frames_count": int(cached_summary.get("frames_count", 0) or 0),
                    "remaining": int(final_stats.get("remaining", 0) or 0),
                }
            latest_frame = get_latest_frame(simulation_id)
            if latest_frame:
                stats = latest_frame.get("stats", {}) or {}
                return {
                    "simulation_id": simulation_id,
                    "total_agents": int(stats.get("total_agents", 0) or 0),
                    "evacuated": int(stats.get("evacuated", 0) or 0),
                    "total_time": float(stats.get("total_time", latest_frame.get("timestamp", 0)) or 0),
                    "bottlenecks": list(latest_frame.get("bottlenecks", []) or []),
                    "frames_count": int(max(1, latest_frame.get("frame_id", 1) or 1)),
                }
            mock_summary = _build_mock_summary(simulation_id)
            return {
                "simulation_id": simulation_id,
                "total_agents": int(mock_summary.get("total_agents", 0) or 0),
                "evacuated": int(mock_summary.get("evacuated", 0) or 0),
                "total_time": float(mock_summary.get("total_time", 0) or 0),
                "bottlenecks": [],
                "frames_count": int(mock_summary.get("frames_count", 0) or 0),
            }

        simulation_repository = await get_simulation_repository()
        simulation = await simulation_repository.get(simulation_id)
        if not simulation:
            if not settings.IS_DEMO_MODE:
                raise HTTPException(status_code=503, detail="Database unavailable")
            raise HTTPException(status_code=404, detail="Simulation not found")

        result_repository = await get_simulation_result_repository()
        frames = await result_repository.list_frames(
            simulation_id,
            limit=None,
            skip=0,
            from_ts=None,
            to_ts=None,
        )
        if not frames:
            return {
                "simulation_id": simulation_id,
                "total_agents": simulation.get("num_agents", 0),
                "evacuated": 0,
                "total_time": 0,
                "bottlenecks": [],
            }

        last_frame = frames[-1]
        evacuated = sum(1 for agent in last_frame.get("agents", []) if agent.get("status") == "evacuated")
        total_time = last_frame.get("timestamp", 0)

        all_bottlenecks: List[Dict[str, Any]] = []
        for frame in frames:
            all_bottlenecks.extend(frame.get("bottlenecks", []))

        return {
            "simulation_id": simulation_id,
            "total_agents": simulation.get("num_agents", 0),
            "evacuated": evacuated,
            "total_time": total_time,
            "bottlenecks": all_bottlenecks,
            "frames_count": len(frames),
        }


legacy_results_service = LegacyResultsService()
