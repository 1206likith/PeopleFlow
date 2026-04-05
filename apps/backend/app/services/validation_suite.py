"""
Validation & Benchmark Suite
Compares simulation results against published evacuation data
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging

from app.validation.benchmark_registry import get_validation_benchmark_registry

logger = logging.getLogger(__name__)

@dataclass
class BenchmarkCase:
    """Benchmark case from research literature"""
    name: str
    description: str
    source: str
    parameters: Dict[str, Any]
    expected_results: Dict[str, float]
    tolerance: Dict[str, float]  # Acceptable error margins

@dataclass
class ValidationResult:
    """Result of validation against benchmark"""
    benchmark_name: str
    passed: bool
    metrics_comparison: Dict[str, Dict[str, float]]  # metric -> {expected, actual, error, passed}
    overall_score: float  # 0-100
    notes: List[str]

class ValidationSuite:
    """Validates simulation against published research data"""
    
    def __init__(self):
        self.registry = get_validation_benchmark_registry()
        self.benchmarks = self._load_benchmarks()
    
    def _load_benchmarks(self) -> Dict[str, BenchmarkCase]:
        """Load benchmark cases from research literature"""
        benchmarks: Dict[str, BenchmarkCase] = {}
        for definition in self.registry.list_suite_benchmarks():
            benchmarks[definition.benchmark_id] = BenchmarkCase(
                name=definition.name,
                description=definition.description,
                source=definition.source,
                parameters=definition.parameters,
                expected_results=definition.expected_results,
                tolerance=definition.tolerance,
            )
        return benchmarks
    
    def validate_simulation(
        self,
        benchmark_id: str,
        simulation_results: Dict[str, Any]
    ) -> ValidationResult:
        """Validate simulation results against benchmark"""
        benchmark = self.benchmarks.get(benchmark_id)
        if not benchmark:
            raise ValueError(f"Benchmark {benchmark_id} not found")
        
        metrics_comparison = {}
        passed_metrics = 0
        total_metrics = len(benchmark.expected_results)
        
        for metric, expected_value in benchmark.expected_results.items():
            actual_value = simulation_results.get(metric)
            if actual_value is None:
                metrics_comparison[metric] = {
                    "expected": expected_value,
                    "actual": None,
                    "error": None,
                    "passed": False
                }
                continue
            
            error = abs(actual_value - expected_value)
            tolerance = benchmark.tolerance.get(metric, expected_value * 0.1)  # 10% default
            passed = error <= tolerance
            
            metrics_comparison[metric] = {
                "expected": expected_value,
                "actual": actual_value,
                "error": error,
                "error_percentage": (error / expected_value * 100) if expected_value > 0 else 0,
                "tolerance": tolerance,
                "passed": passed
            }
            
            if passed:
                passed_metrics += 1
        
        overall_score = (passed_metrics / total_metrics) * 100 if total_metrics > 0 else 0
        passed = overall_score >= 70.0  # 70% threshold
        
        # Generate notes
        notes = []
        if passed:
            notes.append(f"Validation passed with {overall_score:.1f}% accuracy")
        else:
            notes.append(f"Validation failed: {overall_score:.1f}% accuracy (threshold: 70%)")
        
        for metric, comparison in metrics_comparison.items():
            if not comparison["passed"]:
                notes.append(
                    f"{metric}: Expected {comparison['expected']:.2f}, "
                    f"Got {comparison['actual']:.2f} "
                    f"(Error: {comparison['error_percentage']:.1f}%)"
                )
        
        return ValidationResult(
            benchmark_name=benchmark.name,
            passed=passed,
            metrics_comparison=metrics_comparison,
            overall_score=overall_score,
            notes=notes
        )
    
    def run_all_benchmarks(self, simulation_results_map: Dict[str, Dict]) -> Dict[str, ValidationResult]:
        """Run all benchmarks and return results"""
        results = {}
        for benchmark_id in self.benchmarks.keys():
            if benchmark_id in simulation_results_map:
                try:
                    result = self.validate_simulation(
                        benchmark_id,
                        simulation_results_map[benchmark_id]
                    )
                    results[benchmark_id] = result
                except Exception as e:
                    logger.error(f"Error validating {benchmark_id}: {e}")
        
        return results
    
    def get_benchmark(self, benchmark_id: str) -> Optional[BenchmarkCase]:
        """Get benchmark case"""
        return self.benchmarks.get(benchmark_id)
    
    def list_benchmarks(self) -> List[Dict]:
        """List all available benchmarks"""
        return [benchmark.to_dict() for benchmark in self.registry.list_suite_benchmarks()]

# Global instance
validation_suite = ValidationSuite()

