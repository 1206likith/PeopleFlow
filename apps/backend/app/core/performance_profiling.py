"""
Performance profiling and guardrails for critical paths.
Validates p95 response times and hot-path execution profiles.
"""

import time
import cProfile
import pstats
import io
from contextlib import contextmanager
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
import statistics
import logging

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Record for a single performance measurement."""
    name: str
    duration_ms: float
    status_code: Optional[int] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class PerformanceStats:
    """Aggregated performance statistics."""
    name: str
    measurements: List[float]
    
    @property
    def count(self) -> int:
        return len(self.measurements)
    
    @property
    def min_ms(self) -> float:
        return min(self.measurements) if self.measurements else 0.0
    
    @property
    def max_ms(self) -> float:
        return max(self.measurements) if self.measurements else 0.0
    
    @property
    def mean_ms(self) -> float:
        return statistics.mean(self.measurements) if self.measurements else 0.0
    
    @property
    def median_ms(self) -> float:
        return statistics.median(self.measurements) if self.measurements else 0.0
    
    @property
    def p95_ms(self) -> float:
        """95th percentile latency."""
        if len(self.measurements) < 2:
            return self.max_ms
        sorted_measurements = sorted(self.measurements)
        index = int(len(sorted_measurements) * 0.95)
        return sorted_measurements[min(index, len(sorted_measurements) - 1)]
    
    @property
    def p99_ms(self) -> float:
        """99th percentile latency."""
        if len(self.measurements) < 2:
            return self.max_ms
        sorted_measurements = sorted(self.measurements)
        index = int(len(sorted_measurements) * 0.99)
        return sorted_measurements[min(index, len(sorted_measurements) - 1)]
    
    def is_within_threshold(self, p95_threshold_ms: float) -> bool:
        """Check if p95 latency is within threshold."""
        return self.p95_ms <= p95_threshold_ms


class PerformanceProfiler:
    """Collects and analyzes performance metrics."""
    
    def __init__(self):
        self.metrics: Dict[str, List[float]] = {}
    
    def record(self, name: str, duration_ms: float) -> None:
        """Record a performance measurement."""
        if name not in self.metrics:
            self.metrics[name] = []
        self.metrics[name].append(duration_ms)
    
    def get_stats(self, name: str) -> Optional[PerformanceStats]:
        """Get aggregated statistics for a metric."""
        if name not in self.metrics:
            return None
        return PerformanceStats(name, self.metrics[name])
    
    def get_all_stats(self) -> List[PerformanceStats]:
        """Get statistics for all metrics."""
        return [PerformanceStats(name, measurements) 
                for name, measurements in self.metrics.items()]
    
    def report(self) -> str:
        """Generate a performance report."""
        lines = ["Performance Report", "=" * 50]
        
        for stats in self.get_all_stats():
            lines.append(f"\n{stats.name}:")
            lines.append(f"  Count:  {stats.count}")
            lines.append(f"  Min:    {stats.min_ms:.2f} ms")
            lines.append(f"  Mean:   {stats.mean_ms:.2f} ms")
            lines.append(f"  Median: {stats.median_ms:.2f} ms")
            lines.append(f"  P95:    {stats.p95_ms:.2f} ms")
            lines.append(f"  P99:    {stats.p99_ms:.2f} ms")
            lines.append(f"  Max:    {stats.max_ms:.2f} ms")
        
        return "\n".join(lines)
    
    def validate_thresholds(self, thresholds: Dict[str, float]) -> Tuple[bool, List[str]]:
        """
        Validate that all metrics are within specified thresholds.
        
        Args:
            thresholds: Dict of metric_name -> p95_threshold_ms
        
        Returns:
            Tuple of (all_pass: bool, violations: List[str])
        """
        violations = []
        
        for name, threshold in thresholds.items():
            stats = self.get_stats(name)
            if stats and not stats.is_within_threshold(threshold):
                violations.append(
                    f"{name}: p95={stats.p95_ms:.2f}ms exceeds threshold={threshold}ms"
                )
        
        return len(violations) == 0, violations


# Global profiler instance
_global_profiler = PerformanceProfiler()


@contextmanager
def profile_execution(name: str):
    """Context manager to profile execution time."""
    start = time.time()
    try:
        yield
    finally:
        duration_ms = (time.time() - start) * 1000
        _global_profiler.record(name, duration_ms)
        logger.debug(f"{name}: {duration_ms:.2f}ms")


def get_profiler() -> PerformanceProfiler:
    """Get the global performance profiler."""
    return _global_profiler


@contextmanager
def cpu_profile_execution(name: str):
    """Context manager for detailed CPU profiling."""
    pr = cProfile.Profile()
    pr.enable()
    start = time.time()
    
    try:
        yield pr
    finally:
        pr.disable()
        duration_ms = (time.time() - start) * 1000
        _global_profiler.record(f"{name}_cpu", duration_ms)
        
        # Get top functions by cumulative time
        s = io.StringIO()
        ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
        ps.print_stats(10)  # Top 10
        logger.debug(f"CPU Profile for {name} ({duration_ms:.2f}ms):\n{s.getvalue()}")


# Performance thresholds for critical APIs
CRITICAL_API_THRESHOLDS = {
    "GET_/api/v2/system/status": 100,          # 100ms p95
    "POST_/api/v2/scenarios/create": 500,      # 500ms p95
    "GET_/api/v2/scenarios/list": 200,         # 200ms p95
    "POST_/api/v2/simulations/start": 1000,    # 1s p95 (can be slow)
    "GET_/api/v2/simulations/results": 500,    # 500ms p95
}


def validate_performance_thresholds() -> Tuple[bool, str]:
    """
    Validate that critical APIs meet performance thresholds.
    Should be called after running load tests.
    
    Returns:
        Tuple of (all_pass: bool, report: str)
    """
    profiler = get_profiler()
    success, violations = profiler.validate_thresholds(CRITICAL_API_THRESHOLDS)
    report = profiler.report()
    
    if violations:
        report += "\n\nPerformance Violations:\n"
        report += "\n".join(f"  ✗ {v}" for v in violations)
    else:
        report += "\n\n✓ All performance thresholds met"
    
    return success, report
