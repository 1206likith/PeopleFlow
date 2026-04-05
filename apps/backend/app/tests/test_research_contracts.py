import json
from pathlib import Path

import pytest

from app.core.config import settings
from app.services import report_service
from app.services.validation_application_service import validation_application_service
from app.validation import runner as validation_runner
from app.experiments.metadata import build_provenance


def test_run_validation_returns_summary_and_checks(tmp_path, monkeypatch):
    output_path = tmp_path / "result.json"
    output_path.write_text(json.dumps({"metrics": {"total_evacuation_time": 72.0}}), encoding="utf-8")

    monkeypatch.setattr(validation_runner, "validate_exit89", lambda _metrics: {"status": "ok", "score": 0.9})
    monkeypatch.setattr(validation_runner, "validate_fundamental_diagram", lambda _metrics: {"status": "poor_fit", "score": 0.2})
    monkeypatch.setattr(validation_runner, "validate_evacuation_metrics", lambda _metrics: {"status": "ok", "score": 0.8})

    report = validation_runner.run_validation(str(output_path))

    assert report["summary"]["schema_version"] == "peopleflow-validation-summary-v1"
    assert report["summary"]["source"] == "literature_validation"
    assert report["summary"]["passed_checks"] == 2
    assert set(report["checks"]) == {"exit89", "fundamental", "evacuation"}
    assert report["checks"]["exit89"]["passed"] is True
    assert report["checks"]["fundamental"]["passed"] is False
    assert report["provenance"]["output_path"] == str(output_path)


@pytest.mark.asyncio
async def test_runtime_validation_service_returns_normalized_summary(monkeypatch):
    previous_mode = settings.APP_MODE
    settings.APP_MODE = "demo"
    monkeypatch.setattr(
        "app.services.validation_application_service.validation_engine.validate_simulation",
        lambda _simulation, _agents, _exits: {
            "overall_score": 66.7,
            "passed_tests": 2,
            "total_tests": 3,
            "results": [
                {"test_name": "corridor_flow_rate", "passed": True, "rmse": 0.05},
                {"test_name": "density_speed_curve", "passed": False, "rmse": 0.22},
                {"test_name": "pre_evacuation_delay", "passed": True, "rmse": 0.08},
            ],
            "validation_status": "failed",
        },
    )

    try:
        report = await validation_application_service.validate_simulation_by_id("mock-validation-contract")
    finally:
        settings.APP_MODE = previous_mode

    assert report["summary"]["source"] == "runtime_validation"
    assert report["summary"]["overall_score"] == pytest.approx(66.7)
    assert report["summary"]["passed_checks"] == 2
    assert report["checks"]["corridor_flow_rate"]["passed"] is True
    assert report["checks"]["density_speed_curve"]["status"] == "failed"
    assert report["provenance"]["simulation_id"] == "mock-validation-contract"


def test_build_provenance_includes_config_snapshot_and_hash():
    provenance = build_provenance(
        {
            "name": "baseline",
            "engine": "core",
            "seed": 42,
            "floor_plan_id": "fp-123",
            "metadata": {
                "publication": {"paper": "PeopleFlow", "section": "results"},
                "tag": "regression",
            },
        },
        config_hash="abc123",
        floor_plan_revision="rev-7",
    ).to_dict()

    assert provenance["config_hash"] == "abc123"
    assert provenance["config_snapshot"]["name"] == "baseline"
    assert provenance["floor_plan_revision"] == "rev-7"
    assert provenance["publication_metadata"]["paper"] == "PeopleFlow"
    assert provenance["run_metadata"]["tag"] == "regression"


@pytest.mark.asyncio
async def test_generate_pdf_report_writes_manifest_sidecar(tmp_path, monkeypatch):
    previous_mode = settings.APP_MODE
    settings.APP_MODE = "demo"

    def _fake_safe_artifact_path(filename: str, subdir: str = "reports"):
        target_dir = tmp_path / subdir
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir / filename

    monkeypatch.setattr(report_service, "get_safe_artifact_path", _fake_safe_artifact_path)

    try:
        report_path = await report_service.generate_pdf_report("mock-report-contract")
        manifest_path = Path(str(report_path).replace(".pdf", ".manifest.json"))

        assert Path(report_path).exists()
        assert manifest_path.exists()

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["manifest_version"] == "peopleflow-report-manifest-v1"
        assert manifest["record_version"] == "peopleflow-research-artifact-v1"
        assert manifest["simulation_id"] == "mock-report-contract"
        assert manifest["artifact_type"] == "pdf"
        assert manifest["validation"]["summary"]["source"] == "report_generation"
        assert manifest["provenance"]["simulation_id"] == "mock-report-contract"

        index_path = tmp_path / "reports" / "simulation_report_mock-report-contract.index.json"
        assert index_path.exists()
        index_payload = json.loads(index_path.read_text(encoding="utf-8"))
        assert index_payload["manifest_version"] == "peopleflow-research-artifact-index-v1"
        assert index_payload["artifact_count"] >= 1
        assert index_payload["artifacts"][0]["artifact_kind"] == "report"
    finally:
        settings.APP_MODE = previous_mode


@pytest.mark.asyncio
async def test_build_heatmap_data_writes_artifact_manifest_and_index(tmp_path, monkeypatch):
    previous_mode = settings.APP_MODE
    settings.APP_MODE = "demo"

    def _fake_safe_artifact_path(filename: str, subdir: str = "reports"):
        target_dir = tmp_path / subdir
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir / filename

    monkeypatch.setattr(report_service, "get_safe_artifact_path", _fake_safe_artifact_path)

    try:
        payload = await report_service.build_heatmap_data("mock-report-heatmap")

        heatmap_path = tmp_path / "reports" / "simulation_report_mock-report-heatmap.heatmap.json"
        manifest_path = tmp_path / "reports" / "simulation_report_mock-report-heatmap.heatmap.manifest.json"
        index_path = tmp_path / "reports" / "simulation_report_mock-report-heatmap.index.json"

        assert payload["total_points"] > 0
        assert heatmap_path.exists()
        assert manifest_path.exists()
        assert index_path.exists()

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        index_payload = json.loads(index_path.read_text(encoding="utf-8"))

        assert manifest["artifact_type"] == "heatmap"
        assert manifest["record_version"] == "peopleflow-research-artifact-v1"
        assert manifest["validation"]["summary"]["source"] == "report_generation"
        assert index_payload["manifest_version"] == "peopleflow-research-artifact-index-v1"
        assert any(artifact["artifact_type"] == "heatmap" for artifact in index_payload["artifacts"])
    finally:
        settings.APP_MODE = previous_mode
