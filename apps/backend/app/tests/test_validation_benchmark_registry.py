import json

from app.services.model_calibration import EXIT89Dataset, ModelCalibrator
from app.services.validation_application_service import validation_application_service
from app.services.validation_engine import ValidationEngine
from app.services.validation_suite import ValidationSuite
from app.validation.benchmark_registry import get_validation_benchmark_registry
from app.validation.targets import load_targets


def test_load_targets_delegates_to_registry(tmp_path):
    custom_targets = {
        "exit89": {"mean_delay": {"target": 4.2, "tolerance": 0.7}},
        "fundamental": {"peak_flow_rate": {"min": 0.5, "max": 2.1}, "rmse_tolerance": 0.9},
        "evacuation": {"time_target": 80.0, "time_tolerance_pct": 0.2},
    }
    target_file = tmp_path / "targets.json"
    target_file.write_text(json.dumps(custom_targets), encoding="utf-8")

    assert load_targets(str(target_file)) == custom_targets


def test_validation_engine_uses_registry_targets(tmp_path, monkeypatch):
    custom_targets = {
        "exit89": {"mean_delay": {"target": 4.2, "tolerance": 0.7}},
        "fundamental": {"peak_flow_rate": {"min": 0.5, "max": 2.1}, "rmse_tolerance": 0.9},
        "evacuation": {"time_target": 80.0, "time_tolerance_pct": 0.2},
    }
    target_file = tmp_path / "targets.json"
    target_file.write_text(json.dumps(custom_targets), encoding="utf-8")

    monkeypatch.setattr(
        "app.services.validation_engine.get_validation_benchmark_registry",
        lambda: get_validation_benchmark_registry(str(target_file)),
    )

    engine = ValidationEngine()

    pre_evacuation_benchmark = engine.registry.get_runtime_benchmark("pre_evacuation_delay")
    density_speed_benchmark = engine.registry.get_runtime_benchmark("density_speed_curve")

    assert pre_evacuation_benchmark is not None
    assert pre_evacuation_benchmark.expected_results["mean"] == 4.2
    assert pre_evacuation_benchmark.tolerance["mean_abs"] == 0.7
    assert density_speed_benchmark is not None
    assert density_speed_benchmark.tolerance["rmse"] == 0.9


def test_validation_suite_and_service_share_registry_catalog():
    registry = get_validation_benchmark_registry()
    suite = ValidationSuite()
    benchmark_payload = validation_application_service.list_benchmarks()

    runtime_ids = [benchmark["id"] for benchmark in benchmark_payload["runtime_benchmarks"]]
    suite_ids = [benchmark["id"] for benchmark in benchmark_payload["suite_benchmarks"]]

    assert benchmark_payload["catalog_version"] == "peopleflow-validation-benchmarks-v1"
    assert [benchmark["name"] for benchmark in benchmark_payload["benchmarks"]] == [
        "corridor_flow_rate",
        "density_speed_curve",
        "pre_evacuation_delay",
    ]
    assert runtime_ids == [benchmark.benchmark_id for benchmark in registry.list_runtime_benchmarks()]
    assert suite_ids == [benchmark.benchmark_id for benchmark in registry.list_suite_benchmarks()]
    assert [benchmark["id"] for benchmark in suite.list_benchmarks()] == suite_ids
    assert benchmark_payload["targets"]["exit89"]["mean_delay"]["target"] == 2.5


def test_model_calibration_exit89_dataset_uses_registry_targets(tmp_path, monkeypatch):
    custom_targets = {
        "exit89": {"mean_delay": {"target": 3.8, "tolerance": 0.4}},
        "fundamental": {"peak_flow_rate": {"min": 0.5, "max": 1.9}, "rmse_tolerance": 0.6},
        "evacuation": {"time_target": 70.0, "time_tolerance_pct": 0.2},
    }
    target_file = tmp_path / "targets.json"
    target_file.write_text(json.dumps(custom_targets), encoding="utf-8")

    monkeypatch.setattr(
        "app.services.model_calibration.get_validation_benchmark_registry",
        lambda: get_validation_benchmark_registry(str(target_file)),
    )

    delays = EXIT89Dataset.get_pre_evac_delay_distribution()
    walking_speeds = EXIT89Dataset.get_walking_speed_distribution()
    flow_rates = EXIT89Dataset.get_flow_rate_parameters()
    calibrator = ModelCalibrator()

    assert delays["mean"] == 3.8
    assert walking_speeds["mean"] == 1.35
    assert flow_rates["base_flow_rate"] == 1.33
    assert flow_rates["max_flow_rate"] == 1.9
    assert calibrator.empirical_datasets["EXIT89"][0].value == 3.8
