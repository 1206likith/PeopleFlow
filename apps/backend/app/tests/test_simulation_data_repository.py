import pytest

from app.core.config import settings
from app.core.database import db
from app.services.data_service import get_simulation_data, save_simulation_data
from app.services.simulation_data_repository import get_simulation_data_repository
from app.services.simulation_data_store import clear_simulation_data_store


@pytest.fixture(autouse=True)
def clear_demo_simulation_data_store():
    clear_simulation_data_store()
    yield
    clear_simulation_data_store()


@pytest.mark.asyncio
async def test_demo_simulation_data_repository_round_trip():
    previous_mode = settings.APP_MODE
    previous_client = db.client
    previous_instrumented = db.instrumented
    settings.APP_MODE = "demo"
    db.client = None
    db.instrumented = None

    try:
        repository = await get_simulation_data_repository()
        record_id = await repository.create(
            "demo-simulation",
            {"total_time": 18.4, "evacuated": 22},
        )
        assert record_id.startswith("mock-data-")

        items = await repository.list("demo-simulation")
        assert len(items) == 1
        assert items[0]["simulation_id"] == "demo-simulation"
        assert items[0]["data"]["evacuated"] == 22
        assert "_id" not in items[0]
    finally:
        settings.APP_MODE = previous_mode
        db.client = previous_client
        db.instrumented = previous_instrumented


@pytest.mark.asyncio
async def test_legacy_data_service_uses_repository_boundary_in_demo_mode():
    previous_mode = settings.APP_MODE
    previous_client = db.client
    previous_instrumented = db.instrumented
    settings.APP_MODE = "demo"
    db.client = None
    db.instrumented = None

    try:
        record_id = await save_simulation_data(
            "service-demo-simulation",
            {"agents": 48, "total_time": 32.1},
        )
        assert record_id.startswith("mock-data-")

        items = await get_simulation_data("service-demo-simulation")
        assert len(items) == 1
        assert items[0]["data"]["agents"] == 48
        assert items[0]["simulation_id"] == "service-demo-simulation"
    finally:
        settings.APP_MODE = previous_mode
        db.client = previous_client
        db.instrumented = previous_instrumented
