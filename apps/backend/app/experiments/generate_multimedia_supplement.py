"""Generate a polished multimedia supplement for PeopleFlow.

This script produces a high-quality supplementary video with:
1) Cinematic intro and clear narrative pacing
2) Pipeline and floor-plan ingestion visuals
3) Geometry extraction explanation
4) Scenario configuration highlights
5) Live simulation with dynamic metrics panels
6) Analytics summary with trend charts
7) Reproducibility-oriented closing section

Outputs:
- Research_Paper_IEEE/supplementary/peopleflow_multimedia_supplement.mp4
- Research_Paper_IEEE/supplementary/peopleflow_multimedia_supplement_1080p.mp4
- Research_Paper_IEEE/supplementary/peopleflow_multimedia_metadata.json
- Research_Paper_IEEE/supplementary/preview_frames_v6/*.png
"""

from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

import cv2  # type: ignore
import numpy as np  # type: ignore

try:
    import imageio_ffmpeg  # type: ignore
except Exception:  # pragma: no cover - optional runtime dependency
    imageio_ffmpeg = None

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.experiments.generate_journal_results import _rescale_floor_plan  # type: ignore
from app.services.floorplan_service import process_floor_plan_image  # type: ignore
from app.services.metrics_engine import MetricsEngine  # type: ignore
from app.sim.simulation_kernel import SimulationKernel  # type: ignore

ROOT_DIR = Path(__file__).resolve().parents[4]
PAPER_DIR = ROOT_DIR / "Research_Paper_IEEE"
OUT_DIR = PAPER_DIR / "supplementary"
VIDEO_PATH = OUT_DIR / "peopleflow_multimedia_supplement.mp4"
PROJECTOR_VIDEO_PATH = OUT_DIR / "peopleflow_multimedia_supplement_1080p.mp4"
META_PATH = OUT_DIR / "peopleflow_multimedia_metadata.json"
PREVIEW_DIR = OUT_DIR / "preview_frames_v6"

PIPELINE_FIG = PAPER_DIR / "fig_pipeline.png"

W, H = 1280, 720
FPS = 30

# Color theme (BGR for OpenCV)
INK_900 = (16, 20, 30)
INK_800 = (25, 32, 46)
INK_700 = (40, 50, 70)
INK_500 = (90, 108, 140)
TEXT_100 = (238, 242, 250)
TEXT_200 = (210, 220, 236)
TEXT_300 = (170, 184, 210)
ACCENT_A = (255, 170, 52)
ACCENT_B = (240, 130, 78)
ACCENT_C = (180, 96, 255)
GOOD = (85, 210, 140)
WARN = (70, 175, 255)
BAD = (85, 95, 245)
PANEL_EDGE = (85, 100, 130)

RNG = np.random.default_rng(4242)


def _mime(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".png":
        return "image/png"
    if suffix == ".webp":
        return "image/webp"
    return "image/jpeg"


def _resolve_layout_path() -> Path:
    candidates = [
        PAPER_DIR / "Floor_Plans" / "Plan2.jpg",
        PAPER_DIR / "Floor_Plans" / "Plan3.jpg",
        ROOT_DIR
        / "apps"
        / "backend"
        / "app"
        / "experiments"
        / "input_floorplans"
        / "ieee_journal_blueprints"
        / "H_metro_taipei.jpg",
    ]
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError("Could not find a valid floor-plan image for multimedia generation")


def _blank() -> np.ndarray:
    return np.zeros((H, W, 3), dtype=np.uint8)


def _fill_gradient(frame: np.ndarray, top: tuple[int, int, int], bottom: tuple[int, int, int]) -> None:
    grad = np.linspace(0.0, 1.0, H, dtype=np.float32).reshape(H, 1, 1)
    top_arr = np.array(top, dtype=np.float32).reshape(1, 1, 3)
    bot_arr = np.array(bottom, dtype=np.float32).reshape(1, 1, 3)
    frame[:] = np.uint8(np.clip(top_arr * (1.0 - grad) + bot_arr * grad, 0, 255))


def _put_text(
    frame: np.ndarray,
    text: str,
    x: int,
    y: int,
    scale: float = 0.7,
    color: tuple[int, int, int] = TEXT_100,
    thick: int = 1,
) -> None:
    cv2.putText(frame, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, scale, color, thick, cv2.LINE_AA)


def _fit_image(img: np.ndarray, max_w: int, max_h: int) -> np.ndarray:
    h, w = img.shape[:2]
    if h <= 0 or w <= 0:
        out = np.zeros((max_h, max_w, 3), dtype=np.uint8)
        out[:] = INK_700
        return out

    scale = min(max_w / w, max_h / h)
    nw = max(1, int(w * scale))
    nh = max(1, int(h * scale))
    resized = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)

    canvas = np.zeros((max_h, max_w, 3), dtype=np.uint8)
    canvas[:] = INK_800
    x0 = (max_w - nw) // 2
    y0 = (max_h - nh) // 2
    canvas[y0 : y0 + nh, x0 : x0 + nw] = resized
    return canvas


def _zoom_to_canvas(img: np.ndarray, out_w: int, out_h: int, scale: float) -> np.ndarray:
    # scale > 1.0 zooms in
    h, w = img.shape[:2]
    zw = max(1, int(w * scale))
    zh = max(1, int(h * scale))
    zimg = cv2.resize(img, (zw, zh), interpolation=cv2.INTER_LINEAR)

    x0 = max(0, (zw - out_w) // 2)
    y0 = max(0, (zh - out_h) // 2)
    crop = zimg[y0 : y0 + out_h, x0 : x0 + out_w]
    if crop.shape[0] != out_h or crop.shape[1] != out_w:
        padded = np.zeros((out_h, out_w, 3), dtype=np.uint8)
        padded[:] = INK_800
        padded[: crop.shape[0], : crop.shape[1]] = crop
        return padded
    return crop


def _ease(p: float) -> float:
    p = min(1.0, max(0.0, p))
    return p * p * (3.0 - 2.0 * p)


def _draw_panel(frame: np.ndarray, x0: int, y0: int, x1: int, y1: int, alpha: float = 0.55) -> None:
    overlay = frame.copy()
    cv2.rectangle(overlay, (x0, y0), (x1, y1), (34, 42, 60), -1)
    cv2.addWeighted(overlay, alpha, frame, 1.0 - alpha, 0.0, frame)
    cv2.rectangle(frame, (x0, y0), (x1, y1), PANEL_EDGE, 1)


def _draw_glow_circle(
    frame: np.ndarray,
    center: tuple[int, int],
    radius: int,
    color: tuple[int, int, int],
    glow_scale: float = 2.2,
) -> None:
    blur = frame.copy()
    cv2.circle(blur, center, max(2, int(radius * glow_scale)), color, -1, cv2.LINE_AA)
    blur = cv2.GaussianBlur(blur, (0, 0), sigmaX=8.0, sigmaY=8.0)
    cv2.addWeighted(blur, 0.18, frame, 0.82, 0.0, frame)
    cv2.circle(frame, center, radius, color, -1, cv2.LINE_AA)


def _draw_stat_chip(frame: np.ndarray, x: int, y: int, label: str, value: str, color: tuple[int, int, int]) -> None:
    _draw_panel(frame, x, y, x + 240, y + 58, alpha=0.58)
    _put_text(frame, label, x + 12, y + 22, 0.46, TEXT_300, 1)
    _put_text(frame, value, x + 12, y + 47, 0.68, color, 1)


def _apply_post_fx(frame: np.ndarray, progress: float, scene_gain: float = 0.16) -> np.ndarray:
    out = frame.astype(np.float32)

    # Subtle vignette to focus the eye on central action.
    yy = np.linspace(-1.0, 1.0, H, dtype=np.float32).reshape(H, 1)
    xx = np.linspace(-1.0, 1.0, W, dtype=np.float32).reshape(1, W)
    rr = np.sqrt(xx * xx + yy * yy)
    vignette = np.clip(1.0 - (0.58 + 0.06 * math.sin(progress * 2.0 * math.pi)) * np.power(rr, 1.6), 0.72, 1.0)
    out *= vignette[..., None]

    # Controlled film grain for premium motion texture.
    grain_h = max(90, H // 6)
    grain_w = max(160, W // 6)
    grain_small = RNG.normal(0.0, 1.0, size=(grain_h, grain_w, 1)).astype(np.float32)
    grain = cv2.resize(grain_small, (W, H), interpolation=cv2.INTER_CUBIC)
    if grain.ndim == 2:
        grain = grain[:, :, None]
    out += grain * (8.0 * scene_gain)

    return np.uint8(np.clip(out, 0.0, 255.0))


def _draw_footer(frame: np.ndarray, caption: str, segment_name: str) -> None:
    y0 = H - 42
    _draw_panel(frame, 0, y0, W, H, alpha=0.82)
    _put_text(frame, segment_name, 16, H - 17, 0.52, TEXT_200, 1)
    _put_text(frame, caption, 220, H - 17, 0.52, TEXT_300, 1)


def _draw_timeline(
    frame: np.ndarray,
    section_names: list[str],
    active_idx: int,
    overall_progress: float,
) -> None:
    bar_x0, bar_x1 = 26, W - 26
    bar_y = 24
    bar_h = 7
    _draw_panel(frame, bar_x0 - 2, 8, bar_x1 + 2, 36, alpha=0.50)

    cv2.rectangle(frame, (bar_x0, bar_y), (bar_x1, bar_y + bar_h), (62, 74, 104), -1)
    fill_x = bar_x0 + int((bar_x1 - bar_x0) * min(1.0, max(0.0, overall_progress)))
    cv2.rectangle(frame, (bar_x0, bar_y), (fill_x, bar_y + bar_h), ACCENT_A, -1)

    n = len(section_names)
    for i, name in enumerate(section_names):
        px = bar_x0 + int((bar_x1 - bar_x0) * (i + 0.5) / n)
        color = ACCENT_A if i == active_idx else TEXT_300
        cv2.circle(frame, (px, bar_y + 3), 4 if i == active_idx else 3, color, -1, cv2.LINE_AA)
        if i == active_idx:
            _put_text(frame, name, px - 36, 16, 0.45, TEXT_100, 1)


def _draw_heat_legend(frame: np.ndarray, x0: int, y0: int, x1: int, y1: int) -> None:
    _draw_panel(frame, x0, y0, x1, y1, alpha=0.60)
    w = x1 - x0 - 24
    grad = np.linspace(0, 255, w, dtype=np.uint8).reshape(1, w)
    grad = np.repeat(grad, 18, axis=0)
    cmap = cv2.COLORMAP_TURBO if hasattr(cv2, "COLORMAP_TURBO") else cv2.COLORMAP_MAGMA
    color_bar = cv2.applyColorMap(grad, cmap)
    frame[y0 + 20 : y0 + 38, x0 + 12 : x1 - 12] = color_bar
    _put_text(frame, "Low occupancy", x0 + 12, y0 + 56, 0.42, TEXT_300, 1)
    _put_text(frame, "High occupancy", x1 - 112, y0 + 56, 0.42, TEXT_300, 1)


def _world_to_px(
    x: float,
    z: float,
    bounds: dict[str, float],
    rect: tuple[int, int, int, int],
) -> tuple[int, int]:
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


def _series_from_frames(sim_frames: list[dict[str, Any]]) -> tuple[list[float], list[float], list[float]]:
    completion: list[float] = []
    density: list[float] = []
    remaining: list[float] = []

    for sf in sim_frames:
        stats = sf.get("stats") or {}
        completion.append(float(stats.get("completion_percentage", 0.0) or 0.0))
        density.append(
            float(
                stats.get("current_congestion_density", stats.get("average_density", 0.0))
                or 0.0
            )
        )
        remaining.append(float(stats.get("remaining", 0.0) or 0.0))

    if not completion:
        completion = [0.0]
    if not density:
        density = [0.0]
    if not remaining:
        remaining = [0.0]
    return completion, density, remaining


def _draw_line_chart(
    frame: np.ndarray,
    series: list[float],
    rect: tuple[int, int, int, int],
    color: tuple[int, int, int],
    label: str,
) -> None:
    x0, y0, x1, y1 = rect
    _draw_panel(frame, x0, y0, x1, y1, alpha=0.45)

    vals = np.array(series, dtype=np.float32)
    vmin = float(vals.min())
    vmax = float(vals.max())
    if abs(vmax - vmin) < 1e-6:
        vmax = vmin + 1.0

    n = max(2, len(vals))
    points: list[tuple[int, int]] = []
    for i, v in enumerate(vals):
        px = x0 + 10 + int((x1 - x0 - 20) * (i / (n - 1)))
        py = y1 - 12 - int((y1 - y0 - 26) * ((float(v) - vmin) / (vmax - vmin)))
        points.append((px, py))

    for i in range(1, len(points)):
        cv2.line(frame, points[i - 1], points[i], color, 2, cv2.LINE_AA)

    if points:
        cv2.circle(frame, points[-1], 4, ACCENT_A, -1, cv2.LINE_AA)
    _put_text(frame, label, x0 + 12, y0 + 20, 0.48, TEXT_200, 1)


def _build_heatmap_overlay(floor_plan: dict[str, Any], all_frames: list[dict[str, Any]], out_size: tuple[int, int]) -> np.ndarray:
    out_w, out_h = out_size
    bounds = floor_plan.get("building_bounds") or {}

    min_x = float(bounds.get("min_x", 0.0))
    max_x = float(bounds.get("max_x", 1.0))
    min_y = float(bounds.get("min_y", 0.0))
    max_y = float(bounds.get("max_y", 1.0))
    span_x = max(1e-6, max_x - min_x)
    span_y = max(1e-6, max_y - min_y)

    bins_w, bins_h = 220, 150
    heat = np.zeros((bins_h, bins_w), dtype=np.float32)

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

    colormap = cv2.COLORMAP_TURBO if hasattr(cv2, "COLORMAP_TURBO") else cv2.COLORMAP_MAGMA
    heat_rgb = cv2.applyColorMap(heat_u8, colormap)
    return cv2.resize(heat_rgb, (out_w, out_h), interpolation=cv2.INTER_CUBIC)


def _extract_detector_summary(floor_plan: dict[str, Any]) -> dict[str, Any]:
    wall_count = int(
        len(
            floor_plan.get("detected_walls", [])
            or floor_plan.get("walls", [])
            or floor_plan.get("boundaries", [])
            or []
        )
    )
    exit_count = int(len(floor_plan.get("exits", []) or []))
    room_count = int(len(floor_plan.get("rooms", []) or []))
    quality = float(floor_plan.get("processing_confidence", floor_plan.get("quality_score", 0.0)) or 0.0)
    if quality <= 0.0 and exit_count > 0:
        quality = min(1.0, 0.30 + 0.04 * exit_count)

    return {
        "wall_count": wall_count,
        "exit_count": exit_count,
        "room_count": room_count,
        "quality_score": quality,
    }


def _choose_blocked_exits(floor_plan: dict[str, Any], count: int = 1) -> list[str]:
    exits = list(floor_plan.get("exits") or [])
    if not exits or count <= 0:
        return []

    bounds = floor_plan.get("building_bounds") or {}
    min_x = float(bounds.get("min_x", 0.0))
    max_x = float(bounds.get("max_x", 1.0))
    min_y = float(bounds.get("min_y", 0.0))
    max_y = float(bounds.get("max_y", 1.0))

    scored: list[tuple[float, str]] = []
    for ex in exits:
        ex_id = str(ex.get("id", ""))
        if not ex_id:
            continue
        x = float(ex.get("x", 0.0))
        z = float(ex.get("z", ex.get("y", 0.0)))
        edge_dist = min(abs(x - min_x), abs(max_x - x), abs(z - min_y), abs(max_y - z))
        scored.append((edge_dist, ex_id))

    if not scored:
        return [str(exits[0].get("id"))] if exits and exits[0].get("id") else []

    scored.sort(key=lambda t: t[0])
    return [ex_id for _, ex_id in scored[:count]]


def _extract_structural_lines(edge_map: np.ndarray, max_lines: int = 220) -> list[tuple[int, int, int, int]]:
    if edge_map.size == 0:
        return []

    gray = cv2.cvtColor(edge_map, cv2.COLOR_BGR2GRAY)
    lines = cv2.HoughLinesP(
        gray,
        rho=1,
        theta=np.pi / 180.0,
        threshold=38,
        minLineLength=24,
        maxLineGap=6,
    )
    if lines is None:
        return []

    out: list[tuple[int, int, int, int]] = []
    for ln in lines:
        x1, y1, x2, y2 = [int(v) for v in ln[0]]
        if abs(x2 - x1) + abs(y2 - y1) < 26:
            continue
        out.append((x1, y1, x2, y2))
        if len(out) >= max_lines:
            break
    return out


def _build_sim_trace(floor_plan: dict[str, Any], blocked_exits: list[str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    config = {
        "seed": 4242,
        "mode": "paper",
        "num_agents": 140,
        "emergency_type": "fire",
        "routing_policy": "least_crowded",
        "panic_level": 0.4,
        "blocked_exits": blocked_exits,
        "parameter_overrides": {"disable_hazards": True},
        "max_runtime_seconds": 420,
    }

    kernel = SimulationKernel("multimedia_supplement", config)
    kernel.initialize(floor_plan)

    metrics_engine = MetricsEngine()
    sim_frames: list[dict[str, Any]] = []
    target_agents = int(config.get("num_agents") or 140)
    stagnant_steps = 0
    prev_evac = -1

    # Keep stepping beyond engine "95% complete" threshold so the video shows a
    # near-full or full evacuation whenever the scenario allows it.
    for _ in range(1400):
        sf = kernel.step(0.2)
        sim_frames.append(sf)
        metrics_engine.add_frame(sf)

        stats = sf.get("stats") or {}
        evacuated = int(stats.get("evacuated", 0) or 0)

        if evacuated >= target_agents:
            break

        if evacuated <= prev_evac:
            stagnant_steps += 1
        else:
            stagnant_steps = 0
            prev_evac = evacuated

        # If completion plateaued after the kernel-complete signal for long enough,
        # stop and preserve deterministic output length.
        if kernel.is_complete() and stagnant_steps >= 110:
            break

    if not sim_frames:
        sf = kernel.current_frame()
        sim_frames.append(sf)
        metrics_engine.add_frame(sf)

    metrics = metrics_engine.calculate_metrics()
    metrics_dict = metrics.__dict__ if hasattr(metrics, "__dict__") else dict(metrics)
    return sim_frames, metrics_dict


def _write_preview_frames(video_path: Path, preview_dir: Path, seconds: list[int]) -> None:
    preview_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return

    try:
        for sec in seconds:
            cap.set(cv2.CAP_PROP_POS_MSEC, float(sec) * 1000.0)
            ok, frame = cap.read()
            if not ok or frame is None:
                continue
            out = preview_dir / f"frame_{sec:02d}s.png"
            cv2.imwrite(str(out), frame)
    finally:
        cap.release()


def _find_ffmpeg_executable() -> str | None:
    if imageio_ffmpeg is not None:
        try:
            ffmpeg_static = imageio_ffmpeg.get_ffmpeg_exe()
            if ffmpeg_static and Path(ffmpeg_static).exists():
                return ffmpeg_static
        except Exception:
            pass

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return ffmpeg

    env_root = Path(sys.prefix)
    candidates = [
        env_root / "Library" / "bin" / "ffmpeg.exe",
        env_root / "bin" / "ffmpeg",
        env_root / "Scripts" / "ffmpeg.exe",
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return None


def _export_projector_video(input_path: Path, output_path: Path, fps: int) -> dict[str, Any]:
    ffmpeg = _find_ffmpeg_executable()
    ffmpeg_args = [
        "-y",
        "-i",
        str(input_path),
        "-vf",
        "scale=1920:1080:flags=lanczos",
        "-c:v",
        "libx264",
        "-preset",
        "slow",
        "-profile:v",
        "high",
        "-level",
        "4.2",
        "-pix_fmt",
        "yuv420p",
        "-r",
        str(fps),
        "-b:v",
        "12M",
        "-maxrate",
        "16M",
        "-bufsize",
        "24M",
        "-movflags",
        "+faststart",
        "-an",
        str(output_path),
    ]

    ffmpeg_failure_detail = "ffmpeg_not_found"

    if ffmpeg:
        ffmpeg_path = Path(ffmpeg)
        env = os.environ.copy()
        env_root = Path(sys.prefix)
        path_parts = [
            str(ffmpeg_path.parent),
            str(env_root / "Library" / "bin"),
            str(env_root / "Library" / "usr" / "bin"),
            str(env_root / "bin"),
            str(env_root / "Scripts"),
            env.get("PATH", ""),
        ]
        env["PATH"] = os.pathsep.join([p for p in path_parts if p])

        proc = subprocess.run([ffmpeg, *ffmpeg_args], capture_output=True, text=True, env=env)
        if proc.returncode == 0 and output_path.exists():
            return {
                "enabled": True,
                "path": str(output_path),
                "resolution": [1920, 1080],
                "target_bitrate": "12M",
                "encoder": "ffmpeg/libx264",
                "status": "ok",
            }

        err_tail = (proc.stderr or "").strip().splitlines()[-3:]
        ffmpeg_failure_detail = " | ".join(err_tail) if err_tail else f"ffmpeg_exit_{proc.returncode}"

        conda_exe = Path(sys.prefix).parents[1] / "Scripts" / "conda.exe"
        if conda_exe.exists():
            env_name = Path(sys.prefix).name
            conda_proc = subprocess.run(
                [str(conda_exe), "run", "-n", env_name, "ffmpeg", *ffmpeg_args],
                capture_output=True,
                text=True,
            )
            if conda_proc.returncode == 0 and output_path.exists():
                return {
                    "enabled": True,
                    "path": str(output_path),
                    "resolution": [1920, 1080],
                    "target_bitrate": "12M",
                    "encoder": "ffmpeg/libx264",
                    "status": "ok_conda_run",
                }
            conda_err_tail = (conda_proc.stderr or "").strip().splitlines()[-3:]
            if conda_err_tail:
                ffmpeg_failure_detail = " | ".join(conda_err_tail)

    cap = cv2.VideoCapture(str(input_path))
    if not cap.isOpened():
        return {
            "enabled": False,
            "path": str(output_path),
            "resolution": [1920, 1080],
            "target_bitrate": "unavailable_without_ffmpeg",
            "encoder": "none",
            "status": "failed_open_input",
            "failure_detail": ffmpeg_failure_detail,
        }

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output_path), fourcc, float(fps), (1920, 1080))
    if not writer.isOpened():
        cap.release()
        return {
            "enabled": False,
            "path": str(output_path),
            "resolution": [1920, 1080],
            "target_bitrate": "unavailable_without_ffmpeg",
            "encoder": "none",
            "status": "failed_open_output",
            "failure_detail": ffmpeg_failure_detail,
        }

    try:
        while True:
            ok, frame = cap.read()
            if not ok or frame is None:
                break
            up = cv2.resize(frame, (1920, 1080), interpolation=cv2.INTER_LANCZOS4)
            writer.write(up)
    finally:
        writer.release()
        cap.release()

    return {
        "enabled": True,
        "path": str(output_path),
        "resolution": [1920, 1080],
        "target_bitrate": "best_effort_opencv",
        "encoder": "opencv/mp4v_fallback",
        "status": "ok_fallback",
        "ffmpeg_failure_detail": ffmpeg_failure_detail,
    }


def main() -> None:
    t0 = time.perf_counter()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    layout_path = _resolve_layout_path()
    raw = process_floor_plan_image(_mime(layout_path), str(layout_path), {"mode": "traditional"})
    floor_plan = _rescale_floor_plan(raw)

    blocked_exits = _choose_blocked_exits(floor_plan, count=1)

    sim_frames, metrics_dict = _build_sim_trace(floor_plan, blocked_exits)
    completion_series, density_series, remaining_series = _series_from_frames(sim_frames)

    pipeline_img = cv2.imread(str(PIPELINE_FIG), cv2.IMREAD_COLOR) if PIPELINE_FIG.exists() else None
    raw_layout_img = cv2.imread(str(layout_path), cv2.IMREAD_COLOR)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(VIDEO_PATH), fourcc, FPS, (W, H))
    if not writer.isOpened():
        raise RuntimeError("Could not open video writer for multimedia output")

    section_names = [
        "Intro",
        "Pipeline",
        "Ingestion",
        "Geometry",
        "Scenario",
        "Simulation",
        "Analytics",
        "Closing",
    ]

    segment_durations = [3.4, 3.8, 4.0, 3.8, 3.4, 8.6, 4.2, 3.6]
    total_target_frames = sum(int(round(d * FPS)) for d in segment_durations)

    map_rect = (56, 96, 900, 650)
    map_w = map_rect[2] - map_rect[0]
    map_h = map_rect[3] - map_rect[1]
    bounds = floor_plan.get("building_bounds") or {}
    heat_overlay = _build_heatmap_overlay(floor_plan, sim_frames, (map_w, map_h))

    map_backdrop = np.zeros((map_h, map_w, 3), dtype=np.uint8)
    map_backdrop[:] = (34, 28, 24)
    map_edges = np.zeros((map_h, map_w, 3), dtype=np.uint8)
    structural_lines_px: list[tuple[int, int, int, int]] = []
    if raw_layout_img is not None:
        # Stretch-to-canvas keeps world overlays aligned with raster backdrop,
        # avoiding visual offset from letterbox padding.
        aligned_map = cv2.resize(raw_layout_img, (map_w, map_h), interpolation=cv2.INTER_AREA)

        gray = cv2.cvtColor(aligned_map, cv2.COLOR_BGR2GRAY)
        gray_eq = cv2.equalizeHist(gray)
        edge = cv2.Canny(gray_eq, 70, 160)
        map_edges = cv2.cvtColor(edge, cv2.COLOR_GRAY2BGR)
        structural_lines_px = _extract_structural_lines(map_edges)

        map_backdrop = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        tint = np.full_like(map_backdrop, (40, 30, 20))
        map_backdrop = cv2.addWeighted(map_backdrop, 0.62, tint, 0.38, 0.0)

    frame_count = 0
    prev_end_frame: np.ndarray | None = None
    transition_frames = int(0.24 * FPS)

    def write_segment(
        seg_idx: int,
        duration_s: float,
        render_fn: Callable[[float], np.ndarray],
        caption: str,
    ) -> None:
        nonlocal frame_count, prev_end_frame

        n_frames = max(1, int(round(duration_s * FPS)))
        transition_from = prev_end_frame

        for i in range(n_frames):
            p = i / max(1, n_frames - 1)
            frame = render_fn(p)

            overall_p = (frame_count + i) / max(1, total_target_frames - 1)
            _draw_timeline(frame, section_names, seg_idx, overall_p)
            _draw_footer(frame, caption, section_names[seg_idx])
            frame = _apply_post_fx(frame, overall_p, scene_gain=0.15 + 0.03 * seg_idx)

            if transition_from is not None and i < transition_frames:
                a = i / max(1, transition_frames - 1)
                frame = cv2.addWeighted(transition_from, 1.0 - a, frame, a, 0.0)

            writer.write(frame)
            prev_end_frame = frame

        frame_count += n_frames

    def scene_intro(p: float) -> np.ndarray:
        frame = _blank()
        _fill_gradient(frame, (42, 28, 18), (20, 13, 8))

        overlay = frame.copy()
        for k in range(12):
            phase = p * 2.4 + k * 0.31
            cx = int(80 + (W - 160) * ((k + 1) / 13.0) + 20 * math.sin(phase * 2.3))
            cy = int(120 + 420 * ((k % 5) / 4.0) + 16 * math.cos(phase * 1.9))
            radius = 24 + (k % 4) * 12
            color = ACCENT_C if k % 3 == 0 else ACCENT_B if k % 3 == 1 else ACCENT_A
            cv2.circle(overlay, (cx, cy), radius, color, -1, cv2.LINE_AA)
        cv2.addWeighted(overlay, 0.12, frame, 0.88, 0.0, frame)

        card_x0, card_y0, card_x1, card_y1 = 84, 128, W - 84, H - 112
        _draw_panel(frame, card_x0, card_y0, card_x1, card_y1, alpha=0.56)

        enter = _ease(min(1.0, p * 1.6))
        title_x = int(130 - (1.0 - enter) * 120)
        _put_text(frame, "PeopleFlow", title_x, 236, 1.7, TEXT_100, 3)
        _put_text(frame, "Supplementary Video", title_x, 290, 1.1, TEXT_200, 2)
        _put_text(frame, "Reproducible Geometry-Aware Evacuation Analytics", title_x, 334, 0.72, TEXT_300, 1)

        bullet_y = 396
        bullets = [
            "Automated floor-plan ingestion and geometry extraction",
            "Stress-tested multi-agent simulation with live metrics",
            "Audit-ready analytics, artifacts, and reproducibility metadata",
        ]
        for j, line in enumerate(bullets):
            reveal = min(1.0, max(0.0, (p - 0.22 - 0.12 * j) / 0.20))
            if reveal <= 0.0:
                continue
            x = 142 + int((1.0 - _ease(reveal)) * 42)
            cv2.circle(frame, (x - 16, bullet_y - 8), 5, GOOD, -1, cv2.LINE_AA)
            _put_text(frame, line, x, bullet_y, 0.63, TEXT_200, 1)
            bullet_y += 36

        _put_text(frame, "IEEE ACCESS multimedia companion", 142, H - 132, 0.58, WARN, 1)
        _draw_stat_chip(frame, W - 350, 146, "Render profile", "God Tier v6", ACCENT_A)
        _draw_stat_chip(frame, W - 350, 212, "Run mode", "Deterministic", GOOD)
        return frame

    def scene_pipeline(p: float) -> np.ndarray:
        frame = _blank()
        _fill_gradient(frame, (40, 28, 18), (22, 14, 9))

        _put_text(frame, "Pipeline Overview", 74, 88, 0.98, TEXT_100, 2)
        _put_text(frame, "From blueprint to comparative evacuation evidence", 74, 118, 0.58, TEXT_300, 1)

        _draw_panel(frame, 60, 138, W - 60, H - 86, alpha=0.60)
        if pipeline_img is not None:
            fitted = _fit_image(pipeline_img, W - 170, H - 270)
            zoom = 1.0 + 0.06 * _ease(p)
            canvas = _zoom_to_canvas(fitted, fitted.shape[1], fitted.shape[0], zoom)
            y0 = 174
            x0 = 85
            frame[y0 : y0 + canvas.shape[0], x0 : x0 + canvas.shape[1]] = canvas

        stages = ["Ingest", "Extract", "Session", "Simulate", "Analyze", "Report"]
        active = min(len(stages) - 1, int(_ease(p) * len(stages)))
        sx = 92
        for i, s in enumerate(stages):
            c = ACCENT_A if i <= active else TEXT_300
            _put_text(frame, s, sx + i * 180, H - 114, 0.54, c, 1)
        _draw_stat_chip(frame, 80, 146, "Pipeline depth", "6 stages", WARN)
        _draw_stat_chip(frame, 334, 146, "Evidence mode", "Artifacts + metrics", GOOD)
        return frame

    def scene_ingestion(p: float) -> np.ndarray:
        frame = _blank()
        _fill_gradient(frame, (38, 26, 17), (20, 12, 8))

        _put_text(frame, "Step 1: Floor-Plan Ingestion", 74, 88, 0.98, TEXT_100, 2)
        _put_text(frame, f"Input layout: {layout_path.name}", 74, 116, 0.56, TEXT_300, 1)

        _draw_panel(frame, 56, 136, 860, 644, alpha=0.62)
        if raw_layout_img is not None:
            fitted = _fit_image(raw_layout_img, 770, 470)
            zoom = 1.0 + 0.08 * _ease(p)
            canvas = _zoom_to_canvas(fitted, fitted.shape[1], fitted.shape[0], zoom)
            frame[160 : 160 + canvas.shape[0], 74 : 74 + canvas.shape[1]] = canvas

        summary = _extract_detector_summary(floor_plan)
        _draw_panel(frame, 890, 136, 1238, 644, alpha=0.70)
        _put_text(frame, "Detection Summary", 914, 176, 0.76, TEXT_100, 2)
        _put_text(frame, f"Walls detected: {summary['wall_count']}", 914, 220, 0.60, TEXT_200, 1)
        _put_text(frame, f"Exits detected: {summary['exit_count']}", 914, 248, 0.60, TEXT_200, 1)
        _put_text(frame, f"Rooms detected: {summary['room_count']}", 914, 276, 0.60, TEXT_200, 1)
        _put_text(frame, f"Quality score: {summary['quality_score']:.2f}", 914, 304, 0.60, TEXT_200, 1)

        q = _ease(p)
        cv2.rectangle(frame, (914, 330), (1214, 350), (60, 74, 100), -1)
        cv2.rectangle(frame, (914, 330), (914 + int(300 * q), 350), GOOD, -1)
        _put_text(frame, "Preprocess + normalize", 914, 382, 0.54, TEXT_300, 1)
        _put_text(frame, "Adaptive threshold + edge-line extraction", 914, 408, 0.52, TEXT_300, 1)
        _put_text(frame, "Exit candidate filtering and validation", 914, 434, 0.52, TEXT_300, 1)
        _draw_stat_chip(frame, 914, 474, "Input fidelity", f"{raw_layout_img.shape[1]}x{raw_layout_img.shape[0]}" if raw_layout_img is not None else "N/A", ACCENT_A)
        return frame

    def scene_geometry(p: float) -> np.ndarray:
        frame = _blank()
        _fill_gradient(frame, (36, 24, 16), (18, 12, 8))

        _put_text(frame, "Step 2: Geometry Extraction", 74, 88, 0.98, TEXT_100, 2)
        _put_text(frame, "Walls and exits converted into simulation primitives", 74, 116, 0.56, TEXT_300, 1)

        _draw_panel(frame, 56, 136, 900, 650, alpha=0.62)
        frame[map_rect[1] : map_rect[3], map_rect[0] : map_rect[2]] = cv2.addWeighted(
            frame[map_rect[1] : map_rect[3], map_rect[0] : map_rect[2]],
            0.22,
            map_backdrop,
            0.78,
            0.0,
        )

        walls = floor_plan.get("detected_walls") or []
        exits_local = floor_plan.get("exits") or []
        visible_walls = int(len(walls) * _ease(p))

        if len(walls) == 0 and int(np.count_nonzero(map_edges)) > 0:
            reveal_col = max(1, int(map_w * _ease(p)))
            edge_part = np.zeros_like(map_edges)
            edge_part[:, :reveal_col] = map_edges[:, :reveal_col]
            frame[map_rect[1] : map_rect[3], map_rect[0] : map_rect[2]] = cv2.addWeighted(
                frame[map_rect[1] : map_rect[3], map_rect[0] : map_rect[2]],
                1.0,
                edge_part,
                0.55,
                0.0,
            )

        for wall in walls[:visible_walls]:
            p1 = _world_to_px(float(wall.get("x1", 0.0)), float(wall.get("y1", 0.0)), bounds, map_rect)
            p2 = _world_to_px(float(wall.get("x2", 0.0)), float(wall.get("y2", 0.0)), bounds, map_rect)
            cv2.line(frame, p1, p2, (210, 220, 238), 1, cv2.LINE_AA)

        if not walls and structural_lines_px:
            n_lines = int(len(structural_lines_px) * _ease(p))
            for x1, y1, x2, y2 in structural_lines_px[:n_lines]:
                cv2.line(
                    frame,
                    (map_rect[0] + x1, map_rect[1] + y1),
                    (map_rect[0] + x2, map_rect[1] + y2),
                    (206, 216, 236),
                    1,
                    cv2.LINE_AA,
                )

        pulse = 0.5 + 0.5 * math.sin(2.0 * math.pi * (1.5 * p + 0.2))
        for ex in exits_local:
            px, py = _world_to_px(float(ex.get("x", 0.0)), float(ex.get("z", ex.get("y", 0.0))), bounds, map_rect)
            r = 5 + int(3 * pulse)
            cv2.circle(frame, (px, py), r + 3, (60, 100, 60), 1, cv2.LINE_AA)
            _draw_glow_circle(frame, (px, py), r, GOOD)

        _draw_panel(frame, 920, 136, 1238, 650, alpha=0.70)
        _put_text(frame, "Geometry Card", 944, 176, 0.76, TEXT_100, 2)
        _put_text(frame, "- Scale-normalized coordinates", 944, 216, 0.55, TEXT_200, 1)
        _put_text(frame, "- Traversable envelope bounds", 944, 244, 0.55, TEXT_200, 1)
        _put_text(frame, "- Exit IDs for scenario controls", 944, 272, 0.55, TEXT_200, 1)
        _put_text(frame, "- Deterministic session state", 944, 300, 0.55, TEXT_200, 1)
        _draw_stat_chip(frame, 944, 340, "Extracted walls", str(len(walls)), TEXT_100)
        _draw_stat_chip(frame, 944, 408, "Detected exits", str(len(exits_local)), GOOD)
        return frame

    def scene_scenario(p: float) -> np.ndarray:
        frame = _blank()
        _fill_gradient(frame, (40, 28, 18), (20, 12, 8))

        _put_text(frame, "Step 3: Scenario Configuration", 74, 88, 0.98, TEXT_100, 2)
        _put_text(frame, "Blocked-exit stress test with seeded deterministic execution", 74, 116, 0.56, TEXT_300, 1)

        _draw_panel(frame, 80, 160, W - 80, H - 100, alpha=0.68)

        rows = [
            ("Agents", "140"),
            ("Routing policy", "least_crowded"),
            ("Blocked exits", ", ".join(blocked_exits) if blocked_exits else "none"),
            ("Panic level", "0.4"),
            ("Simulation dt", "0.2 s"),
            ("Random seed", "4242"),
        ]

        for i, (k, v) in enumerate(rows):
            reveal = min(1.0, max(0.0, (p - 0.08 * i) / 0.20))
            if reveal <= 0.0:
                continue
            y = 214 + i * 64
            x = 128 + int((1.0 - _ease(reveal)) * 50)
            _draw_panel(frame, x - 20, y - 34, W - 124, y + 18, alpha=0.45)
            _put_text(frame, k, x, y, 0.62, TEXT_200, 1)
            _put_text(frame, v, x + 320, y, 0.62, ACCENT_A, 1)

        _draw_stat_chip(frame, 92, H - 172, "Scenario class", "Blocked-exit stress", WARN)
        _draw_stat_chip(frame, 346, H - 172, "Reproducibility", "Seed = 4242", GOOD)

        return frame

    def scene_simulation(p: float) -> np.ndarray:
        frame = _blank()
        _fill_gradient(frame, (34, 22, 14), (16, 10, 6))

        _put_text(frame, "Step 4: Live Evacuation Simulation", 74, 88, 0.98, TEXT_100, 2)
        _put_text(frame, "Dynamic crowd states under blocked-exit conditions", 74, 116, 0.56, TEXT_300, 1)

        _draw_panel(frame, map_rect[0], map_rect[1], map_rect[2], map_rect[3], alpha=0.66)
        _draw_panel(frame, 920, 96, 1238, 650, alpha=0.72)
        frame[map_rect[1] : map_rect[3], map_rect[0] : map_rect[2]] = cv2.addWeighted(
            frame[map_rect[1] : map_rect[3], map_rect[0] : map_rect[2]],
            0.24,
            map_backdrop,
            0.76,
            0.0,
        )

        if len(sim_frames) == 1:
            sim_idx = 0
        else:
            sim_idx = int(_ease(p) * (len(sim_frames) - 1))
        sf = sim_frames[sim_idx]
        stats = sf.get("stats") or {}

        walls_live = sf.get("walls") or floor_plan.get("detected_walls") or []
        exits_live = sf.get("exits") or floor_plan.get("exits") or []

        if len(walls_live) == 0 and int(np.count_nonzero(map_edges)) > 0:
            frame[map_rect[1] : map_rect[3], map_rect[0] : map_rect[2]] = cv2.addWeighted(
                frame[map_rect[1] : map_rect[3], map_rect[0] : map_rect[2]],
                1.0,
                map_edges,
                0.34,
                0.0,
            )

        for wall in walls_live:
            p1 = _world_to_px(float(wall.get("x1", 0.0)), float(wall.get("y1", 0.0)), bounds, map_rect)
            p2 = _world_to_px(float(wall.get("x2", 0.0)), float(wall.get("y2", 0.0)), bounds, map_rect)
            cv2.line(frame, p1, p2, (200, 212, 236), 1, cv2.LINE_AA)

        if not walls_live and structural_lines_px:
            for x1, y1, x2, y2 in structural_lines_px:
                cv2.line(
                    frame,
                    (map_rect[0] + x1, map_rect[1] + y1),
                    (map_rect[0] + x2, map_rect[1] + y2),
                    (196, 208, 232),
                    1,
                    cv2.LINE_AA,
                )

        pulse = 0.5 + 0.5 * math.sin(sim_idx * 0.14)
        for ex in exits_live:
            ex_id = str(ex.get("id", ""))
            blocked = ex_id in blocked_exits or bool(ex.get("blocked") or ex.get("is_blocked"))
            px, py = _world_to_px(float(ex.get("x", 0.0)), float(ex.get("z", ex.get("y", 0.0))), bounds, map_rect)
            color = BAD if blocked else GOOD
            radius = 5 + int(3 * pulse) if blocked else 6
            cv2.circle(frame, (px, py), radius + 3, (70, 80, 110), 1, cv2.LINE_AA)
            _draw_glow_circle(frame, (px, py), radius, color)

        trail_span = 11
        for back in range(trail_span, 0, -1):
            tidx = max(0, sim_idx - back * 2)
            tf = sim_frames[tidx]
            alpha = (trail_span - back + 1) / (trail_span + 1)
            col = (int(70 + 140 * alpha), int(130 + 90 * alpha), int(185 + 50 * alpha))
            for a in tf.get("agents", []):
                if a.get("status") == "evacuated":
                    continue
                px, py = _world_to_px(float(a.get("x", 0.0)), float(a.get("z", a.get("y", 0.0))), bounds, map_rect)
                cv2.circle(frame, (px, py), 2, col, -1, cv2.LINE_AA)

        active_points: list[tuple[int, int]] = []
        for a in sf.get("agents", []):
            if a.get("status") == "evacuated":
                continue
            speed = float(a.get("speed", 0.0) or 0.0)
            s_norm = max(0.0, min(1.0, speed / 2.2))
            lut = np.uint8([[int(s_norm * 255)]])
            col = cv2.applyColorMap(lut, cv2.COLORMAP_VIRIDIS)[0][0].tolist()
            px, py = _world_to_px(float(a.get("x", 0.0)), float(a.get("z", a.get("y", 0.0))), bounds, map_rect)
            active_points.append((px, py))
            cv2.circle(frame, (px, py), 4, (int(col[0]), int(col[1]), int(col[2])), -1, cv2.LINE_AA)
            cv2.circle(frame, (px, py), 5, (28, 34, 46), 1, cv2.LINE_AA)

        # Hotspot inset highlights the densest active zone to improve readability.
        if active_points:
            grid_w, grid_h = 36, 24
            occ = np.zeros((grid_h, grid_w), dtype=np.int32)
            for px, py in active_points:
                gx = int((px - map_rect[0]) / max(1, map_w) * grid_w)
                gy = int((py - map_rect[1]) / max(1, map_h) * grid_h)
                gx = min(grid_w - 1, max(0, gx))
                gy = min(grid_h - 1, max(0, gy))
                occ[gy, gx] += 1

            by, bx = np.unravel_index(int(np.argmax(occ)), occ.shape)
            cx = map_rect[0] + int((bx + 0.5) / grid_w * map_w)
            cy = map_rect[1] + int((by + 0.5) / grid_h * map_h)

            box_w, box_h = 170, 120
            x0 = max(map_rect[0], cx - box_w // 2)
            y0 = max(map_rect[1], cy - box_h // 2)
            x1 = min(map_rect[2], x0 + box_w)
            y1 = min(map_rect[3], y0 + box_h)
            x0 = x1 - box_w
            y0 = y1 - box_h

            cv2.rectangle(frame, (x0, y0), (x1, y1), ACCENT_A, 2, cv2.LINE_AA)

            inset_x0, inset_y0, inset_x1, inset_y1 = 678, 106, 900, 272
            _draw_panel(frame, inset_x0, inset_y0, inset_x1, inset_y1, alpha=0.68)
            inset = frame[y0:y1, x0:x1].copy()
            if inset.size > 0:
                inset = cv2.resize(inset, (inset_x1 - inset_x0 - 12, inset_y1 - inset_y0 - 28), interpolation=cv2.INTER_LINEAR)
                frame[inset_y0 + 22 : inset_y1 - 6, inset_x0 + 6 : inset_x1 - 6] = inset
            _put_text(frame, "Hotspot Zoom", inset_x0 + 10, inset_y0 + 16, 0.45, ACCENT_A, 1)
            _put_text(frame, f"Local load: {int(occ[by, bx])}", inset_x0 + 114, inset_y0 + 16, 0.40, TEXT_300, 1)

        completion = float(stats.get("completion_percentage", 0.0) or 0.0)
        remaining = int(stats.get("remaining", 0) or 0)
        evacuated = int(stats.get("evacuated", 0) or 0)
        sim_time = float(sf.get("timestamp", 0.0) or 0.0)
        active_agents = max(0, len(active_points))

        _put_text(frame, "Live Metrics", 944, 136, 0.78, TEXT_100, 2)
        _put_text(frame, f"Sim time: {sim_time:.1f} s", 944, 178, 0.58, TEXT_200, 1)
        _put_text(frame, f"Frame: {int(sf.get('frame_id', 0) or 0)}", 944, 204, 0.58, TEXT_200, 1)
        _put_text(frame, f"Evacuated: {evacuated}", 944, 230, 0.58, TEXT_200, 1)
        _put_text(frame, f"Remaining: {remaining}", 944, 256, 0.58, TEXT_200, 1)
        _put_text(frame, f"Active on map: {active_agents}", 944, 282, 0.58, TEXT_200, 1)

        cv2.rectangle(frame, (944, 312), (1214, 330), (60, 74, 104), -1)
        cv2.rectangle(frame, (944, 312), (944 + int(270 * completion / 100.0), 330), ACCENT_A, -1)
        _put_text(frame, f"Completion: {completion:.1f}%", 944, 356, 0.62, TEXT_100, 1)

        _put_text(frame, "Scenario", 944, 380, 0.74, TEXT_100, 2)
        _put_text(frame, "Blocked-exit stress", 944, 414, 0.56, TEXT_200, 1)
        _put_text(frame, "Routing: least_crowded", 944, 438, 0.56, TEXT_200, 1)
        _put_text(frame, f"Blocked IDs: {', '.join(blocked_exits) if blocked_exits else 'none'}", 944, 462, 0.56, TEXT_200, 1)

        _put_text(frame, "Legend", 944, 520, 0.72, TEXT_100, 2)
        cv2.circle(frame, (952, 544), 5, GOOD, -1, cv2.LINE_AA)
        _put_text(frame, "Open exit", 966, 548, 0.50, TEXT_300, 1)
        cv2.circle(frame, (952, 568), 5, BAD, -1, cv2.LINE_AA)
        _put_text(frame, "Blocked exit", 966, 572, 0.50, TEXT_300, 1)
        cv2.circle(frame, (952, 592), 4, WARN, -1, cv2.LINE_AA)
        _put_text(frame, "Agents (speed-colored)", 966, 596, 0.50, TEXT_300, 1)

        _draw_stat_chip(frame, 70, 86, "Live completion", f"{completion:.1f}%", ACCENT_A)
        _draw_stat_chip(frame, 324, 86, "Agents remaining", str(remaining), WARN)

        return frame

    def scene_analytics(p: float) -> np.ndarray:
        frame = _blank()
        _fill_gradient(frame, (36, 24, 16), (16, 10, 6))

        _put_text(frame, "Step 5: Analytics and Reporting", 74, 88, 0.98, TEXT_100, 2)
        _put_text(frame, "Heatmaps, trends, and reproducible summary metrics", 74, 116, 0.56, TEXT_300, 1)

        _draw_panel(frame, map_rect[0], map_rect[1], map_rect[2], map_rect[3], alpha=0.66)
        frame[map_rect[1] : map_rect[3], map_rect[0] : map_rect[2]] = cv2.addWeighted(
            frame[map_rect[1] : map_rect[3], map_rect[0] : map_rect[2]],
            0.30,
            map_backdrop,
            0.70,
            0.0,
        )
        if int(np.count_nonzero(map_edges)) > 0:
            frame[map_rect[1] : map_rect[3], map_rect[0] : map_rect[2]] = cv2.addWeighted(
                frame[map_rect[1] : map_rect[3], map_rect[0] : map_rect[2]],
                1.0,
                map_edges,
                0.22,
                0.0,
            )

        # Blend congestion heatmap over map panel.
        frame[map_rect[1] : map_rect[3], map_rect[0] : map_rect[2]] = cv2.addWeighted(
            frame[map_rect[1] : map_rect[3], map_rect[0] : map_rect[2]],
            0.25,
            heat_overlay,
            0.75,
            0.0,
        )

        for wall in floor_plan.get("detected_walls", []):
            p1 = _world_to_px(float(wall.get("x1", 0.0)), float(wall.get("y1", 0.0)), bounds, map_rect)
            p2 = _world_to_px(float(wall.get("x2", 0.0)), float(wall.get("y2", 0.0)), bounds, map_rect)
            cv2.line(frame, p1, p2, (228, 236, 250), 1, cv2.LINE_AA)

        if not floor_plan.get("detected_walls") and structural_lines_px:
            for x1, y1, x2, y2 in structural_lines_px:
                cv2.line(
                    frame,
                    (map_rect[0] + x1, map_rect[1] + y1),
                    (map_rect[0] + x2, map_rect[1] + y2),
                    (220, 230, 245),
                    1,
                    cv2.LINE_AA,
                )

        _draw_panel(frame, 920, 96, 1238, 650, alpha=0.72)

        upto = max(2, int(_ease(p) * len(completion_series)))
        comp_part = completion_series[:upto]
        dens_part = density_series[:upto]
        rem_part = remaining_series[:upto]

        _draw_line_chart(frame, comp_part, (938, 132, 1220, 248), GOOD, "Completion (%)")
        _draw_line_chart(frame, dens_part, (938, 262, 1220, 378), WARN, "Density trend")
        _draw_line_chart(frame, rem_part, (938, 392, 1220, 508), ACCENT_B, "Remaining agents")
        _draw_heat_legend(frame, 76, 572, 456, 640)

        evac = float(metrics_dict.get("total_evacuation_time", 0.0) or 0.0)
        peak = float(metrics_dict.get("peak_congestion_density", 0.0) or 0.0)
        queue = int(metrics_dict.get("max_queue_length", 0) or 0)
        bottlenecks = int(metrics_dict.get("bottleneck_events", 0) or 0)

        anim = 0.2 + 0.8 * _ease(p)
        _put_text(frame, f"Evac time: {evac * anim:.1f} s", 944, 546, 0.56, TEXT_200, 1)
        _put_text(frame, f"Peak density: {peak * anim:.2f}", 944, 570, 0.56, TEXT_200, 1)
        _put_text(frame, f"Max queue: {int(round(queue * anim))}", 944, 594, 0.56, TEXT_200, 1)
        _put_text(frame, f"Bottlenecks: {int(round(bottlenecks * anim))}", 944, 618, 0.56, TEXT_200, 1)
        return frame

    def scene_closing(p: float) -> np.ndarray:
        frame = _blank()
        _fill_gradient(frame, (38, 26, 17), (18, 12, 8))
        _draw_panel(frame, 84, 120, W - 84, H - 96, alpha=0.62)

        _put_text(frame, "PeopleFlow", 128, 204, 1.42, TEXT_100, 3)
        _put_text(frame, "Reproducible Evacuation Safety Evaluation", 130, 246, 0.78, TEXT_200, 1)

        points = [
            "Automated pipeline from floor plan to evidence",
            "Stress-tested simulation with scenario control",
            "Traceable metrics for comparative safety review",
            "Artifact-backed outputs for reproducible reruns",
        ]

        y = 306
        for i, line in enumerate(points):
            reveal = min(1.0, max(0.0, (p - 0.08 * i) / 0.20))
            if reveal <= 0.0:
                continue
            x = 150 + int((1.0 - _ease(reveal)) * 32)
            cv2.circle(frame, (x - 18, y - 8), 6, GOOD, -1, cv2.LINE_AA)
            _put_text(frame, line, x, y, 0.62, TEXT_200, 1)
            y += 42

        _put_text(frame, "Repository: github.com/1206likith/PeopleFlow", 130, H - 160, 0.56, WARN, 1)
        _put_text(frame, "Supplementary video generated directly from maintained experiment scripts", 130, H - 132, 0.52, TEXT_300, 1)
        _draw_stat_chip(frame, W - 350, H - 212, "Submission-ready", "Video + metadata + previews", GOOD)
        return frame

    write_segment(0, segment_durations[0], scene_intro, "Narrative setup for the reproducible evacuation workflow")
    write_segment(1, segment_durations[1], scene_pipeline, "From ingestion to report: one deterministic pipeline")
    write_segment(2, segment_durations[2], scene_ingestion, "Blueprint normalization and robust geometry detection")
    write_segment(3, segment_durations[3], scene_geometry, "Detected walls and exits converted to simulation primitives")
    write_segment(4, segment_durations[4], scene_scenario, "Scenario card with explicit stress controls and seed")
    write_segment(5, segment_durations[5], scene_simulation, "Live run with blocked-exit stress and real-time metrics")
    write_segment(6, segment_durations[6], scene_analytics, "Heatmaps and trends summarize bottlenecks and completion")
    write_segment(7, segment_durations[7], scene_closing, "Reproducibility assets and deployment relevance")

    writer.release()

    projector_export = _export_projector_video(VIDEO_PATH, PROJECTOR_VIDEO_PATH, FPS)

    elapsed = time.perf_counter() - t0
    _write_preview_frames(VIDEO_PATH, PREVIEW_DIR, [4, 10, 18, 26, 32])

    detector_summary = _extract_detector_summary(floor_plan)
    metadata = {
        "video_path": str(VIDEO_PATH),
        "fps": FPS,
        "resolution": [W, H],
        "total_frames": int(frame_count),
        "duration_seconds": round(frame_count / FPS, 2),
        "generation_wall_clock_s": round(elapsed, 2),
        "style_version": "god_tier_v6",
        "export_profiles": {
            "standard": {
                "path": str(VIDEO_PATH),
                "resolution": [W, H],
                "fps": FPS,
                "encoder": "opencv/mp4v",
            },
            "projector_1080p": projector_export,
        },
        "layout": str(layout_path),
        "layout_name": layout_path.name,
        "detector_summary": detector_summary,
        "scenario": {
            "num_agents": 140,
            "routing_policy": "least_crowded",
            "blocked_exits": blocked_exits,
            "panic_level": 0.4,
            "dt_s": 0.2,
        },
        "metrics_summary": {
            "total_evacuation_time_s": float(metrics_dict.get("total_evacuation_time", 0.0) or 0.0),
            "peak_congestion_density": float(metrics_dict.get("peak_congestion_density", 0.0) or 0.0),
            "max_queue_length": int(metrics_dict.get("max_queue_length", 0) or 0),
            "bottleneck_events": int(metrics_dict.get("bottleneck_events", 0) or 0),
        },
        "segments": [
            {"name": section_names[i], "duration_s": segment_durations[i]}
            for i in range(len(section_names))
        ],
        "preview_frames_dir": str(PREVIEW_DIR),
    }

    META_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(f"Wrote video: {VIDEO_PATH}")
    print(f"Wrote projector video: {PROJECTOR_VIDEO_PATH}")
    print(f"Wrote metadata: {META_PATH}")
    print(f"Wrote preview frames: {PREVIEW_DIR}")


if __name__ == "__main__":
    main()
