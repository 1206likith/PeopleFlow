"""
Simulation frame/result repository abstraction with demo/prod implementations.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol

from fastapi import HTTPException

from app.core.config import settings
from app.core.database import MockDatabase, get_database


class SimulationResultRepository(Protocol):
    async def insert_frame(self, doc: Dict[str, Any]) -> str:
        ...

    async def list_frames(
        self,
        simulation_id: str,
        *,
        limit: Optional[int],
        skip: int,
        from_ts: Optional[float],
        to_ts: Optional[float],
    ) -> List[Dict[str, Any]]:
        ...

    async def get_latest_frame(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        ...

    async def delete_frames(self, simulation_id: str) -> int:
        ...


class DemoSimulationResultRepository:
    async def insert_frame(self, doc: Dict[str, Any]) -> str:
        return "mock"

    async def list_frames(
        self,
        simulation_id: str,
        *,
        limit: Optional[int],
        skip: int,
        from_ts: Optional[float],
        to_ts: Optional[float],
    ) -> List[Dict[str, Any]]:
        from app.services.simulation_store import get_frames

        return get_frames(
            simulation_id,
            limit=limit,
            skip=skip,
            stride=1,
            from_ts=from_ts,
            to_ts=to_ts,
        )

    async def get_latest_frame(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        from app.services.simulation_store import get_latest_frame

        return get_latest_frame(simulation_id)

    async def delete_frames(self, simulation_id: str) -> int:
        from app.services.simulation_store import clear_frames

        clear_frames(simulation_id)
        return 0


class DatabaseSimulationResultRepository:
    def __init__(self, collection: Any):
        self.collection = collection

    @staticmethod
    def _normalize(frame: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(frame)
        if normalized.get("_id") is not None:
            normalized["id"] = str(normalized["_id"])
            del normalized["_id"]
        return normalized

    async def insert_frame(self, doc: Dict[str, Any]) -> str:
        result = await self.collection.insert_one(doc)
        return str(result.inserted_id)

    async def list_frames(
        self,
        simulation_id: str,
        *,
        limit: Optional[int],
        skip: int,
        from_ts: Optional[float],
        to_ts: Optional[float],
    ) -> List[Dict[str, Any]]:
        query: Dict[str, Any] = {"simulation_id": simulation_id}
        if from_ts is not None or to_ts is not None:
            ts_query: Dict[str, float] = {}
            if from_ts is not None:
                ts_query["$gte"] = float(from_ts)
            if to_ts is not None:
                ts_query["$lte"] = float(to_ts)
            query["timestamp"] = ts_query
        cursor = self.collection.find(query).sort("timestamp", 1).skip(skip)
        if limit is not None:
            cursor = cursor.limit(limit)
        frames = await cursor.to_list(length=limit)
        return [self._normalize(frame) for frame in frames]

    async def get_latest_frame(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.collection.find({"simulation_id": simulation_id}).sort("timestamp", -1).limit(1)
        docs = await cursor.to_list(length=1)
        if not docs:
            return None
        return self._normalize(docs[0])

    async def delete_frames(self, simulation_id: str) -> int:
        result = await self.collection.delete_many({"simulation_id": simulation_id})
        return int(getattr(result, "deleted_count", 0) or 0)


async def get_simulation_result_repository() -> SimulationResultRepository:
    if settings.IS_DEMO_MODE:
        return DemoSimulationResultRepository()
    try:
        db = await get_database()
        if isinstance(db, MockDatabase):
            return DemoSimulationResultRepository()
        return DatabaseSimulationResultRepository(db.simulation_results)
    except Exception:
        if not settings.IS_DEMO_MODE:
            raise HTTPException(status_code=503, detail="Database unavailable")
        return DemoSimulationResultRepository()
