"""
Simulation metadata/data repository abstraction with demo/prod implementations.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Protocol

from fastapi import HTTPException

from app.core.config import settings
from app.core.database import MockDatabase, get_database


class SimulationDataRepository(Protocol):
    async def create(self, simulation_id: str, data: Dict[str, Any]) -> str:
        ...

    async def list(self, simulation_id: str) -> List[Dict[str, Any]]:
        ...


class DemoSimulationDataRepository:
    async def create(self, simulation_id: str, data: Dict[str, Any]) -> str:
        from app.services.simulation_data_store import save_simulation_data_record

        return save_simulation_data_record(
            simulation_id,
            {
                "simulation_id": simulation_id,
                "data": dict(data),
                "created_at": datetime.now(timezone.utc),
            },
        )

    async def list(self, simulation_id: str) -> List[Dict[str, Any]]:
        from app.services.simulation_data_store import list_simulation_data_records

        return list_simulation_data_records(simulation_id)


class DatabaseSimulationDataRepository:
    def __init__(self, collection: Any):
        self.collection = collection

    @staticmethod
    def _normalize(doc: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(doc)
        if normalized.get("_id") is not None:
            normalized["id"] = str(normalized["_id"])
            del normalized["_id"]
        return normalized

    async def create(self, simulation_id: str, data: Dict[str, Any]) -> str:
        document = {
            "simulation_id": simulation_id,
            "data": dict(data),
            "created_at": datetime.now(timezone.utc),
        }
        result = await self.collection.insert_one(document)
        return str(result.inserted_id)

    async def list(self, simulation_id: str) -> List[Dict[str, Any]]:
        cursor = self.collection.find({"simulation_id": simulation_id}).sort("created_at", 1)
        docs = await cursor.to_list(length=None)
        return [self._normalize(doc) for doc in docs]


async def get_simulation_data_repository() -> SimulationDataRepository:
    if settings.IS_DEMO_MODE:
        return DemoSimulationDataRepository()
    try:
        db = await get_database()
        if isinstance(db, MockDatabase):
            return DemoSimulationDataRepository()
        return DatabaseSimulationDataRepository(db.simulation_data)
    except Exception:
        if not settings.IS_DEMO_MODE:
            raise HTTPException(status_code=503, detail="Database unavailable")
        return DemoSimulationDataRepository()
