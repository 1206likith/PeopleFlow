"""
Model Validation Engine
Compares simulation results against published evacuation data
Benchmark tests: corridor evacuation, multi-exit scenarios, behavioral decisions
"""
import math
import numpy as np
import logging
from typing import Dict, List
from dataclasses import dataclass

from app.validation.benchmark_registry import get_validation_benchmark_registry

logger = logging.getLogger(__name__)

@dataclass
class BenchmarkResult:
    """Benchmark validation result"""
    test_name: str
    expected_value: float
    actual_value: float
    rmse: float
    error_percent: float
    passed: bool

class ValidationEngine:
    """
    Validation engine for comparing against research benchmarks
    """
    
    def __init__(self):
        self.registry = get_validation_benchmark_registry()

    @property
    def benchmarks(self) -> Dict[str, Dict]:
        runtime_benchmarks = {}
        for benchmark in self.registry.list_runtime_benchmarks():
            runtime_benchmarks[benchmark.benchmark_id] = {
                "expected_results": benchmark.expected_results,
                "tolerance": benchmark.tolerance,
            }
        return runtime_benchmarks
    
    def validate_simulation(
        self,
        simulation_results: Dict,
        agents: List[Dict],
        exits: List[Dict]
    ) -> Dict:
        """
        Validate simulation against benchmarks
        
        Returns:
            Validation report with RMSE, error percentages, pass/fail
        """
        results = []
        
        # Test 1: Corridor flow rate
        flow_result = self._test_corridor_flow_rate(exits, agents)
        results.append(flow_result)
        
        # Test 2: Density-speed relationship
        density_result = self._test_density_speed_curve(agents)
        results.append(density_result)
        
        # Test 3: Pre-evacuation delay distribution
        delay_result = self._test_pre_evacuation_delay(agents)
        results.append(delay_result)
        
        # Calculate overall score
        passed_tests = sum(1 for r in results if r.passed)
        total_tests = len(results)
        overall_score = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        return {
            "overall_score": overall_score,
            "passed_tests": passed_tests,
            "total_tests": total_tests,
            "results": [
                {
                    "test_name": r.test_name,
                    "expected": r.expected_value,
                    "actual": r.actual_value,
                    "rmse": r.rmse,
                    "error_percent": r.error_percent,
                    "passed": r.passed
                }
                for r in results
            ],
            "validation_status": "passed" if overall_score >= 70 else "failed"
        }
    
    def _test_corridor_flow_rate(self, exits: List[Dict], agents: List[Dict]) -> BenchmarkResult:
        """Test exit flow rate against research benchmark"""
        benchmark = self.registry.get_runtime_benchmark("corridor_flow_rate")
        if benchmark is None:
            raise ValueError("Runtime benchmark corridor_flow_rate is not registered")
        expected = float(benchmark.expected_results.get("flow_rate", 1.33))
        tolerance = float(benchmark.tolerance.get("relative_error", 0.15))
        
        # Calculate actual flow rate
        total_flow = 0.0
        total_width = 0.0
        
        for exit_data in exits:
            exit_width = exit_data.get("width", 2.0)
            # Count agents that passed through
            agents_passed = sum(
                1 for agent in agents
                if agent.get("status") == "evacuated" and
                agent.get("target_exit") == exit_data.get("id")
            )
            
            # Estimate flow rate (simplified)
            if exit_width > 0:
                total_flow += agents_passed / exit_width
                total_width += exit_width
        
        actual = total_flow / len(exits) if exits else 0.0
        
        error = abs(actual - expected)
        error_percent = (error / expected) * 100 if expected > 0 else 100
        
        return BenchmarkResult(
            test_name="corridor_flow_rate",
            expected_value=expected,
            actual_value=actual,
            rmse=error,
            error_percent=error_percent,
            passed=error_percent <= tolerance * 100
        )
    
    def _test_density_speed_curve(self, agents: List[Dict]) -> BenchmarkResult:
        """Test density-speed relationship (fundamental diagram)"""
        benchmark = self.registry.get_runtime_benchmark("density_speed_curve")
        if benchmark is None:
            raise ValueError("Runtime benchmark density_speed_curve is not registered")
        expected_points = benchmark.expected_results.get("points", [])
        tolerance = float(benchmark.tolerance.get("rmse", 0.20))
        
        # Calculate actual density-speed points from simulation
        actual_points = []
        
        # Sample agents at different densities
        for agent in agents:
            if agent.get("status") == "evacuated":
                continue
            
            # Calculate local density
            agent_x = agent.get("x", 0.0)
            agent_z = agent.get("z", agent.get("y", 0.0))
            
            nearby_count = sum(
                1 for other in agents
                if other.get("status") != "evacuated" and
                math.sqrt(
                    (other.get("x", 0) - agent_x)**2 +
                    (other.get("z", other.get("y", 0)) - agent_z)**2
                ) < 5.0
            )
            
            density = nearby_count / (math.pi * 5.0 ** 2)
            speed = agent.get("speed", 1.35)
            
            actual_points.append((density, speed))
        
        # Calculate RMSE against expected curve
        rmse = 0.0
        if actual_points:
            for exp_density, exp_speed in expected_points:
                # Find closest actual point
                closest_error = float('inf')
                for act_density, act_speed in actual_points:
                    if abs(act_density - exp_density) < 0.5:
                        error = abs(act_speed - exp_speed)
                        closest_error = min(closest_error, error)
                
                if closest_error != float('inf'):
                    rmse += closest_error ** 2
            
            rmse = math.sqrt(rmse / len(expected_points))
        
        error_percent = (rmse / expected_points[0][1]) * 100 if expected_points else 100
        
        return BenchmarkResult(
            test_name="density_speed_curve",
            expected_value=expected_points[0][1],  # Reference speed
            actual_value=actual_points[0][1] if actual_points else 0.0,
            rmse=rmse,
            error_percent=error_percent,
            passed=rmse <= tolerance
        )
    
    def _test_pre_evacuation_delay(self, agents: List[Dict]) -> BenchmarkResult:
        """Test pre-evacuation delay distribution"""
        benchmark = self.registry.get_runtime_benchmark("pre_evacuation_delay")
        if benchmark is None:
            raise ValueError("Runtime benchmark pre_evacuation_delay is not registered")
        expected_mean = float(benchmark.expected_results.get("mean", 2.5))
        expected_std = float(benchmark.expected_results.get("std", 1.2))
        mean_tolerance = float(benchmark.tolerance.get("mean_abs", 0.3))
        std_tolerance = float(benchmark.tolerance.get("std_abs", 0.3))
        
        # Extract delays from agents
        delays = [
            agent.get("pre_evacuation_delay", 0.0)
            for agent in agents
            if agent.get("pre_evacuation_delay", 0.0) > 0
        ]
        
        if not delays:
            return BenchmarkResult(
                test_name="pre_evacuation_delay",
                expected_value=expected_mean,
                actual_value=0.0,
                rmse=expected_mean,
                error_percent=100.0,
                passed=False
            )
        
        actual_mean = np.mean(delays)
        actual_std = np.std(delays)
        
        mean_error = abs(actual_mean - expected_mean)
        std_error = abs(actual_std - expected_std)
        
        error_percent = (mean_error / expected_mean) * 100 if expected_mean > 0 else 100
        
        return BenchmarkResult(
            test_name="pre_evacuation_delay",
            expected_value=expected_mean,
            actual_value=actual_mean,
            rmse=mean_error,
            error_percent=error_percent,
            passed=mean_error <= mean_tolerance and std_error <= std_tolerance
        )

# Global validation engine
validation_engine = ValidationEngine()

