import json
from pathlib import Path

import pytest

from app.experiments import paper_pipeline


def test_run_paper_pipeline_generates_multi_seed_bundle(tmp_path, monkeypatch):
    root_dir = tmp_path / "repo"
    output_dir = root_dir / "research" / "experiments" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(paper_pipeline, "ROOT_DIR", root_dir)
    monkeypatch.setattr(paper_pipeline, "OUTPUT_DIR", output_dir)

    base_config_path = root_dir / "research" / "experiments" / "baseline.json"
    base_config_path.parent.mkdir(parents=True, exist_ok=True)
    base_config_path.write_text(
        json.dumps(
            {
                "name": "base-run",
                "num_agents": 20,
                "panic_level": 0.3,
                "emergency_type": "fire",
            }
        ),
        encoding="utf-8",
    )

    batch_config_path = root_dir / "research" / "experiments" / "batches" / "paper_suite.json"
    batch_config_path.parent.mkdir(parents=True, exist_ok=True)
    batch_config_path.write_text(
        json.dumps(
            {
                "name": "paper_suite",
                "base_config": "research/experiments/baseline.json",
                "seeds": [11, 13],
                "variants": [
                    {"id": "full_model", "overrides": {"panic_level": 0.4}},
                    {"id": "ablation_a", "overrides": {"panic_level": 0.2}},
                ],
            }
        ),
        encoding="utf-8",
    )

    def _fake_run(config):
        run_name = config.name
        payload = {
            "config": {"name": run_name},
            "metrics": {
                "total_evacuation_time": float(100 + config.seed),
                "safety_score": float(70 + config.seed % 5),
                "survival_probability": 0.9,
            },
        }
        (output_dir / f"{run_name}.json").write_text(json.dumps(payload), encoding="utf-8")
        return payload

    monkeypatch.setattr(paper_pipeline, "run_experiment_sync", _fake_run)
    monkeypatch.setattr(
        paper_pipeline,
        "run_validation",
        lambda _path: {"overall_score": 0.88, "checks": {"exit89": {"score": 0.9}}},
    )

    result = paper_pipeline.run_paper_pipeline(str(batch_config_path), validate=True)

    assert result["suite_name"] == "paper_suite"
    assert result["run_count"] == 4

    runs_csv = Path(result["runs_csv"])
    runs_json = Path(result["runs_json"])
    summary_json = Path(result["stats_summary"])

    assert runs_csv.exists()
    assert runs_json.exists()
    assert summary_json.exists()

    rows = json.loads(runs_json.read_text(encoding="utf-8"))
    assert len(rows) == 4

    summary = json.loads(summary_json.read_text(encoding="utf-8"))
    assert "full_model" in summary["metrics"]
    assert "ablation_a_vs_full_model" in summary["comparisons"]


def test_run_paper_pipeline_publication_layout_and_metadata(tmp_path, monkeypatch):
    root_dir = tmp_path / "repo"
    output_dir = root_dir / "research" / "experiments" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(paper_pipeline, "ROOT_DIR", root_dir)
    monkeypatch.setattr(paper_pipeline, "OUTPUT_DIR", output_dir)

    base_config_path = root_dir / "research" / "experiments" / "baseline.json"
    base_config_path.parent.mkdir(parents=True, exist_ok=True)
    base_config_path.write_text(
        json.dumps(
            {
                "name": "base-run",
                "num_agents": 12,
                "panic_level": 0.25,
                "emergency_type": "fire",
            }
        ),
        encoding="utf-8",
    )

    batch_config_path = root_dir / "research" / "experiments" / "batches" / "paper_suite.json"
    batch_config_path.parent.mkdir(parents=True, exist_ok=True)
    batch_config_path.write_text(
        json.dumps(
            {
                "name": "paper_suite",
                "base_config": "research/experiments/baseline.json",
                "seeds": [2, 1],
                "variants": [
                    {"id": "full_model", "overrides": {}},
                ],
            }
        ),
        encoding="utf-8",
    )

    def _fake_run(config):
        run_name = config.name
        payload = {
            "config_hash": f"hash-{config.seed}",
            "config": {"name": run_name},
            "provenance": {
                "engine_version": "peopleflow-sim-v2",
                "floor_plan_id": "fp-paper",
                "floor_plan_revision": f"rev-{config.seed}",
                "seed": config.seed,
            },
            "metrics": {
                "total_evacuation_time": float(100 + config.seed),
                "safety_score": float(60 + config.seed),
                "survival_probability": 0.93,
            },
        }
        (output_dir / f"{run_name}.json").write_text(json.dumps(payload), encoding="utf-8")
        return payload

    monkeypatch.setattr(paper_pipeline, "run_experiment_sync", _fake_run)
    monkeypatch.setattr(paper_pipeline, "run_validation", lambda _path: {"overall_score": 0.91})

    result = paper_pipeline.run_paper_pipeline(
        str(batch_config_path),
        validate=True,
        artifacts_root=str(root_dir / "artifacts" / "paper_results"),
        copy_run_outputs=True,
    )

    artifact_dir = Path(result["artifact_dir"])
    assert (artifact_dir / "manifests").exists()
    assert (artifact_dir / "summaries").exists()
    assert (artifact_dir / "tables").exists()
    assert (artifact_dir / "figures").exists()
    assert (artifact_dir / "metadata").exists()
    assert (artifact_dir / "raw_runs").exists()

    assert (artifact_dir / "README.md").exists()
    assert (artifact_dir / "figures" / "README.md").exists()
    assert (artifact_dir / "metadata" / "publication_manifest.json").exists()
    assert (artifact_dir / "metadata" / "reproducibility.json").exists()
    assert (artifact_dir / "metadata" / "batch_config_snapshot.json").exists()
    assert (artifact_dir / "metadata" / "base_config_snapshot.json").exists()

    publication_manifest = json.loads((artifact_dir / "metadata" / "publication_manifest.json").read_text(encoding="utf-8"))
    assert publication_manifest["manifest_version"] == "peopleflow-publication-bundle-v1"
    assert publication_manifest["run_record_version"] == "peopleflow-experiment-run-v1"
    assert publication_manifest["seeds"] == [1, 2]
    assert publication_manifest["variants"] == ["full_model"]
    assert publication_manifest["runs"][0]["engine_version"] == "peopleflow-sim-v2"
    assert publication_manifest["runs"][0]["floor_plan_id"] == "fp-paper"

    assert Path(result["metrics_table"]).exists()
    assert result["copied_run_count"] == 2
    raw_runs = list((artifact_dir / "raw_runs").glob("*.json"))
    assert len(raw_runs) == 2


def test_run_paper_pipeline_rejects_empty_seed_or_variant(tmp_path, monkeypatch):
    root_dir = tmp_path / "repo"
    monkeypatch.setattr(paper_pipeline, "ROOT_DIR", root_dir)
    monkeypatch.setattr(paper_pipeline, "OUTPUT_DIR", root_dir / "research" / "experiments" / "output")

    base_config_path = root_dir / "research" / "experiments" / "baseline.json"
    base_config_path.parent.mkdir(parents=True, exist_ok=True)
    base_config_path.write_text(
        json.dumps(
            {
                "name": "base-run",
                "num_agents": 10,
                "panic_level": 0.2,
                "emergency_type": "fire",
            }
        ),
        encoding="utf-8",
    )

    bad_batch_path = root_dir / "research" / "experiments" / "batches" / "bad_suite.json"
    bad_batch_path.parent.mkdir(parents=True, exist_ok=True)
    bad_batch_path.write_text(
        json.dumps(
            {
                "name": "bad_suite",
                "base_config": "research/experiments/baseline.json",
                "seeds": [],
                "variants": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        paper_pipeline.run_paper_pipeline(str(bad_batch_path), validate=False)
