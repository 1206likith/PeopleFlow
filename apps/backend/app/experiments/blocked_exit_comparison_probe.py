"""Run a focused blocked-exit policy comparison for manuscript evidence.

Outputs:
- Research_Paper_IEEE/blocked_exit_policy_comparison.csv
- Research_Paper_IEEE/blocked_exit_policy_comparison.json
"""

from __future__ import annotations

import csv
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.experiments.generate_journal_results import _rescale_floor_plan  # type: ignore
from app.services.floorplan_service import process_floor_plan_image  # type: ignore
from app.services.metrics_engine import MetricsEngine  # type: ignore
from app.sim.simulation_kernel import SimulationKernel  # type: ignore

ROOT_DIR = Path(__file__).resolve().parents[4]
OUTPUT_DIR = ROOT_DIR / "Research_Paper_IEEE"
METRO_LAYOUT = ROOT_DIR / "apps" / "backend" / "app" / "experiments" / "input_floorplans" / "ieee_journal_blueprints" / "H_metro_taipei.jpg"


def _run_once(
    floor_plan: dict[str, Any],
    routing_policy: str,
    blocked_exits: list[str],
    num_agents: int,
    seed: int,
    max_steps: int = 1500,
    wall_cap_s: float = 12.0,
) -> dict[str, Any]:
    config = {
        "seed": seed,
        "mode": "paper",
        "num_agents": num_agents,
        "emergency_type": "fire",
        "routing_policy": routing_policy,
        "panic_level": 0.35,
        "blocked_exits": blocked_exits,
        "parameter_overrides": {"disable_hazards": True},
        "max_runtime_seconds": 240,
    }

    kernel = SimulationKernel("blocked_exit_probe", config)
    kernel.initialize(floor_plan)
    metrics = MetricsEngine()

    start = time.perf_counter()
    steps = 0
    last_frame: dict[str, Any] | None = None
    while not kernel.is_complete() and steps < max_steps and (time.perf_counter() - start) < wall_cap_s:
        last_frame = kernel.step(0.2)
        metrics.add_frame(last_frame)
        steps += 1

    if last_frame is None:
        last_frame = kernel.current_frame()

    computed = metrics.calculate_metrics()
    stats = last_frame.get("stats", {}) or {}
    completion_pct = float(stats.get("completion_percentage") or 0.0)

    return {
        "steps": steps,
        "wall_clock_s": time.perf_counter() - start,
        "sim_time_s": float(computed.total_evacuation_time or (steps * 0.2)),
        "peak_density": float(computed.peak_congestion_density or 0.0),
        "completion_pct": completion_pct,
        "completed": bool(kernel.is_complete()),
    }


def _mime(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".png":
        return "image/png"
    if suffix == ".webp":
        return "image/webp"
    return "image/jpeg"


def main() -> None:
    if not METRO_LAYOUT.exists():
        raise FileNotFoundError(f"Missing layout file: {METRO_LAYOUT}")

    raw = process_floor_plan_image(_mime(METRO_LAYOUT), str(METRO_LAYOUT), {"mode": "traditional"})
    floor_plan = _rescale_floor_plan(raw)

    exits = list(floor_plan.get("exits") or [])
    if not exits:
        raise RuntimeError("No exits detected for blocked-exit probe")

    blocked_exit_id = str(exits[0].get("id"))
    policies = [
        ("shortest_path", "Nearest/shortest baseline"),
        ("least_crowded", "Congestion-aware (PeopleFlow)"),
    ]

    num_runs = 10
    num_agents = 120

    rows: list[dict[str, Any]] = []
    summary: list[dict[str, Any]] = []

    for policy_key, policy_label in policies:
        results = []
        for i in range(num_runs):
            seed = 3100 + i
            run = _run_once(
                floor_plan=floor_plan,
                routing_policy=policy_key,
                blocked_exits=[blocked_exit_id],
                num_agents=num_agents,
                seed=seed,
            )
            run_row = {
                "policy": policy_key,
                "policy_label": policy_label,
                "run": i + 1,
                "seed": seed,
                **run,
            }
            rows.append(run_row)
            results.append(run)

        summary.append(
            {
                "policy": policy_key,
                "policy_label": policy_label,
                "runs": num_runs,
                "num_agents": num_agents,
                "blocked_exit_id": blocked_exit_id,
                "evac_time_mean_s": round(statistics.mean([r["sim_time_s"] for r in results]), 2),
                "evac_time_std_s": round(statistics.pstdev([r["sim_time_s"] for r in results]), 2),
                "peak_density_mean": round(statistics.mean([r["peak_density"] for r in results]), 2),
                "completion_pct_mean": round(statistics.mean([r["completion_pct"] for r in results]), 2),
                "completion_rate": round(statistics.mean([1.0 if r["completed"] else 0.0 for r in results]), 2),
                "wall_clock_mean_s": round(statistics.mean([r["wall_clock_s"] for r in results]), 3),
            }
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUTPUT_DIR / "blocked_exit_policy_comparison.json"
    csv_path = OUTPUT_DIR / "blocked_exit_policy_comparison.csv"
    detail_path = OUTPUT_DIR / "blocked_exit_policy_comparison_detail.csv"

    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary[0].keys()))
        writer.writeheader()
        writer.writerows(summary)

    with detail_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote: {json_path}")
    print(f"Wrote: {csv_path}")
    print(f"Wrote: {detail_path}")


if __name__ == "__main__":
    main()
