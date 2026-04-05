"""ETH/UCY trajectory validation utilities.

This module evaluates short-horizon trajectory prediction quality using RMSE on
ETH-style trajectory files (e.g., ``obsmat.txt``) and provides a reproducible
report format for paper artifacts.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import tarfile
from typing import Any, Dict, Iterable, List, Tuple
from urllib.request import urlretrieve

import numpy as np

from .targets import load_targets


DEFAULT_ETH_DATASET_URL = "https://data.vision.ee.ethz.ch/cvl/aem/ewap_dataset_full.tgz"
DEFAULT_SUCCESS_FDE_THRESHOLD_M = 1.5
DEFAULT_MIN_STEP_M = 0.05
DEFAULT_OVERLAP_DISTANCE_M = 0.6


@dataclass
class TrajectorySample:
    frame: int
    ped_id: int
    x: float
    y: float


def _default_dataset_root() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "eth_ucy"


def _trajectory_files(dataset_root: Path) -> List[Path]:
    if not dataset_root.exists():
        return []
    files = sorted(dataset_root.rglob("obsmat.txt"))
    if files:
        return files

    # Fallback for alternate ETH/UCY mirrors containing plain trajectory txt/csv files.
    fallback: List[Path] = []
    for ext in ("*.txt", "*.csv"):
        fallback.extend(sorted(dataset_root.rglob(ext)))
    return [f for f in fallback if f.is_file() and f.stat().st_size > 0]


def _maybe_download_eth_dataset(dataset_root: Path, dataset_url: str) -> Dict[str, Any]:
    dataset_root.mkdir(parents=True, exist_ok=True)
    archive_path = dataset_root / "ewap_dataset_full.tgz"
    extract_root = dataset_root / "raw"

    metadata: Dict[str, Any] = {
        "dataset_url": dataset_url,
        "downloaded": False,
        "extracted": False,
        "archive_path": str(archive_path),
        "extract_root": str(extract_root),
    }

    if not archive_path.exists():
        urlretrieve(dataset_url, archive_path)
        metadata["downloaded"] = True

    if not extract_root.exists() or not any(extract_root.iterdir()):
        extract_root.mkdir(parents=True, exist_ok=True)
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(extract_root)
        metadata["extracted"] = True

    return metadata


def _coerce_matrix(path: Path) -> np.ndarray:
    # Handles both whitespace and comma separated trajectory files.
    try:
        matrix = np.loadtxt(path, dtype=float)
    except Exception:
        matrix = np.loadtxt(path, dtype=float, delimiter=",")
    if matrix.ndim == 1:
        matrix = np.expand_dims(matrix, axis=0)
    return matrix


def _to_samples(path: Path) -> List[TrajectorySample]:
    matrix = _coerce_matrix(path)
    if matrix.shape[1] < 4:
        return []

    frame = matrix[:, 0].astype(int)
    ped = matrix[:, 1].astype(int)
    x = matrix[:, 2].astype(float)

    # ETH obsmat files frequently include a near-constant vertical axis. Use the
    # most informative horizontal axis among candidate columns.
    if matrix.shape[1] >= 5:
        c3 = matrix[:, 3].astype(float)
        c4 = matrix[:, 4].astype(float)
        y = c4 if np.std(c4) > (np.std(c3) + 1e-9) else c3
    else:
        y = matrix[:, 3].astype(float)

    samples = [
        TrajectorySample(frame=int(f), ped_id=int(p), x=float(px), y=float(py))
        for f, p, px, py in zip(frame, ped, x, y)
    ]
    samples.sort(key=lambda s: (s.frame, s.ped_id))
    return samples


def _predict_triplet(
    prev_xy: np.ndarray,
    curr_xy: np.ndarray,
    neighbor_positions: Iterable[np.ndarray],
    dt_prev: float,
    dt_next: float,
    *,
    interaction_radius: float,
    repulsion_gain: float,
) -> np.ndarray:
    velocity = (curr_xy - prev_xy) / max(dt_prev, 1e-6)
    repulsion = np.zeros(2, dtype=float)
    for npos in neighbor_positions:
        delta = curr_xy - npos
        dist = float(np.linalg.norm(delta))
        if dist < 1e-6 or dist >= interaction_radius:
            continue
        strength = repulsion_gain * ((interaction_radius - dist) / interaction_radius)
        repulsion += (delta / dist) * strength
    return curr_xy + velocity * dt_next + repulsion * dt_next


def _evaluate_scene(
    scene_path: Path,
    *,
    interaction_radius: float,
    repulsion_gain: float,
) -> Dict[str, Any]:
    samples = _to_samples(scene_path)
    if not samples:
        return {
            "scene": str(scene_path),
            "status": "insufficient_data",
            "samples": 0,
        }

    by_frame: Dict[int, Dict[int, np.ndarray]] = {}
    by_ped: Dict[int, List[TrajectorySample]] = {}
    for s in samples:
        by_frame.setdefault(s.frame, {})[s.ped_id] = np.array([s.x, s.y], dtype=float)
        by_ped.setdefault(s.ped_id, []).append(s)

    errors: List[float] = []
    speed_errors: List[float] = []
    final_errors: List[float] = []
    heading_angles_deg: List[float] = []
    smoothness_scores: List[float] = []
    successful_trajectories = 0
    eligible_trajectories = 0

    overlap_events = 0
    overlap_total = 0
    for frame_positions in by_frame.values():
        if len(frame_positions) < 2:
            continue
        positions = np.stack(list(frame_positions.values()), axis=0)
        # Pairwise nearest-neighbor check used as a clipping proxy.
        deltas = positions[:, None, :] - positions[None, :, :]
        dist_sq = np.sum(deltas * deltas, axis=2)
        np.fill_diagonal(dist_sq, np.inf)
        min_dist = np.sqrt(np.min(dist_sq, axis=1))
        overlap_events += int(np.sum(min_dist < DEFAULT_OVERLAP_DISTANCE_M))
        overlap_total += int(positions.shape[0])

    for ped_id, traj in by_ped.items():
        if len(traj) < 3:
            continue
        eligible_trajectories += 1
        traj.sort(key=lambda s: s.frame)
        last_err = None
        pred_displacements: List[np.ndarray] = []
        pred_step_norms: List[float] = []
        for i in range(1, len(traj) - 1):
            prev_s = traj[i - 1]
            curr_s = traj[i]
            next_s = traj[i + 1]

            dt_prev = float(max(curr_s.frame - prev_s.frame, 1))
            dt_next = float(max(next_s.frame - curr_s.frame, 1))
            prev_xy = np.array([prev_s.x, prev_s.y], dtype=float)
            curr_xy = np.array([curr_s.x, curr_s.y], dtype=float)
            true_next = np.array([next_s.x, next_s.y], dtype=float)

            neighbors = [
                pos
                for other_id, pos in by_frame.get(curr_s.frame, {}).items()
                if other_id != ped_id
            ]
            pred_next = _predict_triplet(
                prev_xy,
                curr_xy,
                neighbors,
                dt_prev,
                dt_next,
                interaction_radius=interaction_radius,
                repulsion_gain=repulsion_gain,
            )
            err = float(np.linalg.norm(pred_next - true_next))
            errors.append(err)
            last_err = err
            pred_disp = pred_next - curr_xy
            pred_displacements.append(pred_disp)
            pred_step_norms.append(float(np.linalg.norm(pred_disp)))

            true_speed = float(np.linalg.norm((true_next - curr_xy) / dt_next))
            pred_speed = float(np.linalg.norm((pred_next - curr_xy) / dt_next))
            speed_errors.append(abs(pred_speed - true_speed))

        for j in range(1, len(pred_displacements)):
            v1 = pred_displacements[j - 1]
            v2 = pred_displacements[j]
            n1 = float(np.linalg.norm(v1))
            n2 = float(np.linalg.norm(v2))
            if n1 < 1e-9 or n2 < 1e-9:
                continue
            cosang = float(np.clip(np.dot(v1, v2) / (n1 * n2), -1.0, 1.0))
            angle = float(np.arccos(cosang))
            heading_angles_deg.append(float(np.degrees(angle)))
            smoothness_scores.append(float(max(0.0, 1.0 - (angle / np.pi))))

        if (
            last_err is not None
            and pred_step_norms
            and last_err <= DEFAULT_SUCCESS_FDE_THRESHOLD_M
            and float(np.mean(pred_step_norms)) >= DEFAULT_MIN_STEP_M
        ):
            successful_trajectories += 1

        if last_err is not None:
            final_errors.append(last_err)

    if not errors:
        return {
            "scene": str(scene_path),
            "status": "insufficient_data",
            "samples": 0,
        }

    rmse = float(np.sqrt(np.mean(np.square(errors))))
    ade = float(np.mean(errors))
    fde = float(np.mean(final_errors)) if final_errors else None

    return {
        "scene": str(scene_path),
        "status": "ok",
        "samples": len(errors),
        "rmse": rmse,
        "ade": ade,
        "fde": fde,
        "speed_mae": float(np.mean(speed_errors)) if speed_errors else None,
        "oscillation_strength_deg": float(np.mean(heading_angles_deg)) if heading_angles_deg else None,
        "path_smoothness": float(np.mean(smoothness_scores)) if smoothness_scores else None,
        "successful_trajectories": int(successful_trajectories),
        "eligible_trajectories": int(eligible_trajectories),
        "successful_trajectory_ratio": (
            float(successful_trajectories / max(eligible_trajectories, 1)) if eligible_trajectories else None
        ),
        "overlap_events": int(overlap_events),
        "overlap_total": int(overlap_total),
        "overlap_proportion": float(overlap_events / max(overlap_total, 1)) if overlap_total else None,
        "num_pedestrians": len(by_ped),
        "num_frames": len(by_frame),
    }


def validate_eth_trajectory(
    dataset_root: str | None = None,
    *,
    download_if_missing: bool = False,
    dataset_url: str = DEFAULT_ETH_DATASET_URL,
) -> Dict[str, Any]:
    targets = load_targets().get("eth_trajectory", {})
    rmse_tol = float(targets.get("rmse_tolerance", 1.0) or 1.0)
    success_ratio_min = float(targets.get("success_ratio_min", 0.80) or 0.80)
    overlap_proportion_max = float(targets.get("overlap_proportion_max", 0.05) or 0.05)
    interaction_radius = float(targets.get("interaction_radius", 2.5) or 2.5)
    repulsion_gain = float(targets.get("repulsion_gain", 0.12) or 0.12)
    min_scenes = int(targets.get("min_scenes", 2) or 2)

    root = Path(dataset_root) if dataset_root else _default_dataset_root()
    download_meta: Dict[str, Any] = {
        "dataset_url": dataset_url,
        "downloaded": False,
        "extracted": False,
    }

    files = _trajectory_files(root)
    if not files and download_if_missing:
        try:
            download_meta = _maybe_download_eth_dataset(root, dataset_url)
            files = _trajectory_files(root)
        except Exception as exc:
            return {
                "status": "dataset_unavailable",
                "score": None,
                "error": str(exc),
                "dataset_root": str(root),
                "download": download_meta,
            }

    if not files:
        return {
            "status": "dataset_missing",
            "score": None,
            "dataset_root": str(root),
            "download": download_meta,
            "message": "No ETH/UCY trajectory files found. Expected obsmat.txt or equivalent trajectory txt/csv files.",
        }

    scene_results = [
        _evaluate_scene(
            scene,
            interaction_radius=interaction_radius,
            repulsion_gain=repulsion_gain,
        )
        for scene in files
    ]
    scene_ok = [scene for scene in scene_results if scene.get("status") == "ok"]
    if len(scene_ok) < min_scenes:
        return {
            "status": "insufficient_data",
            "score": None,
            "dataset_root": str(root),
            "download": download_meta,
            "scenes_evaluated": len(scene_ok),
            "scene_results": scene_results,
        }

    rmse_values = [float(scene["rmse"]) for scene in scene_ok if scene.get("rmse") is not None]
    ade_values = [float(scene["ade"]) for scene in scene_ok if scene.get("ade") is not None]
    fde_values = [float(scene["fde"]) for scene in scene_ok if scene.get("fde") is not None]
    oscillation_values = [
        float(scene["oscillation_strength_deg"])
        for scene in scene_ok
        if scene.get("oscillation_strength_deg") is not None
    ]
    smoothness_values = [float(scene["path_smoothness"]) for scene in scene_ok if scene.get("path_smoothness") is not None]
    successful_total = int(sum(int(scene.get("successful_trajectories", 0)) for scene in scene_ok))
    eligible_total = int(sum(int(scene.get("eligible_trajectories", 0)) for scene in scene_ok))
    overlap_events_total = int(sum(int(scene.get("overlap_events", 0)) for scene in scene_ok))
    overlap_total = int(sum(int(scene.get("overlap_total", 0)) for scene in scene_ok))
    total_samples = int(sum(int(scene.get("samples", 0)) for scene in scene_ok))

    rmse = float(np.mean(rmse_values)) if rmse_values else float("inf")
    ade = float(np.mean(ade_values)) if ade_values else None
    fde = float(np.mean(fde_values)) if fde_values else None
    oscillation_strength_deg = float(np.mean(oscillation_values)) if oscillation_values else None
    path_smoothness = float(np.mean(smoothness_values)) if smoothness_values else None
    successful_trajectory_ratio = float(successful_total / max(eligible_total, 1)) if eligible_total else None
    overlap_proportion = float(overlap_events_total / max(overlap_total, 1)) if overlap_total else None
    score = max(0.0, 1.0 - (rmse / max(rmse_tol, 1e-6))) if np.isfinite(rmse) else 0.0
    passes_rmse = rmse <= rmse_tol
    passes_success = successful_trajectory_ratio is None or successful_trajectory_ratio >= success_ratio_min
    passes_overlap = overlap_proportion is None or overlap_proportion <= overlap_proportion_max
    status = "ok" if (passes_rmse and passes_success and passes_overlap) else "poor_fit"

    return {
        "status": status,
        "score": score,
        "dataset_root": str(root),
        "download": download_meta,
        "scenes_evaluated": len(scene_ok),
        "scene_files": len(files),
        "samples": total_samples,
        "rmse": rmse,
        "ade": ade,
        "fde": fde,
        "oscillation_strength_deg": oscillation_strength_deg,
        "path_smoothness": path_smoothness,
        "successful_trajectories": successful_total,
        "eligible_trajectories": eligible_total,
        "successful_trajectory_ratio": successful_trajectory_ratio,
        "overlap_events": overlap_events_total,
        "overlap_total": overlap_total,
        "overlap_proportion": overlap_proportion,
        "target_rmse_tolerance": rmse_tol,
        "target_success_ratio_min": success_ratio_min,
        "target_overlap_proportion_max": overlap_proportion_max,
        "interaction_radius": interaction_radius,
        "repulsion_gain": repulsion_gain,
        "scene_results": scene_results,
    }


def write_eth_validation_artifacts(report: Dict[str, Any], output_json: Path, output_csv: Path) -> None:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, indent=2), encoding="utf-8")

    scene_rows = report.get("scene_results", []) if isinstance(report, dict) else []
    columns = [
        "scene",
        "status",
        "samples",
        "rmse",
        "ade",
        "fde",
        "speed_mae",
        "oscillation_strength_deg",
        "path_smoothness",
        "successful_trajectories",
        "eligible_trajectories",
        "successful_trajectory_ratio",
        "overlap_events",
        "overlap_total",
        "overlap_proportion",
        "num_pedestrians",
        "num_frames",
    ]
    with output_csv.open("w", encoding="utf-8", newline="") as handle:
        handle.write(",".join(columns) + "\n")
        for row in scene_rows:
            values = [str(row.get(col, "")) for col in columns]
            handle.write(",".join(values) + "\n")
