import pandas as pd
from typing import Dict, Any
from app.sim.core_engine import CoreSimulationEngine, SimConfig
from app.experiments import OUTPUT_DIR
from app.experiments.stats_engine import ExperimentStatsEngine

class PolicyComparator:
    """Runs A/B tests against different evacuation policies."""
    
    POLICIES = ["nearest", "least_crowded", "guided"]
    
    @classmethod
    def run_comparison(cls, floor_plan: Dict[str, Any], runs_per_policy: int = 3, num_agents: int = 150):
        print(f"Starting Policy Comparison: {runs_per_policy} runs per policy...")
        results = []
        time_series_data = {p: [] for p in cls.POLICIES}
        
        for policy in cls.POLICIES:
            print(f"Testing Policy: {policy}")
            policy_evac_times = []
            
            for run_id in range(runs_per_policy):
                seed = 42 + run_id
                config = SimConfig(
                    num_agents=num_agents,
                    routing_policy=policy,
                    seed=seed
                )
                
                engine = CoreSimulationEngine(config)
                engine.initialize_from_floor_plan(floor_plan)
                engine.initialize_agents()
                
                run_time_series = []
                while not engine.is_complete() and engine.time < 300.0:
                    engine.update(0.1)
                    if int(engine.time * 10) % 5 == 0:  # capture every 0.5s
                        current_speeds = [a.speed for a in engine.agents]
                        avg_spd = sum(current_speeds)/len(current_speeds) if current_speeds else 0.0
                        run_time_series.append({
                            "step": engine.time,
                            "evacuated": engine.evacuated_count,
                            "remaining": num_agents - engine.evacuated_count,
                            "mean_speed": avg_spd
                        })
                
                # Append completion time
                policy_evac_times.append(engine.time)
                time_series_data[policy].append(pd.DataFrame(run_time_series))
            
            # Record final metrics
            ci_data = ExperimentStatsEngine.compute_confidence_intervals(policy_evac_times)
            results.append({
                "Policy": policy,
                "Mean Evac Time (s)": round(ci_data["mean"], 2),
                "Lower CI": round(ci_data["ci_lower"], 2),
                "Upper CI": round(ci_data["ci_upper"], 2),
                "Std Dev": round(ci_data["std"], 2),
                "Raw Times": policy_evac_times
            })
            
        # Compile into Comparison Table
        df = pd.DataFrame(results)
        df_display = df.drop(columns=["Raw Times"])
        print("\n=== Publishable Comparison Table ===")
        print(df_display.to_markdown(index=False))
        
        # Save output
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        comparison_csv_path = OUTPUT_DIR / "policy_comparison.csv"
        df_display.to_csv(comparison_csv_path, index=False)
        
        # Plot time series using Visualizer
        plt_colors = ["#1f77b4", "#ff7f0e", "#2ca02c"]
        import matplotlib.pyplot as plt
        plt.figure(figsize=(10, 6))
        
        for i, policy in enumerate(cls.POLICIES):
            agg_df = ExperimentStatsEngine.aggregate_time_series(time_series_data[policy])
            if agg_df.empty:
                continue
            
            time_data = agg_df["step"].tolist()
            mean_rem = agg_df["remaining_mean"].tolist()
            plt.plot(time_data, mean_rem, linewidth=2, color=plt_colors[i], label=f"{policy} (Mean)")
            
        curve_path = OUTPUT_DIR / "policy_curves.png"
        plt.savefig(curve_path, dpi=300)
        plt.close()

        # Generate the Academic Report PDF
        from app.experiments.report_generator import AcademicReportGenerator
        AcademicReportGenerator.generate_pdf(str(comparison_csv_path), [str(curve_path)])
        
        return df

if __name__ == "__main__":
    dummy_floor_plan = {
        "building_bounds": {"min_x": 0.0, "max_x": 100.0, "min_y": 0.0, "max_y": 100.0},
        "exits": [
            {"id": "exit_1", "x": 10, "y": 0, "width": 2.0},
            {"id": "exit_2", "x": 90, "y": 0, "width": 2.0}
        ],
        "detected_walls": [],
        "rooms": [],
        "detected_obstacles": []
    }
    PolicyComparator.run_comparison(dummy_floor_plan, runs_per_policy=2, num_agents=50)
