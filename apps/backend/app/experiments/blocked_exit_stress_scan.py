"""Scan blocked-exit stress settings to identify a baseline failure case."""

from __future__ import annotations

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
LAYOUTS = [
    ("Metro", ROOT_DIR / "apps" / "backend" / "app" / "experiments" / "input_floorplans" / "ieee_journal_blueprints" / "H_metro_taipei.jpg"),
    ("Airport", ROOT_DIR / "apps" / "backend" / "app" / "experiments" / "input_floorplans" / "ieee_journal_blueprints" / "G_airport_bergen.jpg"),
    ("Plan3", ROOT_DIR / "Research_Paper_IEEE" / "Floor_Plans" / "Plan3.jpg"),
]


def _mime(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".png":
        return "image/png"
    if suffix == ".webp":
        return "image/webp"
    return "image/jpeg"


def run_once(floor_plan: dict[str, Any], policy: str, blocked_exits: list[str], num_agents: int, seed: int) -> tuple[float, float, bool]:
    config = {
        "seed": seed,
        "mode": "paper",
        "num_agents": num_agents,
        "emergency_type": "fire",
        "routing_policy": policy,
        "panic_level": 0.45,
        "blocked_exits": blocked_exits,
        "parameter_overrides": {"disable_hazards": True},
        "max_runtime_seconds": 240,
    }
    kernel = SimulationKernel("scan", config)
    kernel.initialize(floor_plan)
    metrics = MetricsEngine()

    start = time.perf_counter()
    steps = 0
    while not kernel.is_complete() and steps < 1800 and (time.perf_counter() - start) < 12.0:
        frame = kernel.step(0.2)
        metrics.add_frame(frame)
        steps += 1

    m = metrics.calculate_metrics()
    completion = frame.get("stats", {}).get("completion_percentage", 0.0) if "frame" in locals() else 0.0
    return float(m.total_evacuation_time or steps * 0.2), float(completion), bool(kernel.is_complete())


def main() -> None:
    occupancies = [120, 160, 200]
    policies = ["shortest_path", "least_crowded"]

    outcomes = []
    for layout_name, path in LAYOUTS:
        raw = process_floor_plan_image(_mime(path), str(path), {"mode": "traditional"})
        fp = _rescale_floor_plan(raw)
        exits = list(fp.get("exits") or [])
        blocked = [str(exits[0].get("id"))] if exits else []

        for occ in occupancies:
            for pol in policies:
                sims = [run_once(fp, pol, blocked, occ, 5000 + i) for i in range(5)]
                times = [s[0] for s in sims]
                comps = [s[1] for s in sims]
                dones = [s[2] for s in sims]
                outcomes.append(
                    {
                        "layout": layout_name,
                        "occupancy": occ,
                        "policy": pol,
                        "time_mean": round(statistics.mean(times), 2),
                        "completion_pct_mean": round(statistics.mean(comps), 2),
                        "completion_rate": round(statistics.mean([1.0 if d else 0.0 for d in dones]), 2),
                    }
                )
                print(outcomes[-1])

    out = ROOT_DIR / "Research_Paper_IEEE" / "blocked_exit_stress_scan.json"
    out.write_text(json.dumps(outcomes, indent=2), encoding="utf-8")
    print(f"Wrote: {out}")


if __name__ == "__main__":
    main()
