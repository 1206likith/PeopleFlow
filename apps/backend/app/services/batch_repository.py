"""
Batch repository abstraction with demo/prod implementations.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol

from fastapi import HTTPException

from app.core.config import settings
from app.core.database import MockDatabase, get_database


class BatchRepository(Protocol):
    async def get(self, batch_id: str) -> Optional[Dict[str, Any]]:
        ...

    async def save(self, batch_id: str, doc: Dict[str, Any]) -> None:
        ...

    async def list(self, *, skip: int, limit: int) -> List[Dict[str, Any]]:
        ...


class DemoBatchRepository:
    async def get(self, batch_id: str) -> Optional[Dict[str, Any]]:
        from app.services.batch_store import get_batch

        return get_batch(batch_id)

    async def save(self, batch_id: str, doc: Dict[str, Any]) -> None:
        from app.services.batch_store import save_batch

        save_batch(batch_id, doc)

    async def list(self, *, skip: int, limit: int) -> List[Dict[str, Any]]:
        from app.services.batch_store import list_batches

        return list_batches(skip=skip, limit=limit)


class DatabaseBatchRepository:
    def __init__(self, collection: Any):
        self.collection = collection

    async def get(self, batch_id: str) -> Optional[Dict[str, Any]]:
        return await self.collection.find_one({"batch_id": batch_id})

    async def save(self, batch_id: str, doc: Dict[str, Any]) -> None:
        await self.collection.update_one(
            {"batch_id": batch_id},
            {"$set": doc},
            upsert=True,
        )

    async def list(self, *, skip: int, limit: int) -> List[Dict[str, Any]]:
        cursor = self.collection.find({"tenant_id": "global"}).sort("created_at", -1).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)


async def get_batch_repository() -> BatchRepository:
    try:
        db = await get_database()
        if isinstance(db, MockDatabase):
            return DemoBatchRepository()
        return DatabaseBatchRepository(db.simulation_batches)
    except Exception:
        if not settings.IS_DEMO_MODE:
            raise HTTPException(status_code=503, detail="Database unavailable")
        return DemoBatchRepository()
