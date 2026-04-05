"""
Simulation record repository abstraction with demo/prod implementations.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol
import uuid

from bson import ObjectId
from fastapi import HTTPException

from app.core.config import settings
from app.core.database import MockDatabase, get_database


class SimulationRepository(Protocol):
    async def create(self, doc: Dict[str, Any]) -> str:
        ...

    async def get(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        ...

    async def update_fields(
        self,
        simulation_id: str,
        updates: Dict[str, Any],
        *,
        upsert: bool = False,
    ) -> Optional[Dict[str, Any]]:
        ...

    async def list(self, *, skip: int, limit: int) -> List[Dict[str, Any]]:
        ...


class DemoSimulationRepository:
    async def create(self, doc: Dict[str, Any]) -> str:
        from app.services.simulation_record_store import save_simulation_record

        simulation_id = str(doc.get("id") or doc.get("_id") or f"mock-{uuid.uuid4().hex[:12]}")
        stored = dict(doc)
        now = datetime.now(timezone.utc)
        stored["_id"] = simulation_id
        stored["id"] = simulation_id
        stored.setdefault("tenant_id", "global")
        stored.setdefault("created_at", now)
        stored["updated_at"] = stored.get("updated_at") or now
        save_simulation_record(simulation_id, stored)
        return simulation_id

    async def get(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        from app.services.simulation_record_store import get_simulation_record

        return get_simulation_record(simulation_id)

    async def update_fields(
        self,
        simulation_id: str,
        updates: Dict[str, Any],
        *,
        upsert: bool = False,
    ) -> Optional[Dict[str, Any]]:
        from app.services.simulation_record_store import get_simulation_record, save_simulation_record

        existing = get_simulation_record(simulation_id)
        if not existing and not upsert:
            return None

        now = datetime.now(timezone.utc)
        next_doc = dict(existing or {})
        next_doc.setdefault("_id", simulation_id)
        next_doc.setdefault("id", simulation_id)
        next_doc.setdefault("tenant_id", "global")
        next_doc.setdefault("created_at", now)
        next_doc.update(dict(updates))
        next_doc["updated_at"] = now
        save_simulation_record(simulation_id, next_doc)
        return next_doc

    async def list(self, *, skip: int, limit: int) -> List[Dict[str, Any]]:
        from app.services.simulation_record_store import list_simulation_records

        return list_simulation_records(skip=skip, limit=limit)


class DatabaseSimulationRepository:
    def __init__(self, collection: Any):
        self.collection = collection

    async def _find_doc(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        try:
            oid = ObjectId(simulation_id)
        except Exception:
            oid = None

        if oid is not None:
            doc = await self.collection.find_one({"_id": oid})
            if doc:
                return doc

        doc = await self.collection.find_one({"_id": simulation_id})
        if doc:
            return doc

        doc = await self.collection.find_one({"id": simulation_id})
        if doc:
            return doc

        return None

    async def create(self, doc: Dict[str, Any]) -> str:
        result = await self.collection.insert_one(doc)
        return str(result.inserted_id)

    async def get(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        return await self._find_doc(simulation_id)

    async def update_fields(
        self,
        simulation_id: str,
        updates: Dict[str, Any],
        *,
        upsert: bool = False,
    ) -> Optional[Dict[str, Any]]:
        existing = await self._find_doc(simulation_id)
        if not existing and not upsert:
            return None

        if existing and existing.get("_id") is not None:
            update_filter = {"_id": existing.get("_id")}
        elif simulation_id:
            update_filter = {"id": simulation_id}
        else:
            return None

        normalized_updates = dict(updates)
        normalized_updates["updated_at"] = datetime.now(timezone.utc)
        await self.collection.update_one(update_filter, {"$set": normalized_updates}, upsert=upsert)
        return await self._find_doc(simulation_id)

    async def list(self, *, skip: int, limit: int) -> List[Dict[str, Any]]:
        cursor = self.collection.find({"tenant_id": "global"}).sort("created_at", -1).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)


async def get_simulation_repository() -> SimulationRepository:
    if settings.IS_DEMO_MODE:
        return DemoSimulationRepository()
    try:
        db = await get_database()
        if isinstance(db, MockDatabase):
            return DemoSimulationRepository()
        return DatabaseSimulationRepository(db.simulations)
    except Exception:
        if not settings.IS_DEMO_MODE:
            raise HTTPException(status_code=503, detail="Database unavailable")
        return DemoSimulationRepository()
