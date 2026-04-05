import pytest

from app.core.config import settings
from app.core.database import db
from app.services.floor_plan_repository import get_floor_plan_repository
from app.services.floorplan_store import clear_floor_plans


@pytest.fixture(autouse=True)
def clear_floor_plan_demo_store():
    clear_floor_plans()
    yield
    clear_floor_plans()


@pytest.mark.asyncio
async def test_demo_floor_plan_repository_round_trip_and_lookup():
    previous_mode = settings.APP_MODE
    previous_client = db.client
    previous_instrumented = db.instrumented
    settings.APP_MODE = "demo"
    db.client = None
    db.instrumented = None

    try:
        repository = await get_floor_plan_repository()
        floor_plan_id = await repository.create(
            {
                "building_name": "Repository Plan",
                "file_hash": "hash-1",
                "processing_options": {"mode": "traditional", "use_semantic": False},
                "annotations": {"status": "approved"},
            }
        )

        stored = await repository.get(floor_plan_id)
        assert stored is not None
        assert stored["id"] == floor_plan_id
        assert stored["building_name"] == "Repository Plan"

        by_hash = await repository.find_by_hash(
            "hash-1",
            {"mode": "traditional", "use_semantic": False},
        )
        assert by_hash is not None
        assert by_hash["id"] == floor_plan_id

        updated = await repository.update_fields(
            floor_plan_id,
            {"building_name": "Updated Repository Plan"},
        )
        assert updated is not None
        assert updated["building_name"] == "Updated Repository Plan"

        approved = await repository.list_approved(limit=10)
        assert len(approved) == 1
        assert approved[0]["id"] == floor_plan_id
    finally:
        settings.APP_MODE = previous_mode
        db.client = previous_client
        db.instrumented = previous_instrumented
