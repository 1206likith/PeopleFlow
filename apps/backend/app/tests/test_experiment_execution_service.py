import json
from pathlib import Path
from types import SimpleNamespace

from app.experiments.config import ExperimentConfig
from app.services.experiment_execution_service import ExperimentExecutionService


def test_run_experiment_with_validation_persists_validation(tmp_path, monkeypatch):
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    def _fake_run(config):
        payload = {
            "config": config.model_dump(),
            "config_hash": "hash-single-run",
            "metrics": {"total_evacuation_time": 91.0},
        }
        (output_dir / f"{config.name}.json").write_text(json.dumps(payload), encoding="utf-8")
        return payload

    monkeypatch.setattr("app.services.experiment_execution_service.OUTPUT_DIR", output_dir)
    monkeypatch.setattr("app.services.experiment_execution_service.run_experiment_sync", _fake_run)
    monkeypatch.setattr(
        "app.services.experiment_execution_service.run_validation",
        lambda _path: {"summary": {"overall_score": 0.88, "status": "passed"}},
    )
    monkeypatch.setattr(
        "app.services.experiment_execution_service.experiment_artifact_service.build_catalog_summary",
        lambda: {
            "catalog_version": "peopleflow-experiment-artifact-catalog-v1",
            "run_count": 1,
            "artifact_count": 0,
            "suite_manifest_count": 0,
            "publication_bundle_count": 0,
        },
    )

    service = ExperimentExecutionService()
    response = service.run_experiment(ExperimentConfig(name="single-run", num_agents=12), validate=True)

    assert response["execution_type"] == "single_run"
    assert response["result"]["validation"]["summary"]["status"] == "passed"
    persisted = json.loads((output_dir / "single-run.json").read_text(encoding="utf-8"))
    assert persisted["validation"]["summary"]["overall_score"] == 0.88


def test_run_calibration_with_inline_config_stages_file(tmp_path, monkeypatch):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    captured = {}

    monkeypatch.setattr(
        "app.services.experiment_execution_service.get_safe_artifact_path",
        lambda _name, subdir="cache": cache_dir / subdir / "placeholder.tmp",
    )
    monkeypatch.setattr(
        "app.services.experiment_execution_service.run_calibration",
        lambda base_config, calibration_config_path=None: captured.setdefault(
            "summary",
            {
                "suite_type": "calibration",
                "source_config_path": calibration_config_path,
                "base_name": base_config.name,
            },
        ),
    )
    monkeypatch.setattr(
        "app.services.experiment_execution_service.experiment_artifact_service.build_catalog_summary",
        lambda: {
            "catalog_version": "peopleflow-experiment-artifact-catalog-v1",
            "run_count": 4,
            "artifact_count": 2,
            "suite_manifest_count": 1,
            "publication_bundle_count": 1,
        },
    )

    service = ExperimentExecutionService()
    response = service.run_calibration(
        ExperimentConfig(name="calibration-base", num_agents=16),
        calibration_config={"trials": 3, "parameters": [{"path": "movement.base_speed", "min": 1.0, "max": 1.2}]},
    )

    staged_path = Path(response["summary"]["source_config_path"])
    assert response["execution_type"] == "calibration"
    assert staged_path.exists()
    assert json.loads(staged_path.read_text(encoding="utf-8"))["trials"] == 3


def test_run_publication_bundle_with_inline_batch_config_stages_file(tmp_path, monkeypatch):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    captured = {}

    monkeypatch.setattr(
        "app.services.experiment_execution_service.get_safe_artifact_path",
        lambda _name, subdir="cache": cache_dir / subdir / "placeholder.tmp",
    )

    def _fake_run_paper_pipeline(batch_config_path, validate=True, artifacts_root=None, copy_run_outputs=True):
        captured["batch_config_path"] = batch_config_path
        captured["validate"] = validate
        captured["artifacts_root"] = artifacts_root
        captured["copy_run_outputs"] = copy_run_outputs
        return {"suite_name": "paper-suite", "publication_manifest": str(tmp_path / "bundle.json")}

    monkeypatch.setattr("app.services.experiment_execution_service.run_paper_pipeline", _fake_run_paper_pipeline)
    monkeypatch.setattr(
        "app.services.experiment_execution_service.experiment_artifact_service.build_catalog_summary",
        lambda: {
            "catalog_version": "peopleflow-experiment-artifact-catalog-v1",
            "run_count": 7,
            "artifact_count": 3,
            "suite_manifest_count": 0,
            "publication_bundle_count": 2,
        },
    )

    service = ExperimentExecutionService()
    response = service.run_publication_bundle(
        batch_config={
            "name": "paper-suite",
            "base_config": "research/experiments/baseline.json",
            "seeds": [11],
            "variants": [{"id": "baseline", "overrides": {}}],
        },
        validate=False,
        artifacts_root=str(tmp_path / "paper-results"),
        copy_run_outputs=False,
    )

    staged_path = Path(captured["batch_config_path"])
    assert response["execution_type"] == "publication_bundle"
    assert staged_path.exists()
    assert json.loads(staged_path.read_text(encoding="utf-8"))["name"] == "paper-suite"
    assert captured["validate"] is False
    assert captured["copy_run_outputs"] is False


def test_run_experiment_sync_loads_floor_plan_from_sync_context(tmp_path, monkeypatch):
    from app.experiments.runner import run_experiment_sync

    captured = {}

    class FakeMetricsEngine:
        def __init__(self):
            self.frames = []

        def add_frame(self, frame):
            self.frames.append(frame)

        def calculate_metrics(self):
            return SimpleNamespace(total_evacuation_time=12.5, evacuated_agents=4)

    class FakeSimulationEngine:
        def __init__(self, *args, **kwargs):
            captured["init_args"] = args
            captured["init_kwargs"] = kwargs
            self.completed = False

        def initialize_from_floor_plan(self, floor_plan_data):
            captured["floor_plan_data"] = floor_plan_data

        def set_exits(self, exits):
            captured["exits"] = exits

        def initialize_agents(self):
            captured["initialized_agents"] = True

        def update(self, dt):
            captured["dt"] = dt
            self.completed = True

        def get_frame(self):
            return {
                "timestamp": 0.1,
                "agents": [],
                "stats": {"evacuated": 0, "remaining": 4},
            }

        def is_complete(self):
            return self.completed

    async def fake_load_floor_plan_data(floor_plan_id, floor_number, exits):
        captured["load_args"] = (floor_plan_id, floor_number, exits)
        return (
            {"revision": 7, "detected_walls": [], "exits": [{"id": "main-exit"}]},
            [{"id": "main-exit", "x": 10, "y": 0, "z": 0, "width": 2, "capacity": 50}],
        )

    monkeypatch.setattr("app.experiments.runner.OUTPUT_DIR", tmp_path)
    monkeypatch.setattr("app.experiments.runner.MetricsEngine", FakeMetricsEngine)
    monkeypatch.setattr("app.experiments.runner.load_floor_plan_data", fake_load_floor_plan_data)
    monkeypatch.setattr("app.experiments.runner.parameter_database.snapshot", lambda: {"speed": 1.0})
    monkeypatch.setattr("app.sim.simulation.SimulationEngine", FakeSimulationEngine)

    result = run_experiment_sync(
        ExperimentConfig(name="sync-floor-plan-run", floor_plan_id="mock-floor-plan", num_agents=4)
    )

    assert captured["load_args"] == ("mock-floor-plan", 1, [])
    assert captured["initialized_agents"] is True
    assert captured["exits"][0]["id"] == "main-exit"
    assert result["config"]["floor_plan_id"] == "mock-floor-plan"
    assert result["provenance"]["floor_plan_revision"] == "7"
    assert (tmp_path / "sync-floor-plan-run.json").exists()


def test_catalog_summary_uses_lightweight_artifact_counts(tmp_path, monkeypatch):
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / "single-run.json").write_text(
        json.dumps(
            {
                "record_version": "peopleflow-experiment-run-v1",
                "config": {"name": "single-run", "num_agents": 12},
                "metrics": {"total_evacuation_time": 42.0},
            }
        ),
        encoding="utf-8",
    )
    (output_dir / "suite-summary.json").write_text(
        json.dumps(
            {
                "summary_version": "peopleflow-experiment-suite-v1",
                "suite_type": "ablation",
                "run_count": 3,
                "generated_at": "2026-04-04T00:00:00Z",
                "output_path": str(output_dir / "suite-summary.json"),
            }
        ),
        encoding="utf-8",
    )
    (output_dir / "benchmark.manifest.json").write_text(
        json.dumps(
            {
                "record_version": "peopleflow-research-artifact-v1",
                "artifact_id": "benchmark:corridor",
                "artifact_kind": "benchmark",
                "artifact_type": "json",
                "generated_at": "2026-04-04T00:00:00Z",
                "output_path": str(output_dir / "single-run.json"),
            }
        ),
        encoding="utf-8",
    )

    bundle_manifest = tmp_path / "paper-results" / "paper-suite" / "metadata" / "publication_manifest.json"
    bundle_manifest.parent.mkdir(parents=True, exist_ok=True)
    bundle_manifest.write_text(
        json.dumps(
            {
                "manifest_version": "peopleflow-publication-bundle-v1",
                "generated_at": "2026-04-04T00:00:00Z",
                "suite_name": "paper-suite",
                "run_count": 1,
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr("app.services.experiment_artifact_service.experiment_artifact_service.output_dir", output_dir)
    monkeypatch.setattr("app.services.experiment_artifact_service.experiment_artifact_service.paper_results_dir", tmp_path / "paper-results")

    summary = ExperimentExecutionService._catalog_summary()

    assert summary["catalog_version"] == "peopleflow-experiment-artifact-catalog-v1"
    assert summary["run_count"] == 1
    assert summary["artifact_count"] == 1
    assert summary["suite_manifest_count"] == 1
    assert summary["publication_bundle_count"] == 1
