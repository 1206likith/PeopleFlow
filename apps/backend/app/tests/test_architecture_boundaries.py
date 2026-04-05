from pathlib import Path
import re


BACKEND_ROOT = Path(__file__).resolve().parents[2]
SERVICES_ROOT = BACKEND_ROOT / "app" / "services"
SIMULATION_ROUTE = BACKEND_ROOT / "app" / "api" / "routes" / "simulation.py"
CORE_SIMULATION_SERVICE_FILES = [
    "app/services/data_service.py",
    "app/services/frame_ingest.py",
    "app/services/floor_plan_document_service.py",
    "app/services/floorplan_loader.py",
    "app/services/legacy_results_service.py",
    "app/services/report_service.py",
    "app/services/simulation_catalog_service.py",
    "app/services/simulation_control_service.py",
    "app/services/simulation_data_repository.py",
    "app/services/simulation_runtime_query_service.py",
    "app/services/simulation_scenario_service.py",
    "app/services/simulation_start_service.py",
    "app/services/simulation_upload_service.py",
    "app/services/unity_bridge.py",
    "app/services/validation_application_service.py",
]


def test_services_do_not_import_legacy_simulation_route_module():
    offenders = []
    for path in SERVICES_ROOT.rglob("*.py"):
        content = path.read_text(encoding="utf-8-sig")
        if "from app.api.routes import simulation" in content or "app.api.routes.simulation" in content:
            offenders.append(path.relative_to(BACKEND_ROOT).as_posix())

    assert offenders == []


def test_legacy_simulation_route_module_is_only_a_compatibility_shim():
    content = SIMULATION_ROUTE.read_text(encoding="utf-8-sig")

    assert "@router." not in content
    assert "app.services.simulation_mock_runtime_service" in content


def test_core_simulation_services_do_not_reach_directly_into_database_layer():
    offenders = []
    direct_db_pattern = re.compile(r"\bget_database\b|\.simulation_results\b|\.simulations\b|\.simulation_data\b")
    for relative_path in CORE_SIMULATION_SERVICE_FILES:
        path = BACKEND_ROOT / relative_path
        content = path.read_text(encoding="utf-8-sig")
        if relative_path.endswith("repository.py"):
            continue
        if direct_db_pattern.search(content):
            offenders.append(relative_path)

    assert offenders == []
