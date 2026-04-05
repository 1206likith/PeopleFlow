"""Generate a 30-second multimedia supplement for PeopleFlow.

Video flow:
1) Title + contribution context
2) Pipeline overview
3) Floor-plan ingestion (raw blueprint)
4) Geometry extraction view
5) Scenario configuration card
6) Live evacuation simulation (blocked-exit stress)
7) Heatmap + summary metrics
8) Reproducibility closing slide

Output:
- Research_Paper_IEEE/supplementary/peopleflow_multimedia_supplement.mp4
- Research_Paper_IEEE/supplementary/peopleflow_multimedia_metadata.json
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

import cv2  # type: ignore
import numpy as np  # type: ignore

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.experiments.generate_journal_results import _rescale_floor_plan  # type: ignore
from app.services.floorplan_service import process_floor_plan_image  # type: ignore
from app.services.metrics_engine import MetricsEngine  # type: ignore
from app.sim.simulation_kernel import SimulationKernel  # type: ignore

ROOT_DIR = Path(__file__).resolve().parents[4]
PAPER_DIR = ROOT_DIR / "Research_Paper_IEEE"
OUT_DIR = PAPER_DIR / "supplementary"
VIDEO_PATH = OUT_DIR / "peopleflow_multimedia_supplement.mp4"
META_PATH = OUT_DIR / "peopleflow_multimedia_metadata.json"

LAYOUT_PATH = ROOT_DIR / "apps" / "backend" / "app" / "experiments" / "input_floorplans" / "ieee_journal_blueprints" / "H_metro_taipei.jpg"
PIPELINE_FIG = PAPER_DIR / "fig_pipeline.png"

W, H = 1280, 720
FPS = 30

BG = (245, 246, 248)
DARK = (25, 30, 40)
ACCENT = (56, 112, 255)
GOOD = (64, 156, 82)
WARN = (52, 82, 214)
BAD = (50, 50, 220)


def _mime(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".png":
        return "image/png"
    if suffix == ".webp":
        return "image/webp"
    return "image/jpeg"


def _blank() -> np.ndarray:
    frame = np.zeros((H, W, 3), dtype=np.uint8)
    frame[:, :] = BG
    return frame


def _put_text(frame: np.ndarray, text: str, x: int, y: int, scale: float = 0.8, color: tuple[int, int, int] = DARK, thick: int = 2) -> None:
    cv2.putText(frame, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, scale, color, thick, cv2.LINE_AA)


def _draw_header(frame: np.ndarray, title: str, subtitle: str | None = None) -> None:
    cv2.rectangle(frame, (0, 0), (W, 78), (234, 238, 245), -1)
    _put_text(frame, title, 28, 48, 1.0, DARK, 2)
    if subtitle:
        _put_text(frame, subtitle, 28, 72, 0.6, (90, 98, 114), 1)


def _add_footer(frame: np.ndarray, text: str) -> None:
    cv2.rectangle(frame, (0, H - 44), (W, H), (234, 238, 245), -1)
    _put_text(frame, text, 20, H - 16, 0.55, (88, 96, 110), 1)


def _fit_image(img: np.ndarray, max_w: int, max_h: int) -> np.ndarray:
    h, w = img.shape[:2]
    if h <= 0 or w <= 0:
        return np.zeros((max_h, max_w, 3), dtype=np.uint8)
    scale = min(max_w / w, max_h / h)
    nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
    resized = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)
    canvas = np.zeros((max_h, max_w, 3), dtype=np.uint8)
    canvas[:] = (250, 250, 250)
    x0 = (max_w - nw) // 2
    y0 = (max_h - nh) // 2
    canvas[y0:y0 + nh, x0:x0 + nw] = resized
    return canvas


def _world_to_px(x: float, z: float, bounds: dict[str, float], rect: tuple[int, int, int, int]) -> tuple[int, int]:
    x0, y0, x1, y1 = rect
    min_x = float(bounds.get("min_x", 0.0))
    max_x = float(bounds.get("max_x", 1.0))
    min_y = float(bounds.get("min_y", 0.0))
    max_y = float(bounds.get("max_y", 1.0))

    width = max(1e-6, max_x - min_x)
    height = max(1e-6, max_y - min_y)

    px = x0 + int(((x - min_x) / width) * (x1 - x0))
    py = y1 - int(((z - min_y) / height) * (y1 - y0))
    return px, py


def _draw_geometry_canvas(floor_plan: dict[str, Any], title: str) -> np.ndarray:
    frame = _blank()
    _draw_header(frame, "PeopleFlow Multimedia Supplement", title)

    rect = (70, 110, W - 70, H - 90)
    cv2.rectangle(frame, (rect[0], rect[1]), (rect[2], rect[3]), (255, 255, 255), -1)
    cv2.rectangle(frame, (rect[0], rect[1]), (rect[2], rect[3]), (215, 220, 232), 1)

    bounds = floor_plan.get("building_bounds") or {}

    for wall in floor_plan.get("detected_walls", []):
        p1 = _world_to_px(float(wall.get("x1", 0.0)), float(wall.get("y1", 0.0)), bounds, rect)
        p2 = _world_to_px(float(wall.get("x2", 0.0)), float(wall.get("y2", 0.0)), bounds, rect)
        cv2.line(frame, p1, p2, (90, 96, 110), 1, cv2.LINE_AA)

    for ex in floor_plan.get("exits", []):
        p = _world_to_px(float(ex.get("x", 0.0)), float(ex.get("z", ex.get("y", 0.0))), bounds, rect)
        cv2.circle(frame, p, 6, GOOD, -1, cv2.LINE_AA)

    _add_footer(frame, "Step 2/5: Geometry extraction from uploaded floor plan (walls/exits converted to simulation primitives)")
    return frame


def _draw_simulation_frame(floor_plan: dict[str, Any], sim_frame: dict[str, Any], blocked_exits: set[str]) -> np.ndarray:
    frame = _blank()
    _draw_header(frame, "PeopleFlow Multimedia Supplement", "Step 4/5: Live simulation (blocked-exit stress scenario)")

    rect = (60, 100, 900, 650)
    cv2.rectangle(frame, (rect[0], rect[1]), (rect[2], rect[3]), (255, 255, 255), -1)
    cv2.rectangle(frame, (rect[0], rect[1]), (rect[2], rect[3]), (215, 220, 232), 1)

    bounds = floor_plan.get("building_bounds") or {}

    walls = sim_frame.get("walls") or floor_plan.get("detected_walls") or []
    for wall in walls:
        p1 = _world_to_px(float(wall.get("x1", 0.0)), float(wall.get("y1", 0.0)), bounds, rect)
        p2 = _world_to_px(float(wall.get("x2", 0.0)), float(wall.get("y2", 0.0)), bounds, rect)
        cv2.line(frame, p1, p2, (95, 100, 112), 1, cv2.LINE_AA)

    for ex in (sim_frame.get("exits") or floor_plan.get("exits") or []):
        ex_id = str(ex.get("id", ""))
        p = _world_to_px(float(ex.get("x", 0.0)), float(ex.get("z", ex.get("y", 0.0))), bounds, rect)
        color = BAD if ex_id in blocked_exits or bool(ex.get("blocked") or ex.get("is_blocked")) else GOOD
        cv2.circle(frame, p, 7, color, -1, cv2.LINE_AA)

    agents = sim_frame.get("agents") or []
    for a in agents:
        if a.get("status") == "evacuated":
            continue
        x = float(a.get("x", 0.0))
        z = float(a.get("z", a.get("y", 0.0)))
        p = _world_to_px(x, z, bounds, rect)

        speed = float(a.get("speed", 0.0))
        speed_norm = max(0.0, min(1.0, speed / 2.0))
        color_map_idx = np.uint8([[int(speed_norm * 255)]])
        color = cv2.applyColorMap(color_map_idx, cv2.COLORMAP_VIRIDIS)[0][0].tolist()
        cv2.circle(frame, p, 2, (int(color[0]), int(color[1]), int(color[2])), -1, cv2.LINE_AA)

    stats = sim_frame.get("stats") or {}
    panel_x0, panel_y0, panel_x1, panel_y1 = 930, 110, 1240, 650
    cv2.rectangle(frame, (panel_x0, panel_y0), (panel_x1, panel_y1), (248, 250, 255), -1)
    cv2.rectangle(frame, (panel_x0, panel_y0), (panel_x1, panel_y1), (210, 216, 232), 1)

    _put_text(frame, "Scenario", panel_x0 + 16, panel_y0 + 34, 0.7, DARK, 2)
    _put_text(frame, "Blocked exit stress", panel_x0 + 16, panel_y0 + 62, 0.55, DARK, 1)
    _put_text(frame, "Routing: least_crowded", panel_x0 + 16, panel_y0 + 86, 0.55, DARK, 1)

    _put_text(frame, "Live Stats", panel_x0 + 16, panel_y0 + 132, 0.7, DARK, 2)
    _put_text(frame, f"Sim time: {float(sim_frame.get('timestamp', 0.0)):.1f} s", panel_x0 + 16, panel_y0 + 162, 0.55, DARK, 1)
    _put_text(frame, f"Frame: {int(sim_frame.get('frame_id', 0))}", panel_x0 + 16, panel_y0 + 186, 0.55, DARK, 1)
    _put_text(frame, f"Agents total: {int(stats.get('total_agents', 0))}", panel_x0 + 16, panel_y0 + 210, 0.55, DARK, 1)
    _put_text(frame, f"Evacuated: {int(stats.get('evacuated', 0))}", panel_x0 + 16, panel_y0 + 234, 0.55, DARK, 1)
    _put_text(frame, f"Remaining: {int(stats.get('remaining', 0))}", panel_x0 + 16, panel_y0 + 258, 0.55, DARK, 1)
    _put_text(frame, f"Completion: {float(stats.get('completion_percentage', 0.0)):.1f}%", panel_x0 + 16, panel_y0 + 282, 0.55, DARK, 1)

    _put_text(frame, "Legend", panel_x0 + 16, panel_y0 + 332, 0.7, DARK, 2)
    cv2.circle(frame, (panel_x0 + 24, panel_y0 + 358), 6, GOOD, -1)
    _put_text(frame, "Open exit", panel_x0 + 40, panel_y0 + 362, 0.5, DARK, 1)
    cv2.circle(frame, (panel_x0 + 24, panel_y0 + 382), 6, BAD, -1)
    _put_text(frame, "Blocked exit", panel_x0 + 40, panel_y0 + 386, 0.5, DARK, 1)
    cv2.circle(frame, (panel_x0 + 24, panel_y0 + 406), 5, (255, 180, 40), -1)
    _put_text(frame, "Agent (viridis by speed)", panel_x0 + 40, panel_y0 + 410, 0.5, DARK, 1)

    _add_footer(frame, "Step 4/5: Deterministic simulation with session-state tracking and reproducible seeded execution")
    return frame


def _draw_heatmap_summary(floor_plan: dict[str, Any], all_frames: list[dict[str, Any]], metrics: dict[str, Any]) -> np.ndarray:
    frame = _blank()
    _draw_header(frame, "PeopleFlow Multimedia Supplement", "Step 5/5: Analytics and reporting artifacts")

    rect = (60, 100, 900, 650)
    cv2.rectangle(frame, (rect[0], rect[1]), (rect[2], rect[3]), (255, 255, 255), -1)
    cv2.rectangle(frame, (rect[0], rect[1]), (rect[2], rect[3]), (215, 220, 232), 1)

    bounds = floor_plan.get("building_bounds") or {}
    bins_w, bins_h = 180, 120
    heat = np.zeros((bins_h, bins_w), dtype=np.float32)

    min_x = float(bounds.get("min_x", 0.0))
    max_x = float(bounds.get("max_x", 1.0))
    min_y = float(bounds.get("min_y", 0.0))
    max_y = float(bounds.get("max_y", 1.0))
    span_x = max(1e-6, max_x - min_x)
    span_y = max(1e-6, max_y - min_y)

    for sf in all_frames:
        for a in sf.get("agents", []):
            if a.get("status") == "evacuated":
                continue
            x = float(a.get("x", 0.0))
            z = float(a.get("z", a.get("y", 0.0)))
            ix = int((x - min_x) / span_x * (bins_w - 1))
            iy = int((z - min_y) / span_y * (bins_h - 1))
            if 0 <= ix < bins_w and 0 <= iy < bins_h:
                heat[bins_h - 1 - iy, ix] += 1.0

    if float(heat.max()) > 0.0:
        heat_u8 = np.uint8(np.clip((heat / float(heat.max())) * 255.0, 0, 255))
    else:
        heat_u8 = np.zeros((bins_h, bins_w), dtype=np.uint8)

    cmap = cv2.COLORMAP_MAGMA if hasattr(cv2, "COLORMAP_MAGMA") else cv2.COLORMAP_VIRIDIS
    heat_color = cv2.applyColorMap(heat_u8, cmap)
    heat_color = cv2.resize(heat_color, (rect[2] - rect[0], rect[3] - rect[1]), interpolation=cv2.INTER_CUBIC)
    frame[rect[1]:rect[3], rect[0]:rect[2]] = cv2.addWeighted(frame[rect[1]:rect[3], rect[0]:rect[2]], 0.25, heat_color, 0.75, 0.0)

    # Overlay geometry outlines for context.
    for wall in floor_plan.get("detected_walls", []):
        p1 = _world_to_px(float(wall.get("x1", 0.0)), float(wall.get("y1", 0.0)), bounds, rect)
        p2 = _world_to_px(float(wall.get("x2", 0.0)), float(wall.get("y2", 0.0)), bounds, rect)
        cv2.line(frame, p1, p2, (240, 240, 240), 1, cv2.LINE_AA)

    panel_x0, panel_y0, panel_x1, panel_y1 = 930, 110, 1240, 650
    cv2.rectangle(frame, (panel_x0, panel_y0), (panel_x1, panel_y1), (248, 250, 255), -1)
    cv2.rectangle(frame, (panel_x0, panel_y0), (panel_x1, panel_y1), (210, 216, 232), 1)

    _put_text(frame, "Run Summary", panel_x0 + 16, panel_y0 + 34, 0.72, DARK, 2)
    _put_text(frame, f"Total evac time: {metrics.get('total_evacuation_time', 0.0):.1f} s", panel_x0 + 16, panel_y0 + 70, 0.55, DARK, 1)
    _put_text(frame, f"Peak density: {metrics.get('peak_congestion_density', 0.0):.2f}", panel_x0 + 16, panel_y0 + 94, 0.55, DARK, 1)
    _put_text(frame, f"Max queue: {metrics.get('max_queue_length', 0)}", panel_x0 + 16, panel_y0 + 118, 0.55, DARK, 1)
    _put_text(frame, f"Bottlenecks: {metrics.get('bottleneck_events', 0)}", panel_x0 + 16, panel_y0 + 142, 0.55, DARK, 1)

    _put_text(frame, "Artifacts", panel_x0 + 16, panel_y0 + 188, 0.7, DARK, 2)
    _put_text(frame, "- seeded run config", panel_x0 + 16, panel_y0 + 216, 0.52, DARK, 1)
    _put_text(frame, "- frame-level trajectories", panel_x0 + 16, panel_y0 + 238, 0.52, DARK, 1)
    _put_text(frame, "- aggregate metrics", panel_x0 + 16, panel_y0 + 260, 0.52, DARK, 1)
    _put_text(frame, "- reproducibility metadata", panel_x0 + 16, panel_y0 + 282, 0.52, DARK, 1)

    _put_text(frame, "Color scale", panel_x0 + 16, panel_y0 + 334, 0.7, DARK, 2)
    grad = np.linspace(0, 255, 220, dtype=np.uint8).reshape(1, -1)
    grad = np.repeat(grad, 20, axis=0)
    grad_color = cv2.applyColorMap(grad, cmap)
    frame[panel_y0 + 350:panel_y0 + 370, panel_x0 + 16:panel_x0 + 236] = grad_color
    _put_text(frame, "low", panel_x0 + 16, panel_y0 + 390, 0.45, DARK, 1)
    _put_text(frame, "high", panel_x0 + 198, panel_y0 + 390, 0.45, DARK, 1)

    _add_footer(frame, "Heatmap uses colorblind-friendly colormap (magma/viridis): brighter regions indicate persistent congestion")
    return frame


def _slide(title: str, lines: list[str], footer: str) -> np.ndarray:
    frame = _blank()
    _draw_header(frame, "PeopleFlow Multimedia Supplement", title)
    y = 170
    for line in lines:
        _put_text(frame, line, 90, y, 0.82, DARK, 2)
        y += 44
    _add_footer(frame, footer)
    return frame


def _repeat(writer: cv2.VideoWriter, frame: np.ndarray, seconds: float) -> int:
    count = max(1, int(round(seconds * FPS)))
    for _ in range(count):
        writer.write(frame)
    return count


def main() -> None:
    if not LAYOUT_PATH.exists():
        raise FileNotFoundError(f"Layout not found: {LAYOUT_PATH}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(VIDEO_PATH), fourcc, FPS, (W, H))
    if not writer.isOpened():
        raise RuntimeError("Could not open video writer for mp4 output")

    t0 = time.perf_counter()

    raw = process_floor_plan_image(_mime(LAYOUT_PATH), str(LAYOUT_PATH), {"mode": "traditional"})
    floor_plan = _rescale_floor_plan(raw)

    exits = list(floor_plan.get("exits") or [])
    blocked_exits = {str(exits[0].get("id"))} if exits else set()

    # Build simulation trace for live segment + analytics.
    config = {
        "seed": 4242,
        "mode": "paper",
        "num_agents": 120,
        "emergency_type": "fire",
        "routing_policy": "least_crowded",
        "panic_level": 0.4,
        "blocked_exits": sorted(blocked_exits),
        "parameter_overrides": {"disable_hazards": True},
        "max_runtime_seconds": 240,
    }
    kernel = SimulationKernel("multimedia_supplement", config)
    kernel.initialize(floor_plan)

    metrics_engine = MetricsEngine()
    sim_frames: list[dict[str, Any]] = []
    for _ in range(420):
        if kernel.is_complete():
            break
        sf = kernel.step(0.2)
        sim_frames.append(sf)
        metrics_engine.add_frame(sf)

    if not sim_frames:
        sim_frames.append(kernel.current_frame())
        metrics_engine.add_frame(sim_frames[-1])

    metrics = metrics_engine.calculate_metrics()
    metrics_dict = metrics.__dict__ if hasattr(metrics, "__dict__") else dict(metrics)

    frame_count = 0

    # Intro slide
    frame_count += _repeat(
        writer,
        _slide(
            "End-to-End Evacuation Workflow Demo",
            [
                "PeopleFlow: reproducible geometry-aware evacuation analysis",
                "Demo scenario: metro concourse with blocked-exit stress",
                "Output: simulation trace + analytics + reproducibility artifacts",
            ],
            "Duration ~30s | IEEE multimedia supplement",
        ),
        2.8,
    )

    # Pipeline visual slide
    pipe_slide = _blank()
    _draw_header(pipe_slide, "PeopleFlow Pipeline", "Step 0/5: Workflow overview")
    if PIPELINE_FIG.exists():
        img = cv2.imread(str(PIPELINE_FIG), cv2.IMREAD_COLOR)
        if img is not None:
            fitted = _fit_image(img, W - 140, H - 210)
            y0, y1 = 110, 110 + fitted.shape[0]
            x0, x1 = 70, 70 + fitted.shape[1]
            pipe_slide[y0:y1, x0:x1] = fitted
    _add_footer(pipe_slide, "Pipeline: floor-plan ingestion -> geometry extraction -> simulation -> metrics -> report")
    frame_count += _repeat(writer, pipe_slide, 3.6)

    # Raw blueprint slide
    raw_slide = _blank()
    _draw_header(raw_slide, "Step 1/5: Floor-plan ingestion", "Input blueprint (raw) used to initialize PeopleFlow")
    raw_img = cv2.imread(str(LAYOUT_PATH), cv2.IMREAD_COLOR)
    if raw_img is not None:
        fitted = _fit_image(raw_img, W - 160, H - 220)
        y0, y1 = 105, 105 + fitted.shape[0]
        x0, x1 = 80, 80 + fitted.shape[1]
        raw_slide[y0:y1, x0:x1] = fitted
    _add_footer(raw_slide, "Input source: metro station blueprint | detection mode: traditional/OpenCV fallback")
    frame_count += _repeat(writer, raw_slide, 3.8)

    # Geometry extraction slide
    frame_count += _repeat(writer, _draw_geometry_canvas(floor_plan, "Step 2/5: Geometry extraction"), 3.8)

    # Scenario setup slide
    frame_count += _repeat(
        writer,
        _slide(
            "Step 3/5: Session configuration",
            [
                "Scenario: blocked-exit stress test",
                "Agents: 120 | Routing: least_crowded | dt: 0.2 s",
                f"Blocked exit IDs: {', '.join(sorted(blocked_exits)) if blocked_exits else 'none'}",
                "Seeded execution + frame-level metric logging",
            ],
            "Deterministic configuration supports exact reruns",
        ),
        3.2,
    )

    # Live simulation segment (~12 seconds)
    target_sim_frames = int(12.0 * FPS)
    if len(sim_frames) >= target_sim_frames:
        idxs = np.linspace(0, len(sim_frames) - 1, target_sim_frames).astype(int)
    else:
        idxs = np.arange(len(sim_frames), dtype=int)

    for idx in idxs:
        frame_count += 1
        writer.write(_draw_simulation_frame(floor_plan, sim_frames[int(idx)], blocked_exits))

    # Heatmap + summary segment
    frame_count += _repeat(writer, _draw_heatmap_summary(floor_plan, sim_frames, metrics_dict), 4.3)

    # Closing slide
    frame_count += _repeat(
        writer,
        _slide(
            "Supplementary Reproducibility Assets",
            [
                "- scenario seeds and run metadata",
                "- runtime/scalability benchmark tables",
                "- blocked-exit policy comparison artifacts",
                "- source code: github.com/1206likith/PeopleFlow",
            ],
            "PeopleFlow multimedia supplement generated automatically from project scripts",
        ),
        3.1,
    )

    writer.release()

    elapsed = time.perf_counter() - t0

    metadata = {
        "video_path": str(VIDEO_PATH),
        "fps": FPS,
        "resolution": [W, H],
        "total_frames": frame_count,
        "duration_seconds": round(frame_count / FPS, 2),
        "generation_wall_clock_s": round(elapsed, 2),
        "layout": str(LAYOUT_PATH),
        "scenario": {
            "num_agents": config["num_agents"],
            "routing_policy": config["routing_policy"],
            "blocked_exits": config["blocked_exits"],
            "panic_level": config["panic_level"],
            "dt_s": 0.2,
        },
        "metrics_summary": {
            "total_evacuation_time_s": float(metrics_dict.get("total_evacuation_time", 0.0) or 0.0),
            "peak_congestion_density": float(metrics_dict.get("peak_congestion_density", 0.0) or 0.0),
            "max_queue_length": int(metrics_dict.get("max_queue_length", 0) or 0),
            "bottleneck_events": int(metrics_dict.get("bottleneck_events", 0) or 0),
        },
    }
    META_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(f"Wrote video: {VIDEO_PATH}")
    print(f"Wrote metadata: {META_PATH}")


if __name__ == "__main__":
    main()
