"""
Application service for experiment, benchmark, and publication-bundle execution.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

from app.core.filesystem_hardening import get_safe_artifact_path
from app.experiments import EXPERIMENTS_DIR, ROOT_DIR, OUTPUT_DIR
from app.experiments.ablation_runner import run_ablation_grid
from app.experiments.benchmarks import run_corridor_benchmark, run_multi_exit_benchmark
from app.experiments.calibration_runner import run_calibration
from app.experiments.config import ExperimentConfig
from app.experiments.optimizer import run_bayesian_optimization
from app.experiments.paper_pipeline import run_paper_pipeline
from app.experiments.runner import run_experiment_sync
from app.validation.runner import run_validation
from app.services.experiment_artifact_service import experiment_artifact_service


class ExperimentExecutionService:
    _BENCHMARK_RUNNERS = {
        "corridor": (
            run_corridor_benchmark,
            "Single-exit corridor throughput benchmark for bottleneck and flow behavior.",
            60,
        ),
        "multi_exit": (
            run_multi_exit_benchmark,
            "Multi-exit room benchmark for load balancing and exit utilization behavior.",
            80,
        ),
    }

    @staticmethod
    def _catalog_summary() -> Dict[str, Any]:
        return experiment_artifact_service.build_catalog_summary()

    @staticmethod
    def _persist_validation(output_name: str, validations: Dict[str, Any]) -> None:
        out_path = OUTPUT_DIR / f"{output_name}.json"
        if not out_path.exists():
            return
        data = json.loads(out_path.read_text(encoding="utf-8-sig"))
        data["validation"] = validations
        out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    @staticmethod
    def _resolve_repo_path(path_value: str) -> Path:
        raw = Path(path_value)
        if raw.is_absolute():
            return raw
        return ROOT_DIR / raw

    @staticmethod
    def _staging_dir() -> Path:
        staging_dir = get_safe_artifact_path("experiments-api.tmp", subdir="cache").parent / "experiments_api"
        staging_dir.mkdir(parents=True, exist_ok=True)
        return staging_dir

    def _stage_inline_json(self, prefix: str, payload: Dict[str, Any]) -> Path:
        staged_path = self._staging_dir() / f"{prefix}_{uuid4().hex}.json"
        staged_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return staged_path

    def list_benchmarks(self) -> Dict[str, Any]:
        return {
            "catalog_version": "peopleflow-executable-benchmarks-v1",
            "benchmarks": [
                {
                    "name": name,
                    "description": description,
                    "default_num_agents": default_num_agents,
                }
                for name, (_runner, description, default_num_agents) in self._BENCHMARK_RUNNERS.items()
            ],
        }

    def get_benchmark_definition(self, benchmark_name: str) -> Dict[str, Any]:
        entry = self._BENCHMARK_RUNNERS.get(benchmark_name)
        if entry is None:
            raise LookupError("Benchmark not found")
        _, description, default_num_agents = entry
        return {
            "name": benchmark_name,
            "description": description,
            "default_num_agents": default_num_agents,
        }

    def run_experiment(self, config: ExperimentConfig, *, validate: bool = False) -> Dict[str, Any]:
        result = run_experiment_sync(config)
        if validate:
            validations = run_validation(str(OUTPUT_DIR / f"{result['config']['name']}.json"))
            result["validation"] = validations
            self._persist_validation(result["config"]["name"], validations)
        return {
            "execution_type": "single_run",
            "result": result,
            "catalog": self._catalog_summary(),
        }

    def run_ablation(self, base_config: ExperimentConfig, *, validate: bool = False) -> Dict[str, Any]:
        results = run_ablation_grid(base_config)
        if validate:
            for result in results:
                output_name = result.get("config", {}).get("name")
                if not output_name:
                    continue
                validations = run_validation(str(OUTPUT_DIR / f"{output_name}.json"))
                result["validation"] = validations
                self._persist_validation(output_name, validations)
        summary_path = OUTPUT_DIR / "ablation_summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8-sig")) if summary_path.exists() else {}
        return {
            "execution_type": "ablation",
            "summary": summary,
            "results_count": len(results),
            "catalog": self._catalog_summary(),
        }

    def run_calibration(
        self,
        base_config: ExperimentConfig,
        *,
        calibration_config: Optional[Dict[str, Any]] = None,
        calibration_config_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        resolved_path: Optional[Path] = None
        if calibration_config is not None:
            resolved_path = self._stage_inline_json("calibration", calibration_config)
        elif calibration_config_path:
            resolved_path = self._resolve_repo_path(calibration_config_path)
        summary = run_calibration(
            base_config,
            calibration_config_path=str(resolved_path) if resolved_path is not None else None,
        )
        return {
            "execution_type": "calibration",
            "summary": summary,
            "catalog": self._catalog_summary(),
        }

    def run_optimization(
        self,
        base_config: ExperimentConfig,
        *,
        optimization_config: Optional[Dict[str, Any]] = None,
        optimization_config_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        resolved_path: Optional[Path] = None
        if optimization_config is not None:
            resolved_path = self._stage_inline_json("optimization", optimization_config)
        elif optimization_config_path:
            resolved_path = self._resolve_repo_path(optimization_config_path)
        summary = run_bayesian_optimization(
            base_config,
            optimization_config_path=str(resolved_path) if resolved_path is not None else None,
        )
        return {
            "execution_type": "optimization",
            "summary": summary,
            "catalog": self._catalog_summary(),
        }

    def run_publication_bundle(
        self,
        *,
        batch_config: Optional[Dict[str, Any]] = None,
        batch_config_path: Optional[str] = None,
        validate: bool = True,
        artifacts_root: Optional[str] = None,
        copy_run_outputs: bool = True,
    ) -> Dict[str, Any]:
        resolved_path: Optional[Path] = None
        if batch_config is not None:
            resolved_path = self._stage_inline_json("paper_bundle", batch_config)
        elif batch_config_path:
            resolved_path = self._resolve_repo_path(batch_config_path)
        else:
            resolved_path = EXPERIMENTS_DIR / "batches" / "paper_baseline_suite.json"

        bundle = run_paper_pipeline(
            str(resolved_path),
            validate=validate,
            artifacts_root=artifacts_root,
            copy_run_outputs=copy_run_outputs,
        )
        return {
            "execution_type": "publication_bundle",
            "bundle": bundle,
            "catalog": self._catalog_summary(),
        }

    def run_benchmark(self, benchmark_name: str, *, num_agents: Optional[int] = None) -> Dict[str, Any]:
        definition = self.get_benchmark_definition(benchmark_name)
        runner, description, default_num_agents = self._BENCHMARK_RUNNERS[benchmark_name]
        result = runner(num_agents=num_agents or default_num_agents)
        return {
            "execution_type": "benchmark",
            "benchmark": definition["name"],
            "description": description,
            "result": result,
            "catalog": self._catalog_summary(),
        }


experiment_execution_service = ExperimentExecutionService()
