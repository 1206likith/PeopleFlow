import sys
from pathlib import Path
from typing import Any
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from contextlib import contextmanager

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.main import app
from app.core.config import settings
from app.services.floorplan_store import clear_floor_plans
from app.services.simulation_session_store import clear_all_session_store
from app.services.simulation_store import clear_simulation_store


@contextmanager
def _isolated_settings():
    """Context manager to isolate settings changes per test."""
    original_values = {}
    try:
        yield original_values
    finally:
        for key, value in original_values.items():
            setattr(settings, key, value)


@pytest.fixture
def isolated_settings():
    """Fixture for settings isolation."""
    return _isolated_settings()


def create_test_client(fastapi_app: FastAPI):
    """Factory function to create a TestClient with proper httpx configuration."""
    return TestClient(fastapi_app)


@pytest.fixture
def client():
    """Create a TestClient with explicit httpx transport to avoid deprecation warnings."""
    with create_test_client(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def _reset_runtime_state_after_test():
    """Prevent cross-test leakage from mutable settings and in-memory fallback stores."""
    snapshot: dict[str, Any] = settings.model_dump()
    try:
        yield
    finally:
        for key, value in snapshot.items():
            setattr(settings, key, value)
        clear_floor_plans()
        clear_all_session_store()
        clear_simulation_store()
