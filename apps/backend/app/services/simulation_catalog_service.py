"""
Catalog and metadata service for simulation records.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import HTTPException

from app.core.config import settings
from app.services.simulation_mock_runtime_service import (
    _build_mock_summary,
    _get_mock_runtime,
    _is_demo_like_simulation_id,
    list_mock_runtime_entries,
)
from app.services.simulation_repository import get_simulation_repository

logger = logging.getLogger(__name__)


class SimulationCatalogService:
    async def _fetch_simulation_doc(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        repository = await get_simulation_repository()
        return await repository.get(simulation_id)

    @staticmethod
    def _normalize_simulation_doc(simulation: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(simulation)
        if normalized.get("_id") is not None:
            normalized["id"] = str(normalized["_id"])
            del normalized["_id"]
        return normalized

    async def get_simulation(self, simulation_id: str) -> Dict[str, Any]:
        if _is_demo_like_simulation_id(simulation_id):
            persisted = await self._fetch_simulation_doc(simulation_id)
            runtime = _get_mock_runtime(simulation_id)
            elapsed = max(0.0, time.time() - float(runtime.get("created_ts", time.time())))
            duration = float(runtime.get("duration_seconds", 120.0))
            status = "completed" if elapsed >= duration else "running"
            runtime_view = {
                "id": simulation_id,
                "tenant_id": "global",
                "status": status,
                "num_agents": int(runtime.get("num_agents", 100)),
                "emergency_type": runtime.get("emergency_type", "fire"),
                "created_at": datetime.fromtimestamp(
                    float(runtime.get("created_ts", time.time())),
                    timezone.utc,
                ).isoformat(),
                "floor_number": runtime.get("floor_number", 1),
            }
            if persisted:
                normalized = self._normalize_simulation_doc(persisted)
                for key, value in runtime_view.items():
                    normalized[key] = value if key in {"status", "num_agents", "emergency_type", "created_at", "floor_number"} else normalized.get(key, value)
                normalized.setdefault("id", simulation_id)
                return normalized
            return runtime_view

        try:
            simulation = await self._fetch_simulation_doc(simulation_id)
            if not simulation:
                raise HTTPException(status_code=404, detail="Simulation not found")
            return self._normalize_simulation_doc(simulation)
        except HTTPException:
            raise
        except Exception as exc:
            logger.warning("Database unavailable for get_simulation: %s", exc)
            raise HTTPException(status_code=404, detail="Simulation not found")

    async def update_metadata(self, simulation_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        if not updates:
            raise HTTPException(status_code=400, detail="No metadata updates provided")

        try:
            repository = await get_simulation_repository()
            updated = await repository.update_fields(
                simulation_id,
                updates,
                upsert=_is_demo_like_simulation_id(simulation_id),
            )
            if not updated:
                raise HTTPException(status_code=404, detail="Simulation not found")
            response_updates = dict(updates)
            response_updates["updated_at"] = updated.get("updated_at")
            response: Dict[str, Any] = {"simulation_id": simulation_id, "updates": response_updates}
            if _is_demo_like_simulation_id(simulation_id):
                response["status"] = "mock"
            return response
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to update metadata")

    async def list_simulations(self, *, skip: int, limit: int) -> Dict[str, Any]:
        if settings.IS_DEMO_MODE:
            return await self._build_demo_list(skip=skip, limit=limit)

        try:
            repository = await get_simulation_repository()
            simulations = await repository.list(skip=skip, limit=limit)
            normalized = [self._normalize_simulation_doc(sim) for sim in simulations]
            return {"simulations": normalized, "total": len(normalized)}
        except Exception as exc:
            logger.warning("Database unavailable for list_simulations: %s", exc)
            if not settings.IS_DEMO_MODE:
                raise HTTPException(status_code=503, detail="Database unavailable")
            return await self._build_demo_list(skip=skip, limit=limit)

    async def _build_demo_list(self, *, skip: int, limit: int) -> Dict[str, Any]:
        from app.services.simulation_store import get_summary

        repository = await get_simulation_repository()
        now_utc = datetime.now(timezone.utc)
        mock_simulations = [
            {
                "id": "demo-1",
                "name": "Office Building - Fire Scenario",
                "created_at": now_utc.isoformat(),
                "num_agents": 100,
                "status": "completed",
                "emergency_type": "fire",
                "duration": 120,
                "evacuated": 95,
            },
            {
                "id": "demo-2",
                "name": "Shopping Mall - Earthquake",
                "created_at": (now_utc - timedelta(days=1)).isoformat(),
                "num_agents": 200,
                "status": "completed",
                "emergency_type": "earthquake",
                "duration": 180,
                "evacuated": 190,
            },
            {
                "id": "demo-3",
                "name": "School Building - Fire Drill",
                "created_at": (now_utc - timedelta(days=2)).isoformat(),
                "num_agents": 150,
                "status": "completed",
                "emergency_type": "fire",
                "duration": 95,
                "evacuated": 145,
            },
        ]
        seen_ids = {item["id"] for item in mock_simulations}

        for stored in await repository.list(skip=0, limit=200):
            normalized = self._normalize_simulation_doc(stored)
            sim_id = str(normalized.get("id") or "")
            if not sim_id or sim_id in seen_ids:
                continue

            created_at = normalized.get("created_at")
            if hasattr(created_at, "isoformat"):
                created_at = created_at.isoformat()
            elif created_at is None:
                created_at = now_utc.isoformat()

            duration = float(normalized.get("duration") or normalized.get("max_runtime_seconds") or 0)
            status = str(normalized.get("status") or "running")
            if _is_demo_like_simulation_id(sim_id):
                runtime = _get_mock_runtime(sim_id)
                created_at = datetime.fromtimestamp(
                    float(runtime.get("created_ts", time.time())),
                    timezone.utc,
                ).isoformat()
                duration = float(runtime.get("duration_seconds", duration or 120.0))
                status = "completed" if max(0.0, time.time() - float(runtime.get("created_ts", time.time()))) >= duration else "running"

            mock_simulations.insert(
                0,
                {
                    "id": sim_id,
                    "name": str(normalized.get("label") or normalized.get("name") or f"Simulation {sim_id[-6:]}"),
                    "created_at": created_at,
                    "num_agents": int(normalized.get("num_agents", 0) or 0),
                    "status": status,
                    "emergency_type": normalized.get("emergency_type", "fire"),
                    "duration": duration,
                    "evacuated": int((normalized.get("summary") or {}).get("evacuated", 0) or 0),
                },
            )
            seen_ids.add(sim_id)

        for sim_id, runtime in list_mock_runtime_entries():
            if sim_id in seen_ids:
                continue
            created_ts = float(runtime.get("created_ts", time.time()))
            elapsed = max(0.0, time.time() - created_ts)
            duration = float(runtime.get("duration_seconds", 120.0))
            status = "completed" if elapsed >= duration else "running"
            summary = get_summary(sim_id) or _build_mock_summary(sim_id)
            summary_status = str(summary.get("status", "") or "")
            if summary_status:
                status = summary_status
            final_stats = summary.get("final_stats", {}) or {}
            evacuated = int(final_stats.get("evacuated", summary.get("evacuated", 0)) or 0)
            mock_simulations.insert(
                0,
                {
                    "id": sim_id,
                    "name": f"Live Mock Run {sim_id[-6:]}",
                    "created_at": datetime.fromtimestamp(created_ts, timezone.utc).isoformat(),
                    "num_agents": int(runtime.get("num_agents", 100)),
                    "status": status,
                    "emergency_type": runtime.get("emergency_type", "fire"),
                    "duration": duration,
                    "evacuated": evacuated,
                },
            )
            seen_ids.add(sim_id)

        mock_simulations.sort(key=lambda item: item.get("created_at", ""), reverse=True)
        total = len(mock_simulations)
        mock_simulations = mock_simulations[skip : skip + limit]
        return {"simulations": mock_simulations, "total": total}


simulation_catalog_service = SimulationCatalogService()
