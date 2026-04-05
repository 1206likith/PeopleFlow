"""Measure automated floor-plan ingestion times for workflow-effort reporting."""

from __future__ import annotations

import csv
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.services.floorplan_service import process_floor_plan_image  # type: ignore

ROOT_DIR = Path(__file__).resolve().parents[4]
OUT_DIR = ROOT_DIR / "Research_Paper_IEEE"

LAYOUTS = [
    ("Academic_Plan", ROOT_DIR / "Research_Paper_IEEE" / "Floor_Plans" / "Academic_Plan.jpg"),
    ("Hospital_Plan", ROOT_DIR / "Research_Paper_IEEE" / "Floor_Plans" / "Hospital_Plan.jpg"),
    ("Mall_Plan", ROOT_DIR / "Research_Paper_IEEE" / "Floor_Plans" / "Mall_Plan.jpg"),
    ("Airport_Terminal", ROOT_DIR / "apps" / "backend" / "app" / "experiments" / "input_floorplans" / "ieee_journal_blueprints" / "G_airport_bergen.jpg"),
    ("Metro_Station", ROOT_DIR / "apps" / "backend" / "app" / "experiments" / "input_floorplans" / "ieee_journal_blueprints" / "H_metro_taipei.jpg"),
]


def _mime(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".png":
        return "image/png"
    if ext == ".webp":
        return "image/webp"
    return "image/jpeg"


def main() -> None:
    rows = []

    for name, path in LAYOUTS:
        if not path.exists():
            continue
        result = process_floor_plan_image(_mime(path), str(path), {"mode": "traditional"})
        rows.append(
            {
                "layout": name,
                "processing_time_ms": float(result.get("processing_time_ms") or 0.0),
                "wall_count": int(result.get("wall_count") or len(result.get("walls", []) or [])),
                "exit_count": int(result.get("exit_count") or len(result.get("exits", []) or [])),
                "processed": bool(result.get("processed")),
            }
        )

    if not rows:
        raise RuntimeError("No ingestion timing rows produced")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUT_DIR / "ingestion_timing.csv"
    summary_path = OUT_DIR / "ingestion_timing_summary.json"

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    ms_values = [r["processing_time_ms"] for r in rows]
    summary = {
        "count": len(rows),
        "processing_time_mean_ms": round(statistics.mean(ms_values), 2),
        "processing_time_std_ms": round(statistics.pstdev(ms_values), 2),
        "processing_time_min_ms": round(min(ms_values), 2),
        "processing_time_max_ms": round(max(ms_values), 2),
    }
    summary_path.write_text(__import__("json").dumps(summary, indent=2), encoding="utf-8")

    print(f"Wrote: {csv_path}")
    print(f"Wrote: {summary_path}")


if __name__ == "__main__":
    main()
