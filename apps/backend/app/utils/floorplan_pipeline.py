"""
Floor plan debug pipeline.
Run this to visualize each processing step for a blueprint image.
"""
import argparse
import json
from pathlib import Path
import sys

from app.services.floor_plan_processor import floor_plan_processor


def _print_summary(result: dict) -> None:
    summary = {
        "processed": result.get("processed", False),
        "walls": result.get("wall_count", 0),
        "exits": result.get("exit_count", 0),
        "obstacles": result.get("obstacle_count", 0),
        "rooms": result.get("room_count", 0),
        "building_bounds": result.get("building_bounds", {}),
        "pipeline_steps": result.get("pipeline_steps", []),
    }
    print(json.dumps(summary, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run floor plan processing with debug outputs."
    )
    parser.add_argument("image", help="Path to blueprint image")
    parser.add_argument("--out-dir", help="Base output directory for debug artifacts")
    parser.add_argument(
        "--no-semantic",
        action="store_true",
        help="Skip semantic/ML processing and use traditional OpenCV pipeline",
    )
    parser.add_argument(
        "--save-json",
        action="store_true",
        help="Save full result JSON next to debug artifacts",
    )

    args = parser.parse_args()

    result = floor_plan_processor.process_floor_plan(
        args.image,
        use_semantic=not args.no_semantic,
        debug=True,
        debug_dir=args.out_dir,
    )

    _print_summary(result)

    debug_info = result.get("debug", {})
    debug_dir = debug_info.get("dir")
    if debug_dir:
        print(f"Debug artifacts: {debug_dir}")

    if args.save_json:
        out_path = None
        if debug_dir:
            out_path = Path(debug_dir) / "result.json"
        else:
            out_path = Path("artifacts") / "floorplan_debug" / "result.json"
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)
            print(f"Saved result JSON: {out_path}")
        except Exception as e:
            print(f"Failed to write result JSON: {e}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
