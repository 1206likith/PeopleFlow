"""
Performance benchmarks and guardrail tests for critical APIs.
"""

import pytest
import time
from contextlib import contextmanager
from typing import Callable
from fastapi.testclient import TestClient
from app.main import app
from app.core.performance_profiling import profile_execution, get_profiler


@contextmanager
def measure_endpoint_performance(client: TestClient, method: str, path: str, 
                                 attempts: int = 5, **kwargs):
    """Context manager to measure endpoint performance."""
    durations = []
    
    for _ in range(attempts):
        start = time.perf_counter()
        
        if method == "GET":
            resp = client.get(path, **kwargs)
        elif method == "POST":
            resp = client.post(path, **kwargs)
        elif method == "PUT":
            resp = client.put(path, **kwargs)
        elif method == "DELETE":
            resp = client.delete(path, **kwargs)
        
        duration = (time.perf_counter() - start) * 1000  # Convert to ms
        durations.append(duration)
    
    yield resp, durations


@pytest.mark.performance
def test_system_status_endpoint_performance(client: TestClient) -> None:
    """Verify /api/v2/system/status meets performance threshold."""
    with measure_endpoint_performance(client, "GET", "/api/v2/system/status", attempts=10) as (resp, durations):
        assert resp.status_code == 200
        
        # Calculate statistics
        avg_ms = sum(durations) / len(durations)
        max_ms = max(durations)
        sorted_durations = sorted(durations)
        p95_ms = sorted_durations[int(len(sorted_durations) * 0.95)]
        
        # Thresholds
        assert p95_ms < 100, f"Status endpoint p95 {p95_ms:.2f}ms exceeds 100ms threshold"
        assert max_ms < 500, f"Status endpoint max {max_ms:.2f}ms exceeds 500ms threshold"
        
        print(f"Status endpoint - avg: {avg_ms:.2f}ms, p95: {p95_ms:.2f}ms, max: {max_ms:.2f}ms")


@pytest.mark.performance
def test_list_scenarios_performance(client: TestClient) -> None:
    """Verify /api/v2/scenarios/list meets performance threshold."""
    with measure_endpoint_performance(client, "GET", "/api/v2/scenarios/list", attempts=5) as (resp, durations):
        if resp.status_code != 404:  # Endpoint may not exist yet
            avg_ms = sum(durations) / len(durations)
            p95_ms = sorted(durations)[int(len(durations) * 0.95)]
            
            assert p95_ms < 200, f"List scenarios p95 {p95_ms:.2f}ms exceeds 200ms threshold"
            print(f"List scenarios - avg: {avg_ms:.2f}ms, p95: {p95_ms:.2f}ms")


@pytest.mark.performance
def test_no_n_plus_one_queries(client: TestClient) -> None:
    """Smoke test to detect potential N+1 query patterns."""
    with profile_execution("list_scenarios_n_plus_one_check"):
        resp = client.get("/api/v2/scenarios/list")
    
    # If this correlates with database calls, we should investigate
    profiler = get_profiler()
    stats = profiler.get_stats("list_scenarios_n_plus_one_check")
    
    if stats:
        # Set warning threshold - if queries take too long, might be N+1
        assert stats.mean_ms < 1000, "List scenarios taking too long, possible N+1 queries"


class BenchmarkData:
    """Benchmark data for performance regression detection."""
    
    # API response time baselines (p95, in ms)
    ENDPOINT_BASELINE = {
        "GET_/api/v2/system/status": 50,
        "GET_/api/v2/scenarios/list": 150,
        "POST_/api/v2/scenarios/create": 400,
    }
    
    # Allow 2x regression before test fails
    REGRESSION_THRESHOLD = 2.0


@pytest.mark.performance
def test_performance_regression_detection(client: TestClient) -> None:
    """Detect performance regressions vs baseline."""
    endpoints = [
        ("GET", "/api/v2/system/status"),
    ]
    
    regressions = []
    
    for method, path in endpoints:
        with measure_endpoint_performance(client, method, path, attempts=10) as (resp, durations):
            if resp.status_code < 400:
                sorted_durations = sorted(durations)
                p95_ms = sorted_durations[int(len(sorted_durations) * 0.95)]
                
                key = f"{method}_{path}"
                if key in BenchmarkData.ENDPOINT_BASELINE:
                    baseline = BenchmarkData.ENDPOINT_BASELINE[key]
                    regression_factor = p95_ms / baseline
                    
                    if regression_factor > BenchmarkData.REGRESSION_THRESHOLD:
                        regressions.append(
                            f"{key}: {p95_ms:.2f}ms vs baseline {baseline}ms "
                            f"({regression_factor:.1f}x slower)"
                        )
    
    if regressions:
        pytest.fail(f"Performance regressions detected:\n" + "\n".join(regressions))
