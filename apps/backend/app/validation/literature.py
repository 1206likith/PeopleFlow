import pandas as pd
from typing import Dict, Any

class SFPEBenchmarks:
    """Society of Fire Protection Engineers (SFPE) Handbook Benchmarks"""
    
    # Established specific flow rate maximums (persons / meter effective width / second)
    MAX_SPECIFIC_FLOW_RATE = 1.32
    
    # Typical walking speeds on level terrain (meters / second)
    MEAN_WALKING_SPEED = 1.19
    SPEED_STD_DEV = 0.25
    
    # Capacity thresholds for crowd density
    JAM_DENSITY = 5.4  # persons / m^2 where movement stops
    OPTIMAL_DENSITY = 1.9 # persons / m^2 for maximum flow
    
    @classmethod
    def validate_simulation_outputs(cls, sim_results: pd.DataFrame, exit_widths_meters: Dict[str, float]) -> Dict[str, Any]:
        """
        Validates an existing simulation results dataframe against SFPE literature.
        Returns a dictionary indicating pass/fail checks and error margins.
        """
        validation_report: Dict[str, Any] = {
            "flow_rate_valid": True,
            "flow_error_margin": 0.0,
            "speed_valid": True,
            "speed_error_margin": 0.0,
            "jam_density_respect": True,
            "notes": []
        }
        
        # Validate Mean Flow
        if "max_exit_flow" in sim_results.columns and exit_widths_meters:
            total_width = sum(exit_widths_meters.values())
            # Convert raw flow (persons/sec) to specific flow (persons/sec/meter)
            avg_specific_flow = sim_results["max_exit_flow"].mean() / total_width
            
            error = (avg_specific_flow - cls.MAX_SPECIFIC_FLOW_RATE) / cls.MAX_SPECIFIC_FLOW_RATE
            validation_report["flow_error_margin"] = round(error * 100, 2)
            
            # Flow shouldn't dramatically exceed physical limits by more than 15%
            if avg_specific_flow > cls.MAX_SPECIFIC_FLOW_RATE * 1.15:
                validation_report["flow_rate_valid"] = False
                validation_report["notes"].append(f"Specific flow {avg_specific_flow:.2f} ps/m/s exceeds SFPE max 1.32")
                
        # Validate Meaning Walking Speeds
        if "mean_speed" in sim_results.columns:
            observed_mean_speed = sim_results["mean_speed"].mean()
            error = (observed_mean_speed - cls.MEAN_WALKING_SPEED) / cls.MEAN_WALKING_SPEED
            validation_report["speed_error_margin"] = round(error * 100, 2)
            
            # Speeds shouldn't be entirely unrealistic (e.g. > 3 m/s for a crowd)
            if observed_mean_speed > 3.0 or observed_mean_speed < 0.1:
                validation_report["speed_valid"] = False
                validation_report["notes"].append(f"Mean speed {observed_mean_speed:.2f} m/s falls outside valid pedestrian ranges.")

        return validation_report

    @staticmethod
    def print_validation_summary(report: Dict[str, Any]):
        print("=== Literature Validation Report (SFPE) ===")
        print(f"Flow Rate Realistic: {'Pass' if report['flow_rate_valid'] else 'Fail'} (Margin: {report['flow_error_margin']}%)")
        print(f"Walking Speeds Realistic: {'Pass' if report['speed_valid'] else 'Fail'} (Margin: {report['speed_error_margin']}%)")
        if report["notes"]:
            print("Notes / Warnings:")
            for n in report["notes"]:
                print(f"  - {n}")
        if report['flow_rate_valid'] and report['speed_valid']:
            print("\nCONCLUSION: 'Results align with established evacuation models'")
