"""Measure wall-clock runtime/scalability for representative PeopleFlow layouts.

This script is intended to generate reproducible runtime evidence for manuscript tables.
"""

from __future__ import annotations

import csv
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any

# Keep imports consistent with the backend runtime environment.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.experiments.generate_journal_results import _rescale_floor_plan  # type: ignore
from app.services.floorplan_service import process_floor_plan_image  # type: ignore
from app.services.metrics_engine import MetricsEngine  # type: ignore
from app.sim.simulation_kernel import SimulationKernel  # type: ignore

ROOT_DIR = Path(__file__).resolve().parents[4]
OUTPUT_DIR = ROOT_DIR / "Research_Paper_IEEE"


def _mime_for_path(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".png":
        return "image/png"
    if suffix == ".webp":
        return "image/webp"
    return "image/jpeg"


def _run_single(
    floor_plan: dict[str, Any],
    num_agents: int,
    routing_policy: str,
    panic_level: float,
    seed: int,
    max_runtime_seconds: int = 300,
    max_steps: int = 1600,
    wall_clock_cap_seconds: float = 12.0,
) -> dict[str, Any]:
    config = {
        "seed": seed,
        "mode": "paper",
        "num_agents": num_agents,
        "emergency_type": "fire",
        "routing_policy": routing_policy,
        "panic_level": panic_level,
        "blocked_exits": [],
        "parameter_overrides": {"disable_hazards": True},
        "max_runtime_seconds": max_runtime_seconds,
    }

    kernel = SimulationKernel("runtime_probe", config)
    kernel.initialize(floor_plan)
    metrics = MetricsEngine()

    start = time.perf_counter()
    steps = 0
    while not kernel.is_complete() and steps < max_steps and (time.perf_counter() - start) < wall_clock_cap_seconds:
        frame = kernel.step(0.2)
        metrics.add_frame(frame)
        steps += 1

    elapsed = time.perf_counter() - start
    m = metrics.calculate_metrics()

    return {
        "wall_clock_s": elapsed,
        "steps": steps,
        "completed": bool(kernel.is_complete()),
        "sim_time_s": float(m.total_evacuation_time) if m.total_evacuation_time else float(steps * 0.2),
        "peak_density": float(m.peak_congestion_density) if m.peak_congestion_density else 0.0,
    }


def main() -> None:
    layouts = [
        (
            "Airport Terminal",
            ROOT_DIR / "apps" / "backend" / "app" / "experiments" / "input_floorplans" / "ieee_journal_blueprints" / "G_airport_bergen.jpg",
        ),
        (
            "Metro Station",
            ROOT_DIR / "apps" / "backend" / "app" / "experiments" / "input_floorplans" / "ieee_journal_blueprints" / "H_metro_taipei.jpg",
        ),
        (
            "Office Building",
            ROOT_DIR / "apps" / "backend" / "app" / "experiments" / "input_floorplans" / "ieee_journal_blueprints" / "C_office_dime.png",
        ),
        (
            "Plan3 (core set)",
            ROOT_DIR / "Research_Paper_IEEE" / "Floor_Plans" / "Plan3.jpg",
        ),
    ]

    repeats = 5
    num_agents = 80
    routing_policy = "least_crowded"
    panic_level = 0.3

    detail_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []

    for layout_name, layout_path in layouts:
        if not layout_path.exists():
            raise FileNotFoundError(f"Missing layout file: {layout_path}")

        print(f"Processing layout: {layout_name}")
        raw = process_floor_plan_image(_mime_for_path(layout_path), str(layout_path), {"mode": "traditional"})
        scaled = _rescale_floor_plan(raw)

        run_results: list[dict[str, Any]] = []
        for i in range(repeats):
            seed = 2400 + i
            result = _run_single(
                floor_plan=scaled,
                num_agents=num_agents,
                routing_policy=routing_policy,
                panic_level=panic_level,
                seed=seed,
            )
            run_results.append(result)
            detail_rows.append(
                {
                    "layout": layout_name,
                    "run": i + 1,
                    "seed": seed,
                    **result,
                }
            )
            print(
                f"  run {i + 1}/{repeats}: wall={result['wall_clock_s']:.3f}s, "
                f"steps={result['steps']}, sim_time={result['sim_time_s']:.2f}s"
            )

        walls = [r["wall_clock_s"] for r in run_results]
        steps = [r["steps"] for r in run_results]
        sims = [r["sim_time_s"] for r in run_results]
        done = sum(1 for r in run_results if r["completed"])

        summary_rows.append(
            {
                "layout": layout_name,
                "agents": num_agents,
                "runs": repeats,
                "wall_clock_mean_s": round(statistics.mean(walls), 3),
                "wall_clock_std_s": round(statistics.pstdev(walls), 3),
                "wall_clock_min_s": round(min(walls), 3),
                "wall_clock_max_s": round(max(walls), 3),
                "steps_mean": round(statistics.mean(steps), 1),
                "sim_time_mean_s": round(statistics.mean(sims), 2),
                "completion_rate": round(done / repeats, 2),
            }
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    detail_path = OUTPUT_DIR / "runtime_scalability_detail.json"
    summary_json_path = OUTPUT_DIR / "runtime_scalability_summary.json"
    summary_csv_path = OUTPUT_DIR / "runtime_scalability_summary.csv"

    detail_path.write_text(json.dumps(detail_rows, indent=2), encoding="utf-8")
    summary_json_path.write_text(json.dumps(summary_rows, indent=2), encoding="utf-8")

    with summary_csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    print(f"Wrote: {detail_path}")
    print(f"Wrote: {summary_json_path}")
    print(f"Wrote: {summary_csv_path}")


if __name__ == "__main__":
    main()
