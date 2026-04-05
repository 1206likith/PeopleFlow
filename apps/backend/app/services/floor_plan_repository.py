"""
Floor-plan repository abstraction with demo/prod implementations.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol
import uuid

from bson import ObjectId
from fastapi import HTTPException

from app.core.config import settings
from app.core.database import MockDatabase, get_database


class FloorPlanRepository(Protocol):
    async def create(self, doc: Dict[str, Any]) -> str:
        ...

    async def get(self, floor_plan_id: str) -> Optional[Dict[str, Any]]:
        ...

    async def update_fields(
        self,
        floor_plan_id: str,
        updates: Dict[str, Any],
        *,
        upsert: bool = False,
    ) -> Optional[Dict[str, Any]]:
        ...

    async def find_by_hash(self, file_hash: str, processing_options: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        ...

    async def list_approved(self, *, limit: int) -> List[Dict[str, Any]]:
        ...


class DemoFloorPlanRepository:
    async def create(self, doc: Dict[str, Any]) -> str:
        from app.services.floorplan_store import save_floor_plan

        floor_plan_id = str(doc.get("id") or doc.get("_id") or f"mock-{uuid.uuid4().hex[:12]}")
        if not floor_plan_id.startswith("mock-"):
            floor_plan_id = f"mock-{floor_plan_id}"
        now = datetime.now(timezone.utc)
        stored = dict(doc)
        stored["_id"] = floor_plan_id
        stored["id"] = floor_plan_id
        stored.setdefault("tenant_id", "global")
        stored.setdefault("created_at", now)
        stored["updated_at"] = stored.get("updated_at") or now
        save_floor_plan(floor_plan_id, stored)
        return floor_plan_id

    async def get(self, floor_plan_id: str) -> Optional[Dict[str, Any]]:
        from app.services.floorplan_store import get_floor_plan

        return get_floor_plan(floor_plan_id)

    async def update_fields(
        self,
        floor_plan_id: str,
        updates: Dict[str, Any],
        *,
        upsert: bool = False,
    ) -> Optional[Dict[str, Any]]:
        from app.services.floorplan_store import get_floor_plan, save_floor_plan, update_floor_plan

        existing = get_floor_plan(floor_plan_id)
        if existing:
            return update_floor_plan(floor_plan_id, updates)
        if not upsert:
            return None

        now = datetime.now(timezone.utc)
        next_doc = {
            "_id": floor_plan_id,
            "id": floor_plan_id,
            "tenant_id": "global",
            "created_at": now,
            "updated_at": now,
        }
        next_doc.update(dict(updates))
        save_floor_plan(floor_plan_id, next_doc)
        return get_floor_plan(floor_plan_id)

    async def find_by_hash(self, file_hash: str, processing_options: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        from app.services.floorplan_store import find_floor_plan_by_hash

        return find_floor_plan_by_hash(file_hash, processing_options)

    async def list_approved(self, *, limit: int) -> List[Dict[str, Any]]:
        from app.services.floorplan_store import list_floor_plans

        approved: List[Dict[str, Any]] = []
        for doc in list_floor_plans(skip=0, limit=None):
            annotations = doc.get("annotations") or {}
            if str(annotations.get("status") or "").lower() == "approved":
                approved.append(doc)
                if len(approved) >= limit:
                    break
        return approved


class DatabaseFloorPlanRepository:
    def __init__(self, collection: Any):
        self.collection = collection

    async def _find_doc(self, floor_plan_id: str) -> Optional[Dict[str, Any]]:
        try:
            oid = ObjectId(floor_plan_id)
        except Exception:
            oid = None

        if oid is not None:
            doc = await self.collection.find_one({"_id": oid})
            if doc:
                return doc

        doc = await self.collection.find_one({"_id": floor_plan_id})
        if doc:
            return doc

        doc = await self.collection.find_one({"id": floor_plan_id})
        if doc:
            return doc

        return None

    async def create(self, doc: Dict[str, Any]) -> str:
        result = await self.collection.insert_one(doc)
        return str(result.inserted_id)

    async def get(self, floor_plan_id: str) -> Optional[Dict[str, Any]]:
        return await self._find_doc(floor_plan_id)

    async def update_fields(
        self,
        floor_plan_id: str,
        updates: Dict[str, Any],
        *,
        upsert: bool = False,
    ) -> Optional[Dict[str, Any]]:
        existing = await self._find_doc(floor_plan_id)
        if not existing and not upsert:
            return None

        if existing and existing.get("_id") is not None:
            update_filter = {"_id": existing.get("_id")}
        else:
            update_filter = {"id": floor_plan_id}

        normalized_updates = dict(updates)
        normalized_updates["updated_at"] = normalized_updates.get("updated_at") or datetime.now(timezone.utc)
        await self.collection.update_one(update_filter, {"$set": normalized_updates}, upsert=upsert)
        return await self._find_doc(floor_plan_id)

    async def find_by_hash(self, file_hash: str, processing_options: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not file_hash:
            return None
        return await self.collection.find_one(
            {
                "file_hash": file_hash,
                "processing_options": processing_options,
            }
        )

    async def list_approved(self, *, limit: int) -> List[Dict[str, Any]]:
        cursor = self.collection.find({}).limit(limit)
        docs = await cursor.to_list(length=limit)
        approved: List[Dict[str, Any]] = []
        for doc in docs:
            annotations = doc.get("annotations") or {}
            if str(annotations.get("status") or "").lower() == "approved":
                approved.append(doc)
        return approved


async def get_floor_plan_repository() -> FloorPlanRepository:
    if settings.IS_DEMO_MODE:
        return DemoFloorPlanRepository()
    try:
        db = await get_database()
        if isinstance(db, MockDatabase):
            return DemoFloorPlanRepository()
        return DatabaseFloorPlanRepository(db.floor_plans)
    except Exception:
        if not settings.IS_DEMO_MODE:
            raise HTTPException(status_code=503, detail="Database unavailable")
        return DemoFloorPlanRepository()
