"""Backfill tenant_id to single-tenant global for legacy records."""

from __future__ import annotations

import asyncio

from app.core.database import init_db, close_db, get_database

COLLECTIONS = ("simulations", "floor_plans", "simulation_batches")


async def run() -> None:
    await init_db()
    db = await get_database()
    for name in COLLECTIONS:
        collection = getattr(db, name)
        result = await collection.update_many(
            {"tenant_id": {"$exists": False}},
            {"$set": {"tenant_id": "global"}},
        )
        print(f"{name}: matched={getattr(result, 'matched_count', 0)} modified={getattr(result, 'modified_count', 0)}")
    await close_db()


if __name__ == "__main__":
    asyncio.run(run())
