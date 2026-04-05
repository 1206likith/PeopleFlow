"""
Model Calibration & Validation Framework
Calibrates agent parameters using real evacuation datasets (e.g., EXIT89)
Compares simulation outcomes with documented empirical curves
Research: Model calibration and validation (ScienceDirect, Wikipedia)
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import logging

from app.validation.benchmark_registry import get_validation_benchmark_registry

logger = logging.getLogger(__name__)

@dataclass
class EmpiricalDataPoint:
    """Single data point from empirical studies"""
    scenario: str
    metric_name: str
    value: float
    uncertainty: Optional[float] = None
    source: Optional[str] = None

@dataclass
class CalibrationTarget:
    """Target metric for calibration"""
    metric_name: str
    empirical_value: float
    empirical_std: Optional[float] = None
    weight: float = 1.0  # Importance weight

class EXIT89Dataset:
    """
    EXIT89 dataset loader and validator
    Research dataset for evacuation model validation
    """
    
    @staticmethod
    def _registry():
        return get_validation_benchmark_registry()

    @classmethod
    def get_pre_evac_delay_distribution(cls) -> Dict:
        """Get EXIT89 pre-evacuation delay distribution"""
        benchmark = cls._registry().get_runtime_benchmark("pre_evacuation_delay")
        expected = benchmark.expected_results if benchmark else {}
        return {
            "mean": float(expected.get("mean", 2.5)),
            "std": float(expected.get("std", 1.2)),
            "distribution": "lognormal",
            "min": 0.1,
            "max": 30.0,
        }
    
    @classmethod
    def get_walking_speed_distribution(cls) -> Dict:
        """Get EXIT89 walking speed distribution"""
        benchmark = cls._registry().get_runtime_benchmark("density_speed_curve")
        expected = benchmark.expected_results if benchmark else {}
        points = expected.get("points", [])
        free_flow_speed = float(points[0][1]) if points else 1.35
        return {
            "mean": free_flow_speed,
            "std": 0.25,
            "min": 0.5,
            "max": 2.5,
        }
    
    @classmethod
    def get_flow_rate_parameters(cls) -> Dict:
        """Get EXIT89 flow rate parameters"""
        corridor = cls._registry().get_runtime_benchmark("corridor_flow_rate")
        density_curve = cls._registry().get_runtime_benchmark("density_speed_curve")
        peak_flow_range = {}
        if density_curve is not None:
            peak_flow_range = density_curve.expected_results.get("peak_flow_rate_range", {})
        base_flow_rate = float(corridor.expected_results.get("flow_rate", 1.33)) if corridor else 1.33
        return {
            "base_flow_rate": base_flow_rate,
            "max_flow_rate": float(peak_flow_range.get("max", 2.0) or 2.0),
            "saturation_density": 4.0,
        }

class ModelCalibrator:
    """
    Calibrates model parameters against empirical data
    Uses optimization to minimize difference between simulation and empirical results
    """
    
    def __init__(self):
        self.calibration_targets: List[CalibrationTarget] = []
        self.empirical_datasets: Dict[str, List[EmpiricalDataPoint]] = {}
        self.load_exit89_data()
    
    def load_exit89_data(self):
        """Load EXIT89 dataset"""
        pre_evacuation_delays = EXIT89Dataset.get_pre_evac_delay_distribution()
        walking_speeds = EXIT89Dataset.get_walking_speed_distribution()
        flow_rates = EXIT89Dataset.get_flow_rate_parameters()
        exit89_data = [
            EmpiricalDataPoint(
                scenario="EXIT89",
                metric_name="pre_evacuation_delay_mean",
                value=pre_evacuation_delays["mean"],
                uncertainty=pre_evacuation_delays["std"],
                source="EXIT89"
            ),
            EmpiricalDataPoint(
                scenario="EXIT89",
                metric_name="walking_speed_mean",
                value=walking_speeds["mean"],
                uncertainty=walking_speeds["std"],
                source="EXIT89"
            ),
            EmpiricalDataPoint(
                scenario="EXIT89",
                metric_name="flow_rate_base",
                value=flow_rates["base_flow_rate"],
                source="EXIT89"
            )
        ]
        
        self.empirical_datasets["EXIT89"] = exit89_data
    
    def add_calibration_target(
        self,
        metric_name: str,
        empirical_value: float,
        empirical_std: Optional[float] = None,
        weight: float = 1.0
    ):
        """Add a calibration target"""
        target = CalibrationTarget(
            metric_name=metric_name,
            empirical_value=empirical_value,
            empirical_std=empirical_std,
            weight=weight
        )
        self.calibration_targets.append(target)
    
    def calculate_calibration_error(
        self,
        simulation_results: Dict[str, float],
        targets: Optional[List[CalibrationTarget]] = None
    ) -> float:
        """
        Calculate calibration error (difference between simulation and empirical)
        
        Returns:
            Total weighted error
        """
        if targets is None:
            targets = self.calibration_targets
        
        total_error = 0.0
        total_weight = 0.0
        
        for target in targets:
            sim_value = simulation_results.get(target.metric_name, 0.0)
            emp_value = target.empirical_value
            
            # Calculate error (normalized by empirical value)
            if emp_value > 0:
                relative_error = abs(sim_value - emp_value) / emp_value
            else:
                relative_error = abs(sim_value - emp_value)
            
            # Weight by uncertainty (if available)
            if target.empirical_std:
                uncertainty_weight = 1.0 / (1.0 + target.empirical_std / emp_value)
            else:
                uncertainty_weight = 1.0
            
            weighted_error = relative_error * target.weight * uncertainty_weight
            total_error += weighted_error
            total_weight += target.weight * uncertainty_weight
        
        # Normalize by total weight
        if total_weight > 0:
            return total_error / total_weight
        return total_error
    
    def calibrate_parameters(
        self,
        parameter_ranges: Dict[str, Tuple[float, float]],
        simulation_function,
        max_iterations: int = 100
    ) -> Dict[str, float]:
        """
        Calibrate parameters using optimization
        
        Args:
            parameter_ranges: Dict of parameter_name -> (min, max)
            simulation_function: Function that runs simulation and returns results dict
            max_iterations: Maximum optimization iterations
        
        Returns:
            Optimized parameter values
        """
        # Simple grid search (can be replaced with more sophisticated optimization)
        best_params = {}
        best_error = float('inf')
        
        # Sample parameter space
        for iteration in range(max_iterations):
            # Sample random parameters
            params = {}
            for param_name, (min_val, max_val) in parameter_ranges.items():
                params[param_name] = np.random.uniform(min_val, max_val)
            
            # Run simulation with these parameters
            try:
                simulation_results = simulation_function(params)
                
                # Calculate error
                error = self.calculate_calibration_error(simulation_results)
                
                if error < best_error:
                    best_error = error
                    best_params = params.copy()
            except Exception as e:
                logger.warning(f"Simulation failed with params {params}: {e}")
                continue
        
        return best_params

class ValidationSuite:
    """
    Validation suite for comparing simulation with empirical data
    Cross-validates multiple scenarios
    """
    
    def __init__(self):
        self.calibrator = ModelCalibrator()
        self.validation_results: List[Dict] = []
    
    def validate_against_exit89(
        self,
        simulation_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate simulation results against EXIT89 dataset
        
        Returns:
            Validation report with metrics and comparisons
        """
        exit89_data = self.calibrator.empirical_datasets.get("EXIT89", [])
        
        validation_report = {
            "dataset": "EXIT89",
            "metrics": [],
            "overall_score": 0.0,
            "passed": True
        }
        
        total_score = 0.0
        total_weight = 0.0
        
        for data_point in exit89_data:
            metric_name = data_point.metric_name
            sim_value = simulation_results.get(metric_name, 0.0)
            emp_value = data_point.value
            
            # Calculate error
            if emp_value > 0:
                relative_error = abs(sim_value - emp_value) / emp_value
            else:
                relative_error = abs(sim_value - emp_value)
            
            # Score (0-1, higher is better)
            if data_point.uncertainty:
                # Within uncertainty bounds = perfect score
                if abs(sim_value - emp_value) <= data_point.uncertainty:
                    score = 1.0
                else:
                    # Score decreases with error
                    score = max(0.0, 1.0 - (relative_error / 0.5))  # 50% error = 0 score
            else:
                score = max(0.0, 1.0 - relative_error)
            
            validation_report["metrics"].append({
                "metric": metric_name,
                "simulated": sim_value,
                "empirical": emp_value,
                "error": relative_error,
                "score": score,
                "passed": score >= 0.7  # 70% threshold
            })
            
            total_score += score
            total_weight += 1.0
        
        if total_weight > 0:
            validation_report["overall_score"] = total_score / total_weight
            validation_report["passed"] = validation_report["overall_score"] >= 0.7
        
        return validation_report
    
    def validate_fundamental_diagram(
        self,
        simulation_fundamental_diagram: List[Dict[str, float]],
        empirical_curve: Optional[List[Dict[str, float]]] = None
    ) -> Dict[str, Any]:
        """
        Validate fundamental diagram against empirical curve
        
        Research: Fundamental diagrams should match empirical data (ScienceDirect)
        """
        if not simulation_fundamental_diagram:
            return {"passed": False, "error": "No simulation data"}
        
        # Extract density and flow from simulation
        sim_densities = [d["density"] for d in simulation_fundamental_diagram]
        sim_flows = [d["flow_rate"] for d in simulation_fundamental_diagram]
        
        # Compare with empirical curve if provided
        if empirical_curve:
            emp_densities = [d["density"] for d in empirical_curve]
            emp_flows = [d["flow_rate"] for d in empirical_curve]
            
            # Interpolate and compare
            # (Simplified - would use proper curve comparison)
            max_flow_error = 0.0
            for emp_d, emp_f in zip(emp_densities, emp_flows):
                # Find closest simulation point
                closest_idx = np.argmin([abs(d - emp_d) for d in sim_densities])
                sim_f = sim_flows[closest_idx]
                
                if emp_f > 0:
                    error = abs(sim_f - emp_f) / emp_f
                    max_flow_error = max(max_flow_error, error)
            
            passed = max_flow_error < 0.3  # 30% error threshold
            
            return {
                "passed": passed,
                "max_error": max_flow_error,
                "simulation_curve": simulation_fundamental_diagram,
                "empirical_curve": empirical_curve
            }
        
        # Validate shape (should have peak flow at moderate density)
        # Research: Peak flow typically at 2-3 persons/m²
        peak_flow_idx = np.argmax(sim_flows)
        peak_density = sim_densities[peak_flow_idx]
        
        shape_valid = 1.5 <= peak_density <= 4.0
        
        return {
            "passed": shape_valid,
            "peak_density": peak_density,
            "peak_flow": sim_flows[peak_flow_idx],
            "simulation_curve": simulation_fundamental_diagram
        }
    
    def cross_validate_scenarios(
        self,
        scenario_results: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Cross-validate multiple scenarios
        
        Args:
            scenario_results: Dict of scenario_name -> simulation_results
        
        Returns:
            Cross-validation report
        """
        validation_scores = {}
        
        for scenario_name, results in scenario_results.items():
            if scenario_name == "EXIT89":
                validation = self.validate_against_exit89(results)
            else:
                # Generic validation
                validation = {
                    "dataset": scenario_name,
                    "overall_score": 0.5,  # Placeholder
                    "passed": False
                }
            
            validation_scores[scenario_name] = validation
        
        # Overall cross-validation score
        overall_scores = [v.get("overall_score", 0.0) for v in validation_scores.values()]
        mean_score = np.mean(overall_scores) if overall_scores else 0.0
        
        return {
            "scenario_validations": validation_scores,
            "overall_cross_validation_score": mean_score,
            "passed": mean_score >= 0.7
        }

# Global instances
model_calibrator = ModelCalibrator()
validation_suite = ValidationSuite()

