"""Recompute manuscript values for Plan3 timeout analysis and supplementary S1-S5 expansion.

Outputs:
- Research_Paper_IEEE/plan3_s3_blocked_tmax_sweep.json
- Research_Paper_IEEE/supplementary_layouts_s1_s5.csv
- Research_Paper_IEEE/supplementary_layouts_s1_s5_summary.json
"""

from __future__ import annotations

import csv
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "apps" / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.experiments.generate_journal_results import _rescale_floor_plan  # type: ignore
from app.services.floorplan_service import process_floor_plan_image  # type: ignore
from app.services.metrics_engine import MetricsEngine  # type: ignore
from app.sim.simulation_kernel import SimulationKernel  # type: ignore


PAPER_DIR = ROOT_DIR / "Research_Paper_IEEE"

PLAN3_PATH = PAPER_DIR / "Floor_Plans" / "Plan3.jpg"
SUPPLEMENTARY_LAYOUTS: dict[str, Path] = {
    "Airport terminal": BACKEND_DIR / "app" / "experiments" / "input_floorplans" / "ieee_journal_blueprints" / "G_airport_bergen.jpg",
    "Metro station": BACKEND_DIR / "app" / "experiments" / "input_floorplans" / "ieee_journal_blueprints" / "H_metro_taipei.jpg",
    "Office building": BACKEND_DIR / "app" / "experiments" / "input_floorplans" / "ieee_journal_blueprints" / "C_office_dime.png",
}

SCENARIOS: list[tuple[str, int, str, float, bool]] = [
    ("S1_Baseline", 80, "shortest_path", 0.3, False),
    ("S2_HighOcc", 120, "shortest_path", 0.3, False),
    ("S3_Blocked", 80, "shortest_path", 0.3, True),
    ("S4_Routing", 80, "least_crowded", 0.3, False),
    ("S5_Panic", 80, "shortest_path", 0.8, False),
]


def _mime(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".png":
        return "image/png"
    if suffix == ".webp":
        return "image/webp"
    return "image/jpeg"


def _load_scaled_floor_plan(path: Path) -> dict[str, Any]:
    raw = process_floor_plan_image(_mime(path), str(path), {"mode": "traditional"})
    return _rescale_floor_plan(raw)


def _simulate_once(
    floor_plan: dict[str, Any],
    *,
    seed: int,
    num_agents: int,
    routing_policy: str,
    panic_level: float,
    blocked_exits: list[str],
    max_runtime_seconds: int,
) -> dict[str, Any]:
    dt = 0.2
    max_steps = int(max_runtime_seconds / dt)

    config = {
        "seed": seed,
        "mode": "paper",
        "num_agents": int(num_agents),
        "emergency_type": "fire",
        "routing_policy": routing_policy,
        "panic_level": float(panic_level),
        "blocked_exits": list(blocked_exits),
        "parameter_overrides": {"disable_hazards": True},
        "max_runtime_seconds": int(max_runtime_seconds),
    }

    kernel = SimulationKernel("paper_rerun", config)
    kernel.initialize(floor_plan)
    metrics = MetricsEngine()
    frame: dict[str, Any] | None = None

    started = time.perf_counter()
    for _ in range(max_steps):
        if kernel.is_complete():
            break
        frame = kernel.step(dt)
        metrics.add_frame(frame)
    wallclock_s = time.perf_counter() - started

    stats = (frame or {}).get("stats", {})
    m = metrics.calculate_metrics()
    sim_time_s = float((frame or {}).get("timestamp", len(metrics.frame_history) * dt))
    total_time = float(m.total_evacuation_time) if float(m.total_evacuation_time or 0.0) > 0 else sim_time_s

    remaining = int(stats.get("remaining", config["num_agents"]))
    evacuated = int(stats.get("evacuated", 0))
    completion_pct = float(stats.get("completion_percentage", 0.0))
    completed = bool(kernel.is_complete())

    return {
        "seed": seed,
        "time_s": total_time,
        "sim_time_s": sim_time_s,
        "peak_density": float(m.peak_congestion_density or 0.0),
        "completion_pct": completion_pct,
        "evacuated": evacuated,
        "remaining": remaining,
        "completed": completed,
        "steps": len(metrics.frame_history),
        "wallclock_s": round(wallclock_s, 3),
    }


def _summarize_runs(runs: list[dict[str, Any]]) -> dict[str, Any]:
    times = [float(r["time_s"]) for r in runs]
    densities = [float(r["peak_density"]) for r in runs]
    completion = [float(r["completion_pct"]) for r in runs]
    completed = [1.0 if bool(r["completed"]) else 0.0 for r in runs]
    return {
        "mean_time": round(statistics.mean(times), 2),
        "std_time": round(statistics.pstdev(times), 2),
        "mean_density": round(statistics.mean(densities), 2),
        "std_density": round(statistics.pstdev(densities), 2),
        "mean_completion_pct": round(statistics.mean(completion), 2),
        "completion_rate": round(statistics.mean(completed), 2),
    }


def run_plan3_tmax_sweep(seeds: list[int]) -> dict[str, Any]:
    floor_plan = _load_scaled_floor_plan(PLAN3_PATH)
    exits = list(floor_plan.get("exits") or [])
    blocked_exit = str(exits[0].get("id")) if exits else ""
    blocked = [blocked_exit] if blocked_exit else []

    sweep: dict[str, Any] = {
        "case": "Plan3",
        "scenario": "S3_Blocked",
        "blocked_exit_id": blocked_exit,
        "runs_per_tmax": len(seeds),
        "results": {},
    }

    for tmax in (300, 350, 400):
        runs = [
            _simulate_once(
                floor_plan,
                seed=s,
                num_agents=80,
                routing_policy="shortest_path",
                panic_level=0.3,
                blocked_exits=blocked,
                max_runtime_seconds=tmax,
            )
            for s in seeds
        ]
        sweep["results"][str(tmax)] = {
            **_summarize_runs(runs),
            "runs": runs,
        }
        print(
            f"Plan3 S3 tmax={tmax}: mean_time={sweep['results'][str(tmax)]['mean_time']} "
            f"completion_rate={sweep['results'][str(tmax)]['completion_rate']}"
        )

    out_path = PAPER_DIR / "plan3_s3_blocked_tmax_sweep.json"
    out_path.write_text(json.dumps(sweep, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")
    return sweep


def run_supplementary_matrix(seeds: list[int], max_runtime_seconds: int = 300) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for layout_name, path in SUPPLEMENTARY_LAYOUTS.items():
        floor_plan = _load_scaled_floor_plan(path)
        exits = list(floor_plan.get("exits") or [])
        default_blocked = [str(exits[0].get("id"))] if exits else []

        for scenario_name, num_agents, policy, panic, use_blocked in SCENARIOS:
            blocked = default_blocked if use_blocked else []
            runs = [
                _simulate_once(
                    floor_plan,
                    seed=s,
                    num_agents=num_agents,
                    routing_policy=policy,
                    panic_level=panic,
                    blocked_exits=blocked,
                    max_runtime_seconds=max_runtime_seconds,
                )
                for s in seeds
            ]
            summary = _summarize_runs(runs)
            row = {
                "layout": layout_name,
                "scenario": scenario_name,
                "num_agents": num_agents,
                "routing_policy": policy,
                "blocked_exit_id": default_blocked[0] if (use_blocked and default_blocked) else "",
                "mean_time": summary["mean_time"],
                "std_time": summary["std_time"],
                "mean_density": summary["mean_density"],
                "std_density": summary["std_density"],
                "mean_completion_pct": summary["mean_completion_pct"],
                "completion_rate": summary["completion_rate"],
            }
            rows.append(row)
            print(
                f"{layout_name} {scenario_name}: mean_time={row['mean_time']} "
                f"completion_rate={row['completion_rate']}"
            )

    csv_path = PAPER_DIR / "supplementary_layouts_s1_s5.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    json_path = PAPER_DIR / "supplementary_layouts_s1_s5_summary.json"
    json_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"Wrote {csv_path}")
    print(f"Wrote {json_path}")
    return rows


def main() -> None:
    seeds = [6100 + i for i in range(10)]
    print("Running Plan3 S3 Tmax sweep...")
    run_plan3_tmax_sweep(seeds)
    print("Running supplementary layouts S1-S5 matrix...")
    run_supplementary_matrix(seeds, max_runtime_seconds=300)
    print("Done.")


if __name__ == "__main__":
    main()
