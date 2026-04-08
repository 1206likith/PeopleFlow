"""Generate reproducible case-study results and figures for the paper draft.

This script writes:
- paper_case_studies.json
- paper_case_studies.csv
- fig_pipeline.png
- fig_architecture.png
- fig_case_layouts.png
- fig_floorplan.png
- fig_simulation.png
- fig_density.png

The assets are stored beside research_paper.tex in app/experiments/output so the
folder can be uploaded directly to Overleaf.
"""

from __future__ import annotations

import csv
import json
import math
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import matplotlib.pyplot as plt  # type: ignore
import numpy as np  # type: ignore

from app.sim.simulation_kernel import SimulationKernel
from app.services.metrics_engine import MetricsEngine


OUTPUT_DIR = Path(__file__).resolve().parent / "output"
ROOT_DIR = Path(__file__).resolve().parents[4]
SQLITE_PATH = ROOT_DIR / "apps" / "backend" / "data" / "peopleflow.db"
REAL_FLOOR_PLAN_ID = "b062dcce-2a43-4bfa-91ea-e614531be1af"


def _case_a_floor_plan() -> Dict[str, Any]:
    return {
        "building_bounds": {"min_x": 0.0, "max_x": 40.0, "min_y": 0.0, "max_y": 8.0},
        "detected_walls": [
            {"x1": 0.0, "y1": 0.0, "x2": 40.0, "y2": 0.0},
            {"x1": 0.0, "y1": 8.0, "x2": 40.0, "y2": 8.0},
            {"x1": 0.0, "y1": 0.0, "x2": 0.0, "y2": 8.0},
            {"x1": 40.0, "y1": 0.0, "x2": 40.0, "y2": 8.0},
        ],
        "detected_obstacles": [],
        "rooms": [],
        "hazards": [],
        "image_dimensions": {"width": 40, "height": 8},
        "exits": [
            {"id": "exit_left", "x": 2.0, "y": 4.0, "z": 4.0, "width": 2.5, "capacity": 120},
            {"id": "exit_right", "x": 38.0, "y": 4.0, "z": 4.0, "width": 1.5, "capacity": 80},
        ],
    }


def _case_b_floor_plan() -> Dict[str, Any]:
    return {
        "building_bounds": {"min_x": 0.0, "max_x": 50.0, "min_y": 0.0, "max_y": 30.0},
        "detected_walls": [
            {"x1": 0.0, "y1": 0.0, "x2": 50.0, "y2": 0.0},
            {"x1": 0.0, "y1": 30.0, "x2": 50.0, "y2": 30.0},
            {"x1": 0.0, "y1": 0.0, "x2": 0.0, "y2": 30.0},
            {"x1": 50.0, "y1": 0.0, "x2": 50.0, "y2": 30.0},
        ],
        "detected_obstacles": [],
        "rooms": [],
        "hazards": [],
        "image_dimensions": {"width": 50, "height": 30},
        "exits": [
            {"id": "exit_west", "x": 2.0, "y": 15.0, "z": 15.0, "width": 0.8, "capacity": 40},
            {"id": "exit_east_north", "x": 48.0, "y": 6.0, "z": 6.0, "width": 2.2, "capacity": 130},
            {"id": "exit_east_south", "x": 48.0, "y": 24.0, "z": 24.0, "width": 2.2, "capacity": 130},
        ],
    }


def _load_real_doc() -> Dict[str, Any]:
    conn = sqlite3.connect(SQLITE_PATH)
    try:
        row = conn.execute(
            "select document from floor_plans where id = ?",
            (REAL_FLOOR_PLAN_ID,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        raise FileNotFoundError(f"Floor-plan record {REAL_FLOOR_PLAN_ID} was not found in {SQLITE_PATH}")
    return json.loads(row[0])


def _case_c_floor_plan(scale: float = 50.0) -> Dict[str, Any]:
    doc = _load_real_doc()
    bounds = dict(doc.get("building_bounds") or {})
    boundaries = []
    for boundary in doc.get("boundaries", []):
        boundaries.append(
            {
                "x1": float(boundary.get("x1", 0.0)) / scale,
                "y1": float(boundary.get("y1", 0.0)) / scale,
                "x2": float(boundary.get("x2", 0.0)) / scale,
                "y2": float(boundary.get("y2", 0.0)) / scale,
                "type": boundary.get("type"),
            }
        )

    exits = []
    for index, exit_data in enumerate((doc.get("manual_exits") or [])[:3]):
        exits.append(
            {
                "id": exit_data.get("id", f"real-exit-{index + 1}"),
                "name": exit_data.get("name", f"Exit {index + 1}"),
                "x": float(exit_data.get("x", 0.0)) / scale,
                "y": float(exit_data.get("y", 0.0)) / scale,
                "z": float(exit_data.get("z", exit_data.get("y", 0.0))) / scale,
                "width": max(1.2, float(exit_data.get("width", 2.0)) * 1.5),
                "capacity": max(80, int(exit_data.get("capacity", 100))),
            }
        )

    return {
        "building_bounds": {
            "min_x": float(bounds.get("min_x", 0.0)) / scale,
            "min_y": float(bounds.get("min_y", 0.0)) / scale,
            "max_x": float(bounds.get("max_x", 100.0)) / scale,
            "max_y": float(bounds.get("max_y", 100.0)) / scale,
            "width": float(bounds.get("width", 100.0)) / scale,
            "height": float(bounds.get("height", 100.0)) / scale,
        },
        "detected_walls": boundaries,
        "detected_obstacles": [],
        "rooms": [],
        "corridors": [],
        "boundaries": boundaries,
        "boundary_polygon": [],
        "image_dimensions": {
            "width": float(bounds.get("width", 100.0)) / scale,
            "height": float(bounds.get("height", 100.0)) / scale,
        },
        "hazards": [],
        "exits": exits,
        "metadata": {
            "source_floor_plan_id": REAL_FLOOR_PLAN_ID,
            "source_filename": doc.get("filename"),
            "geometry_mode": "scaled_floor_plan_envelope",
            "scale_factor": scale,
            "source_wall_count": len(doc.get("detected_walls", [])),
            "source_room_count": len(doc.get("rooms", [])),
            "source_detected_exit_count": len(doc.get("detected_exits", [])),
        },
    }


def _simulate_case(
    case_id: str,
    scenario_id: str,
    floor_plan: Dict[str, Any],
    *,
    num_agents: int,
    routing_policy: str,
    blocked_exits: Iterable[str] | None = None,
    seed: int = 333,
    panic_level: float = 0.4,
    disable_hazards: bool = True,
    max_runtime_seconds: int = 180,
    capture_frames: bool = False,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    config = {
        "seed": seed,
        "mode": "paper",
        "num_agents": num_agents,
        "emergency_type": "fire",
        "routing_policy": routing_policy,
        "panic_level": panic_level,
        "blocked_exits": list(blocked_exits or []),
        "parameter_overrides": {"disable_hazards": disable_hazards},
        "max_runtime_seconds": max_runtime_seconds,
    }
    kernel = SimulationKernel(f"paper-{case_id}-{scenario_id}", config)
    kernel.initialize(floor_plan)
    metrics_engine = MetricsEngine()
    frames: List[Dict[str, Any]] = []
    prev_agents: Dict[int, Dict[str, Any]] = {}
    exit_counts: Counter[str] = Counter()

    steps = 0
    max_steps = int(max_runtime_seconds / 0.2) * 5
    while not kernel.is_complete() and steps < max_steps:
        frame = kernel.step(0.2)
        metrics_engine.add_frame(frame)
        if capture_frames or (steps % 5 == 0):
            frames.append(json.loads(json.dumps(frame)))

        curr_agents = {int(agent["agent_id"]): agent for agent in frame.get("agents", [])}
        for agent_id, agent in curr_agents.items():
            previous = prev_agents.get(agent_id)
            if agent.get("status") == "evacuated" and previous and previous.get("status") != "evacuated":
                px = float(previous.get("x", 0.0))
                pz = float(previous.get("z", previous.get("y", 0.0)))
                nearest_exit = min(
                    floor_plan.get("exits", []),
                    key=lambda exit_data: math.hypot(
                        float(exit_data.get("x", 0.0)) - px,
                        float(exit_data.get("z", exit_data.get("y", 0.0))) - pz,
                    ),
                )
                exit_counts[str(nearest_exit.get("id", "unknown"))] += 1
        prev_agents = curr_agents
        steps += 1

    metrics = metrics_engine.calculate_metrics()
    evacuation_distribution = list(metrics.evacuation_time_distribution or [])
    clearance_90 = float(np.percentile(evacuation_distribution, 90)) if evacuation_distribution else None
    exit_values = list(exit_counts.values())
    exit_imbalance = None
    if exit_values:
        mean_value = float(np.mean(exit_values))
        if mean_value > 0:
            exit_imbalance = float(np.std(exit_values) / mean_value)

    result = {
        "case_id": case_id,
        "scenario_id": scenario_id,
        "num_agents": num_agents,
        "routing_policy": routing_policy,
        "blocked_exits": list(blocked_exits or []),
        "seed": seed,
        "panic_level": panic_level,
        "disable_hazards": disable_hazards,
        "completion_threshold_pct": 95.0,
        "terminal_time_s": round(float(kernel.engine.time), 3),
        "operational_clearance_time_s": round(float(metrics.total_evacuation_time), 3),
        "clearance_90_s": round(clearance_90, 3) if clearance_90 is not None else None,
        "peak_density": round(float(metrics.peak_congestion_density), 3),
        "congestion_duration_s": round(float(metrics.congestion_duration), 3),
        "bottleneck_count": int(len(metrics.bottleneck_locations)),
        "completed_agents": int(kernel.engine.evacuated_count),
        "completed_pct": round(float(kernel.engine.evacuated_count / max(num_agents, 1) * 100.0), 1),
        "exit_counts": dict(exit_counts),
        "exit_imbalance_index": round(exit_imbalance, 3) if exit_imbalance is not None else None,
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
            linewidth=2.0,
        )

    for obstacle in floor_plan.get("detected_obstacles", []):
        x = float(obstacle.get("x", 0.0))
        y = float(obstacle.get("y", 0.0))
        width = float(obstacle.get("width", 0.5))
        height = float(obstacle.get("height", 0.5))
        rect = plt.Rectangle((x, y), width, height, color="#9aa4b1", alpha=0.6)
        ax.add_patch(rect)

    for exit_data in floor_plan.get("exits", []):
        ex = float(exit_data.get("x", 0.0))
        ez = float(exit_data.get("z", exit_data.get("y", 0.0)))
        ew = float(exit_data.get("width", 1.0))
        ax.plot([ex - ew / 2, ex + ew / 2], [ez, ez], color="#15b8a6", linewidth=4.5, solid_capstyle="round")

    if frame is not None:
        agents = frame.get("agents", [])
        xs = [float(agent.get("x", 0.0)) for agent in agents if agent.get("status") != "evacuated"]
        zs = [float(agent.get("z", agent.get("y", 0.0))) for agent in agents if agent.get("status") != "evacuated"]
        if xs and zs:
            ax.scatter(xs, zs, s=8, color="#4169e1", alpha=0.55, edgecolors="none")


def _write_case_layouts_figure(case_layouts: Dict[str, Dict[str, Any]]) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    for ax, (case_id, payload) in zip(axes, case_layouts.items()):
        _draw_floor_plan(ax, payload, f"Case {case_id}")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig_case_layouts.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def _write_floorplan_figure(case_c_floor_plan: Dict[str, Any]) -> None:
    fig, ax = plt.subplots(figsize=(5.4, 4.6))
    _draw_floor_plan(ax, case_c_floor_plan, "Case C: Normalized Uploaded Floor Plan")
    meta = case_c_floor_plan.get("metadata") or {}
    ax.text(
        0.02,
        0.02,
        (
            f"Source walls: {meta.get('source_wall_count', 'n/a')}\n"
            f"Source rooms: {meta.get('source_room_count', 'n/a')}\n"
            f"Scale factor: {meta.get('scale_factor', 'n/a')}"
        ),
        transform=ax.transAxes,
        fontsize=8,
        va="bottom",
        ha="left",
        bbox={"facecolor": "white", "alpha": 0.85, "edgecolor": "#c7d0da"},
    )
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig_floorplan.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def _write_simulation_figure(case_c_floor_plan: Dict[str, Any], frames: List[Dict[str, Any]]) -> None:
    sample_indices = [0, max(0, len(frames) // 2), max(0, len(frames) - 1)]
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    for ax, index, label in zip(axes, sample_indices, ["Start", "Mid-run", "Operational clearance"]):
        frame = frames[index] if frames else None
        timestamp = float(frame.get("timestamp", 0.0)) if frame else 0.0
        _draw_floor_plan(ax, case_c_floor_plan, f"{label} ({timestamp:.1f}s)", frame=frame)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig_simulation.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def _write_density_figure(case_c_floor_plan: Dict[str, Any], frames: List[Dict[str, Any]]) -> None:
    bounds = case_c_floor_plan.get("building_bounds") or {}
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
        hist = ax.hist2d(xs, zs, bins=30, range=[[min_x, max_x], [min_y, max_y]], cmap="magma")
        fig.colorbar(hist[3], ax=ax, fraction=0.046, pad=0.04, label="Occupancy intensity")
    for wall in case_c_floor_plan.get("detected_walls", []):
        ax.plot(
            [float(wall.get("x1", 0.0)), float(wall.get("x2", 0.0))],
            [float(wall.get("y1", 0.0)), float(wall.get("y2", 0.0))],
            color="white",
            linewidth=1.2,
            alpha=0.9,
        )
    ax.set_title("Case C Stress Scenario Density Heatmap")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_aspect("equal")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig_density.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def _write_pipeline_figure() -> None:
    fig, ax = plt.subplots(figsize=(10.8, 3.3))
    ax.axis("off")
    labels = [
        "Floor-plan\nupload",
        "Geometry\nreview",
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
        rect = plt.Rectangle((x - box_half_width, 0.31), box_width, 0.40, facecolor="#eef4ff", edgecolor="#2a5bd7", linewidth=1.7)
        ax.add_patch(rect)
        ax.text(x, 0.51, label, ha="center", va="center", fontsize=10.5, fontweight="semibold")
        if index < len(labels) - 1:
            start_x = x + box_half_width + connector_pad
            end_x = xs[index + 1] - box_half_width - connector_pad
            ax.annotate("", xy=(end_x, 0.51), xytext=(start_x, 0.51), arrowprops={"arrowstyle": "->", "lw": 1.8})
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig_pipeline.png", dpi=260, bbox_inches="tight")
    plt.close(fig)


def _write_architecture_figure() -> None:
    fig, ax = plt.subplots(figsize=(10.2, 4.8))
    ax.axis("off")
    blocks = [
        (0.05, 0.56, 0.24, 0.26, "#eef4ff", "Designer\nUpload + exit edits"),
        (0.38, 0.56, 0.24, 0.26, "#eef4ff", "Simulation studio\nLive run + replay"),
        (0.71, 0.56, 0.24, 0.26, "#eef4ff", "Experiments dashboard\nArtifacts + comparison"),
        (0.2, 0.14, 0.24, 0.24, "#f7f9fc", "Backend services\nProcessing + sessions"),
        (0.56, 0.14, 0.24, 0.24, "#f7f9fc", "Persistence\nSQLite + JSON artifacts"),
    ]
    for x, y, w, h, color, label in blocks:
        rect = plt.Rectangle((x, y), w, h, facecolor=color, edgecolor="#334155", linewidth=1.5)
        ax.add_patch(rect)
        ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", fontsize=10.5, fontweight="semibold")
    arrows = [
        ((0.29, 0.58), (0.32, 0.37)),
        ((0.50, 0.58), (0.50, 0.37)),
        ((0.71, 0.58), (0.68, 0.37)),
        ((0.44, 0.26), (0.56, 0.26)),
    ]
    for start, end in arrows:
        ax.annotate("", xy=end, xytext=start, arrowprops={"arrowstyle": "->", "lw": 1.9})
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig_architecture.png", dpi=260, bbox_inches="tight")
    plt.close(fig)


def _write_results_json(results: List[Dict[str, Any]]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "bundle_version": "peopleflow-paper-case-studies-v1",
        "generated_from": "app.experiments.generate_paper_assets",
        "notes": [
            "Operational clearance time corresponds to the current kernel completion rule (95% evacuated).",
            "Case C is derived from a real uploaded floor plan stored in SQLite and normalized by a coordinate scale factor of 50.",
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
                    "blocked_exits": ",".join(row.get("blocked_exits", [])),
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

    case_layouts = {
        "A": _case_a_floor_plan(),
        "B": _case_b_floor_plan(),
        "C": _case_c_floor_plan(),
    }

    results: List[Dict[str, Any]] = []

    case_a_baseline, _ = _simulate_case(
        "A",
        "baseline",
        case_layouts["A"],
        num_agents=30,
        routing_policy="shortest_path",
        blocked_exits=[],
        seed=123,
        panic_level=0.35,
        max_runtime_seconds=240,
    )
    case_a_blocked, _ = _simulate_case(
        "A",
        "blocked_exit",
        case_layouts["A"],
        num_agents=30,
        routing_policy="shortest_path",
        blocked_exits=["exit_left"],
        seed=123,
        panic_level=0.35,
        max_runtime_seconds=240,
    )

    case_b_nearest, _ = _simulate_case(
        "B",
        "nearest_routing",
        case_layouts["B"],
        num_agents=60,
        routing_policy="shortest_path",
        blocked_exits=[],
        seed=222,
        panic_level=0.38,
        max_runtime_seconds=180,
    )
    case_b_congestion_aware, _ = _simulate_case(
        "B",
        "congestion_aware",
        case_layouts["B"],
        num_agents=60,
        routing_policy="least_crowded",
        blocked_exits=[],
        seed=222,
        panic_level=0.38,
        max_runtime_seconds=180,
    )

    case_c_baseline, case_c_baseline_frames = _simulate_case(
        "C",
        "baseline",
        case_layouts["C"],
        num_agents=80,
        routing_policy="least_crowded",
        blocked_exits=[],
        seed=333,
        panic_level=0.4,
        max_runtime_seconds=180,
        capture_frames=True,
    )
    case_c_stress, case_c_stress_frames = _simulate_case(
        "C",
        "occupancy_stress",
        case_layouts["C"],
        num_agents=120,
        routing_policy="least_crowded",
        blocked_exits=[],
        seed=333,
        panic_level=0.4,
        max_runtime_seconds=180,
        capture_frames=True,
    )

    results.extend(
        [
            case_a_baseline,
            case_a_blocked,
            case_b_nearest,
            case_b_congestion_aware,
            case_c_baseline,
            case_c_stress,
        ]
    )
    _write_results_json(results)

    _write_pipeline_figure()
    _write_architecture_figure()
    _write_case_layouts_figure(case_layouts)
    _write_floorplan_figure(case_layouts["C"])
    _write_simulation_figure(case_layouts["C"], case_c_baseline_frames)
    _write_density_figure(case_layouts["C"], case_c_stress_frames)

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
