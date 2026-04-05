"""Generate paper-ready case-study assets from 4 uploaded floor plans.

Inputs:
- app/experiments/input_floorplans/plan1.jpg
- app/experiments/input_floorplans/plan2.jpg
- app/experiments/input_floorplans/plan3.jpg
- app/experiments/input_floorplans/plan4.jpg

Outputs (written to app/experiments/output):
- paper_case_studies.json
- paper_case_studies.csv
- fig_case_layouts.png
- fig_floorplan.png
- fig_simulation.png
- fig_density.png
- fig_pipeline.png
- fig_architecture.png
"""

from __future__ import annotations

import csv
import json
import math
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import matplotlib.pyplot as plt  # type: ignore
import numpy as np  # type: ignore

from app.services.floorplan_service import process_floor_plan_image
from app.services.metrics_engine import MetricsEngine
from app.sim.simulation_kernel import SimulationKernel


EXPERIMENTS_DIR = Path(__file__).resolve().parent
INPUT_DIR = EXPERIMENTS_DIR / "input_floorplans"
OUTPUT_DIR = EXPERIMENTS_DIR / "output"


def _ensure_exits(floor_plan: Dict[str, Any]) -> None:
    exits = list(floor_plan.get("exits") or [])
    bounds = floor_plan.get("building_bounds") or {}
    min_x = float(bounds.get("min_x", 0.0))
    max_x = float(bounds.get("max_x", 100.0))
    min_y = float(bounds.get("min_y", 0.0))
    max_y = float(bounds.get("max_y", 100.0))
    cy = (min_y + max_y) * 0.5

    if len(exits) >= 2:
        floor_plan["exits"] = exits
        return

    default_exits = [
        {"id": "exit_left", "x": min_x + 1.0, "y": cy, "z": cy, "width": 2.0, "capacity": 100},
        {"id": "exit_right", "x": max_x - 1.0, "y": cy, "z": cy, "width": 2.0, "capacity": 100},
    ]
    floor_plan["exits"] = exits + default_exits[: max(0, 2 - len(exits))]


def _rescale_floor_plan(floor_plan: Dict[str, Any], target_max_dim: float = 80.0) -> Dict[str, Any]:
    bounds = dict(floor_plan.get("building_bounds") or {})
    min_x = float(bounds.get("min_x", 0.0))
    max_x = float(bounds.get("max_x", 100.0))
    min_y = float(bounds.get("min_y", 0.0))
    max_y = float(bounds.get("max_y", 100.0))
    width = max(1.0, max_x - min_x)
    height = max(1.0, max_y - min_y)
    scale = max(width, height) / target_max_dim if max(width, height) > target_max_dim else 1.0

    def sx(x: float) -> float:
        return (float(x) - min_x) / scale

    def sy(y: float) -> float:
        return (float(y) - min_y) / scale

    walls: List[Dict[str, Any]] = []
    # Cap wall segments to keep simulation runtime predictable for complex CAD-like plans.
    for wall in list(floor_plan.get("detected_walls", []))[:300]:
        walls.append(
            {
                "x1": sx(wall.get("x1", 0.0)),
                "y1": sy(wall.get("y1", 0.0)),
                "x2": sx(wall.get("x2", 0.0)),
                "y2": sy(wall.get("y2", 0.0)),
            }
        )

    exits: List[Dict[str, Any]] = []
    for idx, exit_data in enumerate(floor_plan.get("exits", []), start=1):
        ex = sx(exit_data.get("x", 0.0))
        ey = sy(exit_data.get("z", exit_data.get("y", 0.0)))
        width_scaled = max(1.2, float(exit_data.get("width", 2.0)) / scale)
        exits.append(
            {
                "id": str(exit_data.get("id") or f"exit_{idx}"),
                "x": ex,
                "y": ey,
                "z": ey,
                "width": width_scaled,
                "capacity": max(80, int(float(exit_data.get("capacity", 100)))),
            }
        )

    obstacles: List[Dict[str, Any]] = []
    for obstacle in floor_plan.get("detected_obstacles", []):
        ox = sx(obstacle.get("x", 0.0))
        oy = sy(obstacle.get("z", obstacle.get("y", 0.0)))
        ow = max(0.2, float(obstacle.get("width", 0.6)) / scale)
        oh = max(0.2, float(obstacle.get("height", obstacle.get("depth", 0.6))) / scale)
        obstacles.append({"x": ox, "y": oy, "width": ow, "height": oh})

    scaled = {
        "building_bounds": {
            "min_x": 0.0,
            "min_y": 0.0,
            "max_x": width / scale,
            "max_y": height / scale,
        },
        "detected_walls": walls,
        "detected_obstacles": obstacles,
        "rooms": [],
        "hazards": [],
        "image_dimensions": {"width": width / scale, "height": height / scale},
        "exits": exits,
        "metadata": {
            "source_scale": scale,
            "source_width": width,
            "source_height": height,
        },
    }
    _ensure_exits(scaled)
    return scaled


def _from_image(path: Path) -> Dict[str, Any]:
    detected = process_floor_plan_image("image/jpeg", str(path), {"mode": "traditional"})
    fp = {
        "building_bounds": detected.get("building_bounds") or {"min_x": 0.0, "min_y": 0.0, "max_x": 100.0, "max_y": 100.0},
        "detected_walls": detected.get("walls", []),
        "detected_obstacles": detected.get("obstacles", []),
        "rooms": detected.get("rooms", []),
        "hazards": [],
        "image_dimensions": detected.get("image_dimensions", {}),
        "exits": detected.get("exits", []),
    }
    _ensure_exits(fp)
    return _rescale_floor_plan(fp)


def _simulate_case(
    case_id: str,
    scenario_id: str,
    floor_plan: Dict[str, Any],
    *,
    num_agents: int,
    routing_policy: str,
    seed: int,
    panic_level: float = 0.32,
    max_runtime_seconds: int = 90,
    hard_wall_seconds: float = 18.0,
    capture_frames: bool = False,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
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
    kernel = SimulationKernel(f"paper-{case_id}-{scenario_id}", config)
    kernel.initialize(floor_plan)

    metrics_engine = MetricsEngine()
    frames: List[Dict[str, Any]] = []
    steps = 0
    max_steps = int(max_runtime_seconds / 0.2) * 5
    started = time.perf_counter()

    while not kernel.is_complete() and steps < max_steps:
        frame = kernel.step(0.2)
        metrics_engine.add_frame(frame)
        if capture_frames or (steps % 5 == 0):
            frames.append(json.loads(json.dumps(frame)))
        steps += 1
        if (time.perf_counter() - started) >= hard_wall_seconds:
            break

    metrics = metrics_engine.calculate_metrics()
    evacuation_distribution = list(metrics.evacuation_time_distribution or [])
    clearance_90 = float(np.percentile(evacuation_distribution, 90)) if evacuation_distribution else None

    result = {
        "case_id": case_id,
        "scenario_id": scenario_id,
        "num_agents": num_agents,
        "routing_policy": routing_policy,
        "blocked_exits": [],
        "seed": seed,
        "panic_level": panic_level,
        "disable_hazards": True,
        "completion_threshold_pct": 95.0,
        "terminal_time_s": round(float(kernel.engine.time), 3),
        "operational_clearance_time_s": round(float(metrics.total_evacuation_time), 3),
        "clearance_90_s": round(clearance_90, 3) if clearance_90 is not None else None,
        "peak_density": round(float(metrics.peak_congestion_density), 3),
        "congestion_duration_s": round(float(metrics.congestion_duration), 3),
        "bottleneck_count": int(len(metrics.bottleneck_locations)),
        "completed_agents": int(kernel.engine.evacuated_count),
        "completed_pct": round(float(kernel.engine.evacuated_count / max(num_agents, 1) * 100.0), 1),
        "exit_counts": {},
        "exit_imbalance_index": None,
    }
    return result, frames


def _draw_floor_plan(ax: Any, floor_plan: Dict[str, Any], title: str, frame: Dict[str, Any] | None = None) -> None:
    bounds = floor_plan.get("building_bounds") or {}
    min_x = float(bounds.get("min_x", 0.0))
    max_x = float(bounds.get("max_x", 100.0))
    min_y = float(bounds.get("min_y", 0.0))
    max_y = float(bounds.get("max_y", 100.0))

    ax.set_xlim(min_x - 1, max_x + 1)
    ax.set_ylim(min_y - 1, max_y + 1)
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=10)
    ax.set_xticks([])
    ax.set_yticks([])

    for wall in floor_plan.get("detected_walls", []):
        ax.plot(
            [float(wall.get("x1", 0.0)), float(wall.get("x2", 0.0))],
            [float(wall.get("y1", 0.0)), float(wall.get("y2", 0.0))],
            color="#202833",
            linewidth=1.8,
        )

    for exit_data in floor_plan.get("exits", []):
        ex = float(exit_data.get("x", 0.0))
        ez = float(exit_data.get("z", exit_data.get("y", 0.0)))
        ew = float(exit_data.get("width", 1.0))
        ax.plot([ex - ew / 2, ex + ew / 2], [ez, ez], color="#15b8a6", linewidth=4.0, solid_capstyle="round")

    if frame is not None:
        agents = frame.get("agents", [])
        xs = [float(agent.get("x", 0.0)) for agent in agents if agent.get("status") != "evacuated"]
        zs = [float(agent.get("z", agent.get("y", 0.0))) for agent in agents if agent.get("status") != "evacuated"]
        if xs and zs:
            ax.scatter(xs, zs, s=8, color="#4169e1", alpha=0.5, edgecolors="none")


def _write_case_layouts_figure(case_layouts: Dict[str, Dict[str, Any]]) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    axes_flat = axes.flatten()
    for ax, (case_id, payload) in zip(axes_flat, case_layouts.items()):
        _draw_floor_plan(ax, payload, case_id)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig_case_layouts.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def _write_floorplan_figure(case_layout: Dict[str, Any], title: str) -> None:
    fig, ax = plt.subplots(figsize=(5.4, 4.6))
    _draw_floor_plan(ax, case_layout, title)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig_floorplan.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def _write_simulation_figure(case_layout: Dict[str, Any], frames: List[Dict[str, Any]]) -> None:
    sample_indices = [0, max(0, len(frames) // 2), max(0, len(frames) - 1)]
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    for ax, index, label in zip(axes, sample_indices, ["Start", "Mid-run", "Operational clearance"]):
        frame = frames[index] if frames else None
        timestamp = float(frame.get("timestamp", 0.0)) if frame else 0.0
        _draw_floor_plan(ax, case_layout, f"{label} ({timestamp:.1f}s)", frame=frame)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig_simulation.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def _write_density_figure(case_layout: Dict[str, Any], frames: List[Dict[str, Any]]) -> None:
    bounds = case_layout.get("building_bounds") or {}
    min_x = float(bounds.get("min_x", 0.0))
    max_x = float(bounds.get("max_x", 100.0))
    min_y = float(bounds.get("min_y", 0.0))
    max_y = float(bounds.get("max_y", 100.0))

    xs: List[float] = []
    zs: List[float] = []
    for frame in frames:
        for agent in frame.get("agents", []):
            if agent.get("status") == "evacuated":
                continue
            xs.append(float(agent.get("x", 0.0)))
            zs.append(float(agent.get("z", agent.get("y", 0.0))))

    fig, ax = plt.subplots(figsize=(5.2, 4.8))
    if xs and zs:
        hist = ax.hist2d(xs, zs, bins=28, range=[[min_x, max_x], [min_y, max_y]], cmap="magma")
        fig.colorbar(hist[3], ax=ax, fraction=0.046, pad=0.04, label="Occupancy intensity")
    ax.set_title("Density Heatmap")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_aspect("equal")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig_density.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def _write_pipeline_figure() -> None:
    fig, ax = plt.subplots(figsize=(9.2, 2.4))
    ax.axis("off")
    labels = [
        "Floor-plan\nupload",
        "Geometry\nextraction",
        "Session\ncreation",
        "Scenario\nexecution",
        "Replay +\nanalytics",
        "Artifact-backed\nreporting",
    ]
    xs = np.linspace(0.08, 0.92, len(labels))
    box_width = 0.14
    box_half_width = box_width * 0.5
    connector_pad = 0.008
    for index, (x, label) in enumerate(zip(xs, labels)):
        rect = plt.Rectangle((x - box_half_width, 0.35), box_width, 0.32, facecolor="#eef4ff", edgecolor="#2a5bd7", linewidth=1.6)
        ax.add_patch(rect)
        ax.text(x, 0.51, label, ha="center", va="center", fontsize=8)
        if index < len(labels) - 1:
            start_x = x + box_half_width + connector_pad
            end_x = xs[index + 1] - box_half_width - connector_pad
            ax.annotate("", xy=(end_x, 0.51), xytext=(start_x, 0.51), arrowprops={"arrowstyle": "->", "lw": 1.4})
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig_pipeline.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def _write_architecture_figure() -> None:
    fig, ax = plt.subplots(figsize=(8.4, 3.8))
    ax.axis("off")
    blocks = [
        (0.05, 0.58, 0.24, 0.24, "#eef4ff", "Designer\nUpload + exit edits"),
        (0.38, 0.58, 0.24, 0.24, "#eef4ff", "Simulation studio\nLive run + replay"),
        (0.71, 0.58, 0.24, 0.24, "#eef4ff", "Experiments dashboard\nArtifacts + comparison"),
        (0.2, 0.15, 0.24, 0.22, "#f7f9fc", "Backend services\nProcessing + sessions"),
        (0.56, 0.15, 0.24, 0.22, "#f7f9fc", "Persistence\nSQLite + JSON artifacts"),
    ]
    for x, y, w, h, color, label in blocks:
        rect = plt.Rectangle((x, y), w, h, facecolor=color, edgecolor="#334155", linewidth=1.5)
        ax.add_patch(rect)
        ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", fontsize=9)
    arrows = [((0.29, 0.58), (0.32, 0.37)), ((0.50, 0.58), (0.50, 0.37)), ((0.71, 0.58), (0.68, 0.37)), ((0.44, 0.26), (0.56, 0.26))]
    for start, end in arrows:
        ax.annotate("", xy=end, xytext=start, arrowprops={"arrowstyle": "->", "lw": 1.5})
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig_architecture.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def _write_results(results: List[Dict[str, Any]]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "bundle_version": "peopleflow-paper-case-studies-v2-input4",
        "generated_from": "app.experiments.generate_paper_assets_from_inputs",
        "notes": [
            "Operational clearance time corresponds to the current kernel completion rule (95% evacuated).",
            "Case studies are generated from four user-provided uploaded floor plans.",
        ],
        "results": results,
    }
    (OUTPUT_DIR / "paper_case_studies.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    with (OUTPUT_DIR / "paper_case_studies.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "case_id",
                "scenario_id",
                "num_agents",
                "routing_policy",
                "blocked_exits",
                "operational_clearance_time_s",
                "clearance_90_s",
                "peak_density",
                "congestion_duration_s",
                "bottleneck_count",
                "completed_pct",
                "exit_imbalance_index",
            ],
        )
        writer.writeheader()
        for row in results:
            writer.writerow(
                {
                    "case_id": row["case_id"],
                    "scenario_id": row["scenario_id"],
                    "num_agents": row["num_agents"],
                    "routing_policy": row["routing_policy"],
                    "blocked_exits": "",
                    "operational_clearance_time_s": row["operational_clearance_time_s"],
                    "clearance_90_s": row["clearance_90_s"],
                    "peak_density": row["peak_density"],
                    "congestion_duration_s": row["congestion_duration_s"],
                    "bottleneck_count": row["bottleneck_count"],
                    "completed_pct": row["completed_pct"],
                    "exit_imbalance_index": row["exit_imbalance_index"],
                }
            )


def generate() -> Dict[str, Any]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    plan_paths = [INPUT_DIR / f"plan{i}.jpg" for i in range(1, 5)]
    missing = [str(path) for path in plan_paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing required input floor plans: {missing}")

    case_layouts: Dict[str, Dict[str, Any]] = {}
    for idx, path in enumerate(plan_paths, start=1):
        case_id = f"Plan {idx}"
        case_layouts[case_id] = _from_image(path)

    results: List[Dict[str, Any]] = []
    showcase_frames: List[Dict[str, Any]] = []

    for idx, (case_id, floor_plan) in enumerate(case_layouts.items(), start=1):
        area = float(floor_plan["building_bounds"]["max_x"] - floor_plan["building_bounds"]["min_x"]) * float(
            floor_plan["building_bounds"]["max_y"] - floor_plan["building_bounds"]["min_y"]
        )
        num_agents = max(36, min(90, int(32 + 0.45 * math.sqrt(max(area, 1.0)))))
        routing_policy = "least_crowded" if idx % 2 == 0 else "shortest_path"
        result, frames = _simulate_case(
            case_id=f"P{idx}",
            scenario_id="baseline",
            floor_plan=floor_plan,
            num_agents=num_agents,
            routing_policy=routing_policy,
            seed=200 + idx,
            capture_frames=(idx == 4),
            max_runtime_seconds=90,
            hard_wall_seconds=18.0,
        )
        results.append(result)
        if idx == 4:
            showcase_frames = frames

    _write_results(results)
    _write_pipeline_figure()
    _write_architecture_figure()
    _write_case_layouts_figure(case_layouts)
    _write_floorplan_figure(case_layouts["Plan 4"], "Plan 4: Uploaded Commercial Layout")
    _write_simulation_figure(case_layouts["Plan 4"], showcase_frames)
    _write_density_figure(case_layouts["Plan 4"], showcase_frames)

    return {
        "result_count": len(results),
        "json_path": str(OUTPUT_DIR / "paper_case_studies.json"),
        "csv_path": str(OUTPUT_DIR / "paper_case_studies.csv"),
        "figures": [
            "fig_pipeline.png",
            "fig_architecture.png",
            "fig_case_layouts.png",
            "fig_floorplan.png",
            "fig_simulation.png",
            "fig_density.png",
        ],
    }


if __name__ == "__main__":
    print(json.dumps(generate(), indent=2))
