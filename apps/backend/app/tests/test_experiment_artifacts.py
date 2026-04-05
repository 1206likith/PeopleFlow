import json
from pathlib import Path
import types

import numpy as np

from app.experiments.ablation_runner import run_ablation_grid
from app.experiments.benchmarks import run_benchmark
from app.experiments.calibration_runner import run_calibration
from app.experiments.config import ExperimentConfig
from app.experiments.indexer import build_index
from app.experiments.metrics_export import export_csv
from app.experiments.optimizer import run_bayesian_optimization
from app.experiments.report_generator import AcademicReportGenerator


def _write_run_record(output_dir: Path, payload: dict) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{payload['config']['name']}.json").write_text(json.dumps(payload), encoding="utf-8")
    return payload


def test_ablation_summary_and_artifact_index_skip_non_run_manifests(tmp_path, monkeypatch):
    output_dir = tmp_path / "output"

    def _fake_run(config):
        payload = {
            "record_version": "peopleflow-experiment-run-v1",
            "config": {
                "name": config.name,
                "seed": config.seed,
                "num_agents": config.num_agents,
                "emergency_type": config.emergency_type,
                "ablation": config.ablation.model_dump(),
            },
            "config_hash": f"hash-{config.name}",
            "metrics": {
                "total_evacuation_time": 100.0,
                "safety_score": 72.0,
                "survival_probability": 0.91,
            },
            "metadata": {"generated_at": "2026-04-03T00:00:00Z"},
            "provenance": {
                "generated_at": "2026-04-03T00:00:00Z",
                "seed": config.seed,
                "engine_version": "peopleflow-sim-v1",
            },
        }
        return _write_run_record(output_dir, payload)

    monkeypatch.setattr("app.experiments.ablation_runner.OUTPUT_DIR", output_dir)
    monkeypatch.setattr("app.experiments.ablation_runner.run_experiment_sync", _fake_run)

    base = ExperimentConfig(name="abl-suite", num_agents=12, emergency_type="fire")
    results = run_ablation_grid(base)

    assert len(results) == 16

    ablation_summary = json.loads((output_dir / "ablation_summary.json").read_text(encoding="utf-8"))
    assert ablation_summary["summary_version"] == "peopleflow-experiment-suite-v1"
    assert ablation_summary["suite_type"] == "ablation"
    assert ablation_summary["run_count"] == 16

    index_payload = build_index(output_dir=str(output_dir), out_path=str(output_dir / "index.json"))
    assert index_payload["manifest_version"] == "peopleflow-experiment-index-v1"
    assert index_payload["result_count"] == 16

    export_manifest = export_csv(output_dir=str(output_dir), csv_path=str(output_dir / "metrics.csv"))
    assert export_manifest["manifest_version"] == "peopleflow-experiment-export-v1"
    assert export_manifest["row_count"] == 16
    assert (output_dir / "metrics.csv.manifest.json").exists()


def test_calibration_summary_uses_canonical_suite_manifest(tmp_path, monkeypatch):
    output_dir = tmp_path / "output"
    calibration_config_path = tmp_path / "calibration.json"
    calibration_config_path.write_text(
        json.dumps(
            {
                "trials": 2,
                "seed": 17,
                "parameters": [{"path": "movement.base_speed", "min": 1.0, "max": 1.2}],
            }
        ),
        encoding="utf-8",
    )

    def _fake_run(config):
        payload = {
            "record_version": "peopleflow-experiment-run-v1",
            "config": {
                "name": config.name,
                "seed": config.seed,
                "num_agents": config.num_agents,
                "emergency_type": config.emergency_type,
                "metadata": config.metadata,
            },
            "config_hash": f"hash-{config.name}",
            "metrics": {"total_evacuation_time": 92.0},
            "metadata": {"generated_at": "2026-04-03T00:00:00Z"},
            "provenance": {"generated_at": "2026-04-03T00:00:00Z", "seed": config.seed},
        }
        return _write_run_record(output_dir, payload)

    monkeypatch.setattr("app.experiments.calibration_runner.OUTPUT_DIR", output_dir)
    monkeypatch.setattr("app.experiments.calibration_runner.run_experiment_sync", _fake_run)
    monkeypatch.setattr("app.experiments.calibration_runner.run_validation", lambda _path: {"overall_score": 0.87, "summary": {"overall_score": 0.87, "status": "passed"}})
    monkeypatch.setattr("app.experiments.calibration_runner.parameter_database.snapshot", lambda: {"movement": {"base_speed": 1.1}})
    monkeypatch.setattr("app.experiments.calibration_runner.parameter_database.apply_overrides", lambda _overrides: None)
    monkeypatch.setattr("app.experiments.calibration_runner.parameter_database.reset", lambda: None)

    summary = run_calibration(
        ExperimentConfig(name="calib-suite", num_agents=8, emergency_type="fire"),
        calibration_config_path=str(calibration_config_path),
    )

    assert summary["summary_version"] == "peopleflow-experiment-suite-v1"
    assert summary["suite_type"] == "calibration"
    assert summary["metadata"]["trials"] == 2
    assert summary["best"]["config_hash"].startswith("hash-")
    assert (output_dir / "calibration_summary.json").exists()


def test_optimization_summary_uses_canonical_suite_manifest(tmp_path, monkeypatch):
    output_dir = tmp_path / "output"
    optimization_config_path = tmp_path / "optimization.json"
    optimization_config_path.write_text(
        json.dumps(
            {
                "trials": 2,
                "seed": 19,
                "method": "tpe",
                "parameters": [{"path": "movement.base_speed", "min": 1.0, "max": 1.2}],
            }
        ),
        encoding="utf-8",
    )

    def _fake_run(config):
        payload = {
            "record_version": "peopleflow-experiment-run-v1",
            "config": {
                "name": config.name,
                "seed": config.seed,
                "num_agents": config.num_agents,
                "emergency_type": config.emergency_type,
                "metadata": config.metadata,
            },
            "config_hash": f"hash-{config.name}",
            "metrics": {
                "total_evacuation_time": 80.0,
                "safety_score": 90.0,
            },
            "metadata": {"generated_at": "2026-04-03T00:00:00Z"},
            "provenance": {"generated_at": "2026-04-03T00:00:00Z", "seed": config.seed},
        }
        return _write_run_record(output_dir, payload)

    monkeypatch.setattr("app.experiments.optimizer.OUTPUT_DIR", output_dir)
    monkeypatch.setattr("app.experiments.optimizer.run_experiment_sync", _fake_run)
    monkeypatch.setattr("app.experiments.optimizer.run_validation", lambda _path: {"overall_score": 0.92, "summary": {"overall_score": 0.92, "status": "passed"}})
    monkeypatch.setattr("app.experiments.optimizer.parameter_database.snapshot", lambda: {"movement": {"base_speed": 1.1}})
    monkeypatch.setattr("app.experiments.optimizer.parameter_database.apply_overrides", lambda _overrides: None)
    monkeypatch.setattr("app.experiments.optimizer.parameter_database.reset", lambda: None)

    summary = run_bayesian_optimization(
        ExperimentConfig(name="opt-suite", num_agents=8, emergency_type="fire"),
        optimization_config_path=str(optimization_config_path),
    )

    assert summary["summary_version"] == "peopleflow-experiment-suite-v1"
    assert summary["suite_type"] == "optimization"
    assert summary["metadata"]["trials"] == 2
    assert summary["best"]["config_hash"].startswith("hash-")
    assert (output_dir / "optimization_summary.json").exists()


def test_academic_report_generator_writes_manifest_and_artifact_index(tmp_path, monkeypatch):
    output_dir = tmp_path / "output"
    csv_path = tmp_path / "comparison.csv"
    csv_path.write_text("Policy,Mean Evac Time (s)\nnearest,12.3\n", encoding="utf-8")

    monkeypatch.setattr("app.experiments.report_generator.OUTPUT_DIR", output_dir)

    output_path = AcademicReportGenerator.generate_pdf(str(csv_path), [], output_filename="academic-report.pdf")

    manifest_path = output_dir / "academic-report.manifest.json"
    index_path = output_dir / "artifacts_index.json"

    assert Path(output_path).exists()
    assert manifest_path.exists()
    assert index_path.exists()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    index_payload = json.loads(index_path.read_text(encoding="utf-8"))

    assert manifest["manifest_version"] == "peopleflow-academic-report-manifest-v1"
    assert manifest["record_version"] == "peopleflow-research-artifact-v1"
    assert manifest["artifact_kind"] == "report"
    assert any(artifact["artifact_id"] == manifest["artifact_id"] for artifact in index_payload["artifacts"])


def test_benchmark_writer_writes_manifest_and_artifact_index(tmp_path, monkeypatch):
    output_dir = tmp_path / "output"

    class _FakeMetricsEngine:
        def add_frame(self, _frame):
            return None

        def calculate_metrics(self):
            return types.SimpleNamespace(max_queue_length=4, total_evacuation_time=33.0, peak_flow_rate=1.2)

    class _FakeSimulationEngine:
        def __init__(self, **_kwargs):
            self.sim = types.SimpleNamespace(
                agents=[
                    types.SimpleNamespace(position=np.array([0.0, 0.0, 0.0])),
                    types.SimpleNamespace(position=np.array([1.0, 1.0, 0.0])),
                ]
            )
            self._complete = False

        def initialize_from_floor_plan(self, _floor_plan):
            return None

        def set_exits(self, _exits):
            return None

        def initialize_agents(self):
            return None

        def update(self, _dt):
            self._complete = True

        def get_frame(self):
            return {"agents": []}

        def is_complete(self):
            return self._complete

    monkeypatch.setattr("app.experiments.benchmarks.OUTPUT_DIR", output_dir)
    monkeypatch.setattr("app.experiments.benchmarks.MetricsEngine", _FakeMetricsEngine)
    monkeypatch.setattr("app.experiments.benchmarks.SimulationEngine", _FakeSimulationEngine)

    result = run_benchmark(
        "corridor_test",
        floor_plan_data={"building_bounds": {"min_x": 0, "max_x": 10, "min_y": 0, "max_y": 2}, "detected_walls": []},
        exits=[{"id": "exit-1", "x": 10, "y": 1.0, "width": 1.0}],
        spawn_area=(1.0, 3.0, 0.5, 1.5),
        num_agents=10,
    )

    manifest_path = output_dir / "benchmark_corridor_test.manifest.json"
    index_path = output_dir / "artifacts_index.json"

    assert result["name"] == "corridor_test"
    assert (output_dir / "benchmark_corridor_test.json").exists()
    assert manifest_path.exists()
    assert index_path.exists()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    index_payload = json.loads(index_path.read_text(encoding="utf-8"))

    assert manifest["manifest_version"] == "peopleflow-benchmark-manifest-v1"
    assert manifest["record_version"] == "peopleflow-research-artifact-v1"
    assert manifest["artifact_kind"] == "benchmark"
    assert any(artifact["artifact_id"] == manifest["artifact_id"] for artifact in index_payload["artifacts"])
