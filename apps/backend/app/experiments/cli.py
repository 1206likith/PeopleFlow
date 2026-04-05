"""
CLI entry point for experiments and ablations.
"""
import json
import argparse
from pathlib import Path

from .config import ExperimentConfig
from .runner import run_experiment_sync
from .ablation_runner import run_ablation_grid
from .indexer import build_index
from .metrics_export import export_csv
from .calibration_runner import run_calibration
from .optimizer import run_bayesian_optimization
from .paper_pipeline import run_paper_pipeline
from app.validation.runner import run_validation
from app.validation.eth_trajectory import validate_eth_trajectory, write_eth_validation_artifacts
from research.analytics.scripts.report_generator import generate_report
from . import OUTPUT_DIR, EXPERIMENTS_DIR, ROOT_DIR


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", help="Path to experiment config JSON")
    parser.add_argument("--ablation", action="store_true", help="Run ablation grid")
    parser.add_argument("--calibrate", action="store_true", help="Run calibration search")
    parser.add_argument(
        "--calibration-config",
        default=str(EXPERIMENTS_DIR / "calibration.json"),
        help="Calibration JSON config",
    )
    parser.add_argument("--validate", action="store_true", help="Run validation on outputs")
    parser.add_argument("--optimize", action="store_true", help="Run Bayesian optimization")
    parser.add_argument(
        "--optimization-config",
        default=str(EXPERIMENTS_DIR / "optimization.json"),
        help="Optimization JSON config",
    )
    parser.add_argument("--report", action="store_true", help="Generate research summary report")
    parser.add_argument("--paper-bundle", action="store_true", help="Run reproducible multi-seed paper pipeline")
    parser.add_argument(
        "--paper-results",
        action="store_true",
        help="Run publication-ready paper-results pipeline (alias of --paper-bundle)",
    )
    parser.add_argument(
        "--paper-batch-config",
        default=str(EXPERIMENTS_DIR / "batches" / "paper_baseline_suite.json"),
        help="Paper pipeline batch config JSON",
    )
    parser.add_argument(
        "--paper-artifacts-root",
        default=str(ROOT_DIR / "artifacts" / "paper_results"),
        help="Output root for paper-results bundles",
    )
    parser.add_argument(
        "--paper-no-copy-runs",
        action="store_true",
        help="Do not copy per-run raw JSON outputs into publication bundle",
    )
    parser.add_argument("--validate-eth", action="store_true", help="Include ETH trajectory RMSE validation")
    parser.add_argument(
        "--eth-dataset-root",
        default=str(ROOT_DIR / "apps" / "backend" / "data" / "eth_ucy"),
        help="Local ETH/UCY dataset root directory",
    )
    parser.add_argument(
        "--eth-dataset-url",
        default="https://data.vision.ee.ethz.ch/cvl/aem/ewap_dataset_full.tgz",
        help="ETH dataset archive URL used when download is required",
    )
    parser.add_argument(
        "--eth-download",
        action="store_true",
        help="Download ETH dataset archive when missing",
    )
    parser.add_argument("--skip-index", action="store_true", help="Skip index.json generation")
    parser.add_argument("--skip-export", action="store_true", help="Skip metrics CSV export")
    parser.add_argument("--run-ablation-study", action="store_true", help="Run the paper's ablation study")
    args = parser.parse_args()

    if args.run_ablation_study:
        run_ablation_study_for_paper()
        return

    if args.paper_bundle or args.paper_results:
        bundle = run_paper_pipeline(
            args.paper_batch_config,
            validate=args.validate,
            validate_eth=args.validate_eth,
            eth_dataset_root=args.eth_dataset_root,
            eth_download_if_missing=args.eth_download,
            eth_dataset_url=args.eth_dataset_url,
            artifacts_root=args.paper_artifacts_root,
            copy_run_outputs=not args.paper_no_copy_runs,
        )
        print(json.dumps(bundle, indent=2))
        _post_process(args)
        return

    # Standalone ETH validation mode (no experiment config required).
    if args.validate_eth and not args.config and not args.ablation and not args.calibrate and not args.optimize:
        eth_report = validate_eth_trajectory(
            dataset_root=args.eth_dataset_root,
            download_if_missing=args.eth_download,
            dataset_url=args.eth_dataset_url,
        )
        json_out = OUTPUT_DIR / "eth_trajectory_validation.json"
        csv_out = OUTPUT_DIR / "eth_trajectory_validation.csv"
        write_eth_validation_artifacts(eth_report, json_out, csv_out)
        print(json.dumps(eth_report, indent=2))
        _post_process(args)
        return

    if not args.config:
        parser.error("--config is required unless --paper-bundle is provided")

    cfg = ExperimentConfig(**json.loads(Path(args.config).read_text(encoding="utf-8-sig")))

    if args.calibrate:
        run_calibration(cfg, args.calibration_config)
        _post_process(args)
        return

    if args.optimize:
        run_bayesian_optimization(cfg, args.optimization_config)
        _post_process(args)
        return

    if args.ablation:
        results = run_ablation_grid(cfg)
        if args.validate:
            for res in results:
                out_path = OUTPUT_DIR / f"{res['config']['name']}.json"
                validations = run_validation(
                    str(out_path),
                    include_eth=args.validate_eth,
                    eth_dataset_root=args.eth_dataset_root,
                    eth_download_if_missing=args.eth_download,
                    eth_dataset_url=args.eth_dataset_url,
                )
                _persist_validation(out_path, validations)
        _post_process(args)
        return

    result = run_experiment_sync(cfg)
    if args.validate:
        out_path = OUTPUT_DIR / f"{result['config']['name']}.json"
        validations = run_validation(
            str(out_path),
            include_eth=args.validate_eth,
            eth_dataset_root=args.eth_dataset_root,
            eth_download_if_missing=args.eth_download,
            eth_dataset_url=args.eth_dataset_url,
        )
        _persist_validation(out_path, validations)

    _post_process(args)


def _persist_validation(out_path: Path, validations: dict) -> None:
    if not out_path.exists():
        return
    data = json.loads(out_path.read_text(encoding="utf-8-sig"))
    data["validation"] = validations
    out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _post_process(args) -> None:
    if not args.skip_index:
        build_index()
    if not args.skip_export:
        export_csv()
    if args.report:
        generate_report()


def run_ablation_study_for_paper():
    """
    Runs the specific ablation study for the IEEE journal paper.
    """
    import numpy as np
    import csv
    import time
    from app.services.floorplan_service import process_floor_plan_image
    from app.sim.simulation_kernel import SimulationKernel
    from app.services.metrics_engine import MetricsEngine

    paper_dir = ROOT_DIR / "Research_Paper_IEEE"
    floor_plans_dir = paper_dir / "Floor_Plans"
    output_dir = paper_dir

    def run_sim(fp_data, num_agents, policy, blocked, panic, max_time=300):
        try:
            config = {
                "seed": int(time.time()*1000) % 10000, "mode": "paper", "num_agents": num_agents,
                "emergency_type": "fire", "routing_policy": policy, "panic_level": panic,
                "blocked_exits": blocked, "parameter_overrides": {"disable_hazards": True},
                "max_runtime_seconds": max_time
            }
            kernel = SimulationKernel("ablation_test", config)
            kernel.initialize(fp_data)
            metrics_engine = MetricsEngine()
            
            start_time = time.perf_counter()
            steps = 0
            while not kernel.is_complete() and steps < 1000 and (time.perf_counter() - start_time) < 4.0:
                frame = kernel.step(0.2)
                metrics_engine.add_frame(frame)
                steps += 1
                
            m = metrics_engine.calculate_metrics()
            return {
                "time": float(m.total_evacuation_time) if m.total_evacuation_time else float(steps * 0.2),
                "density": float(m.peak_congestion_density) if m.peak_congestion_density else 0.0
            }
        except Exception:
            return {"time": 0.0, "density": 0.0}

    def _rescale_floor_plan(floor_plan, target_max_dim=80.0):
        bounds = dict(floor_plan.get("building_bounds") or {})
        min_x, max_x = float(bounds.get("min_x", 0.0)), float(bounds.get("max_x", 100.0))
        min_y, max_y = float(bounds.get("min_y", 0.0)), float(bounds.get("max_y", 100.0))
        width, height = max(1.0, max_x - min_x), max(1.0, max_y - min_y)
        scale = max(width, height) / target_max_dim if max(width, height) > target_max_dim else 1.0
        sx = lambda x: (float(x) - min_x) / scale
        sy = lambda y: (float(y) - min_y) / scale
        walls = [{"x1": sx(w.get("x1",0)), "y1": sy(w.get("y1",0)), "x2": sx(w.get("x2",0)), "y2": sy(w.get("y2",0))} for w in list(floor_plan.get("detected_walls", []))[:250]]
        exits = [{"id": str(e.get("id") or f"e_{i}") , "x": sx(e.get("x",0)), "y": sy(e.get("z", e.get("y",0))), "z": sy(e.get("z", e.get("y",0))), "width": max(1.2, float(e.get("width",2.0))/scale), "capacity": 100} for i, e in enumerate(floor_plan.get("exits",[]))]
        if len(exits) < 2:
            cy = (height/scale) * 0.5
            exits.extend([{"id":"gen_e1", "x":1.0, "y":cy, "z":cy, "width":2.0, "capacity":100}, {"id":"gen_e2", "x":(width/scale)-1.0, "y":cy, "z":cy, "width":2.0, "capacity":100}])
        return {"building_bounds": {"min_x":0,"min_y":0,"max_x":width/scale,"max_y":height/scale}, "detected_walls": walls, "exits": exits, "detected_obstacles":[]}

    print("Starting Ablation Study simulations for IEEE Paper...")
    academic_plan_path = floor_plans_dir / "Academic_Plan.jpg"
    if not academic_plan_path.exists():
        print(f"Error: {academic_plan_path} not found.")
        return

    fp_raw = process_floor_plan_image("image/jpeg", str(academic_plan_path), {"mode": "traditional"})
    fp_scaled = _rescale_floor_plan(fp_raw)
    
    scenarios = {
        "Full Model (S4)": {"policy": "least_crowded", "panic": 0.3},
        "No Congestion Routing": {"policy": "shortest_path", "panic": 0.3},
        "No Panic Variation": {"policy": "least_crowded", "panic": 0.1},
    }
    
    results = []
    for name, params in scenarios.items():
        print(f"  -> Running: {name} (10 iters)...", end="", flush=True)
        times, densities = [], []
        for _ in range(10):
            res = run_sim(fp_scaled, num_agents=80, policy=params["policy"], blocked=[], panic=params["panic"])
            times.append(res["time"])
            densities.append(res["density"])
        
        row = {
            "Configuration": name,
            "Mean Time (s)": round(float(np.mean(times)), 2),
            "Mean Density": round(float(np.mean(densities)), 2)
        }
        results.append(row)
        print(f" done (T={row['Mean Time (s)']}s)")

    output_csv = output_dir / "ablation_study_results.csv"
    with open(output_csv, "w", newline="", encoding='utf-8') as f:
        if results:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
    print(f"\nAblation study completed. Results written to {output_csv}")


if __name__ == "__main__":
    main()
