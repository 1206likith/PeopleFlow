"""
Repository abstraction for v3 simulation sessions.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol
import uuid

from bson import ObjectId
from fastapi import HTTPException

from app.core.config import settings
from app.core.database import MockDatabase, get_database


class SimulationSessionRepository(Protocol):
    async def create(self, doc: Dict[str, Any]) -> str:
        ...

    async def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        ...

    async def update_fields(self, session_id: str, updates: Dict[str, Any], *, upsert: bool = False) -> Optional[Dict[str, Any]]:
        ...

    async def list(self, *, skip: int, limit: int) -> List[Dict[str, Any]]:
        ...


class DemoSimulationSessionRepository:
    async def create(self, doc: Dict[str, Any]) -> str:
        from app.services.simulation_session_store import save_session

        session_id = str(doc.get("id") or doc.get("_id") or f"session-{uuid.uuid4().hex[:12]}")
        stored = dict(doc)
        now = datetime.now(timezone.utc)
        stored["_id"] = session_id
        stored["id"] = session_id
        stored.setdefault("created_at", now)
        stored["updated_at"] = stored.get("updated_at") or now
        save_session(session_id, stored)
        return session_id

    async def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        from app.services.simulation_session_store import get_session

        return get_session(session_id)

    async def update_fields(self, session_id: str, updates: Dict[str, Any], *, upsert: bool = False) -> Optional[Dict[str, Any]]:
        from app.services.simulation_session_store import get_session, save_session

        existing = get_session(session_id)
        if not existing and not upsert:
            return None

        now = datetime.now(timezone.utc)
        next_doc = dict(existing or {})
        next_doc.setdefault("_id", session_id)
        next_doc.setdefault("id", session_id)
        next_doc.setdefault("created_at", now)
        next_doc.update(dict(updates))
        next_doc["updated_at"] = now
        save_session(session_id, next_doc)
        return next_doc

    async def list(self, *, skip: int, limit: int) -> List[Dict[str, Any]]:
        from app.services.simulation_session_store import list_sessions

        return list_sessions(skip=skip, limit=limit)


class DatabaseSimulationSessionRepository:
    def __init__(self, collection: Any):
        self.collection = collection

    async def _find_doc(self, session_id: str) -> Optional[Dict[str, Any]]:
        try:
            oid = ObjectId(session_id)
        except Exception:
            oid = None

        if oid is not None:
            doc = await self.collection.find_one({"_id": oid})
            if doc:
                return doc

        for query in ({"_id": session_id}, {"id": session_id}):
            doc = await self.collection.find_one(query)
            if doc:
                return doc
        return None

    async def create(self, doc: Dict[str, Any]) -> str:
        result = await self.collection.insert_one(doc)
        return str(doc.get("id") or result.inserted_id)

    async def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        return await self._find_doc(session_id)

    async def update_fields(self, session_id: str, updates: Dict[str, Any], *, upsert: bool = False) -> Optional[Dict[str, Any]]:
        existing = await self._find_doc(session_id)
        if not existing and not upsert:
            return None

        if existing and existing.get("_id") is not None:
            update_filter = {"_id": existing.get("_id")}
        else:
            update_filter = {"id": session_id}

        normalized_updates = dict(updates)
        normalized_updates["updated_at"] = datetime.now(timezone.utc)
        await self.collection.update_one(update_filter, {"$set": normalized_updates}, upsert=upsert)
        return await self._find_doc(session_id)

    async def list(self, *, skip: int, limit: int) -> List[Dict[str, Any]]:
        cursor = self.collection.find({}).sort("created_at", -1).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)


async def get_simulation_session_repository() -> SimulationSessionRepository:
    if settings.IS_DEMO_MODE:
        return DemoSimulationSessionRepository()
    try:
        db = await get_database()
        if isinstance(db, MockDatabase):
            return DemoSimulationSessionRepository()
        return DatabaseSimulationSessionRepository(db.simulation_sessions)
    except Exception:
        if not settings.IS_DEMO_MODE:
            raise HTTPException(status_code=503, detail="Database unavailable")
        return DemoSimulationSessionRepository()
