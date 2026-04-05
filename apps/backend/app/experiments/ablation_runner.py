"""
Batch ablation runner.
Generates permutations of ablation toggles.
"""
from itertools import product
from typing import List

from . import OUTPUT_DIR
from .config import ExperimentConfig
from .ablation import AblationConfig
from .artifact_manifests import write_suite_manifest
from .runner import run_experiment_sync


def run_ablation_grid(base: ExperimentConfig) -> List[dict]:
    flags = ["use_social_force", "use_pathfinding", "use_behavioral_decisions", "use_hazard_effects"]
    results = []
    summary_rows = []

    for values in product([False, True], repeat=len(flags)):
        ablation = AblationConfig(**dict(zip(flags, values)))
        name = f"{base.name}__" + "__".join(f"{k}={int(v)}" for k, v in zip(flags, values))
        cfg = base.model_copy(deep=True)
        cfg.name = name
        cfg.ablation = ablation
        result = run_experiment_sync(cfg)
        results.append(result)
        summary_rows.append(
            {
                "name": result.get("config", {}).get("name"),
                "config_hash": result.get("config_hash"),
                "ablation": result.get("config", {}).get("ablation", {}),
                "output_file": f"{result.get('config', {}).get('name')}.json",
            }
        )

    write_suite_manifest(
        suite_type="ablation",
        base_config_payload=base.model_dump(),
        results=summary_rows,
        output_path=OUTPUT_DIR / "ablation_summary.json",
        best=None,
        metadata={"grid_size": len(summary_rows)},
    )

    return results
