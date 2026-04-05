"""
Structured logging with simulation/job IDs and RED (Rate, Errors, Duration) metrics.
"""

import json
import logging
import time
import uuid
from typing import Any, Dict, Optional
from dataclasses import dataclass, asdict
from enum import Enum
from functools import wraps
from contextlib import contextmanager

# Structured logging context
_context: Dict[str, Any] = {}


class ErrorTaxonomy(str, Enum):
    """Error classification for structured error tracking."""
    VALIDATION = "validation"          # Input validation failures
    CONFIG = "config"                   # Configuration/initialization errors
    RUNTIME = "runtime"                 # Runtime/logic errors
    EXTERNAL = "external"              # External service failures
    DATABASE = "database"              # Database errors
    AUTHORIZATION = "authorization"    # Auth/permission errors
    NOT_FOUND = "not_found"            # Resource not found
    CONFLICT = "conflict"              # Resource conflict/duplicate


@dataclass
class StructuredLogEvent:
    """Structured log event with context."""
    timestamp: float
    level: str
    message: str
    simulation_id: Optional[str] = None
    job_id: Optional[str] = None
    request_id: Optional[str] = None
    error_type: Optional[ErrorTaxonomy] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    duration_ms: Optional[float] = None
    status_code: Optional[int] = None
    component: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        if data.get("error_type"):
            data["error_type"] = data["error_type"].value
        # Remove None values
        return {k: v for k, v in data.items() if v is not None}


class StructuredLogger:
    """Logger with structured logging support."""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(name)
    
    def _build_event(
        self,
        level: str,
        message: str,
        error_type: Optional[ErrorTaxonomy] = None,
        error_message: Optional[str] = None,
        error_code: Optional[str] = None,
        duration_ms: Optional[float] = None,
        status_code: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> StructuredLogEvent:
        """Build a structured log event."""
        return StructuredLogEvent(
            timestamp=time.time(),
            level=level,
            message=message,
            simulation_id=_context.get("simulation_id"),
            job_id=_context.get("job_id"),
            request_id=_context.get("request_id"),
            error_type=error_type,
            error_message=error_message,
            error_code=error_code,
            duration_ms=duration_ms,
            status_code=status_code,
            component=self.name,
            metadata=metadata,
        )
    
    def info(
        self,
        message: str,
        duration_ms: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log info message."""
        event = self._build_event("INFO", message, duration_ms=duration_ms, metadata=metadata)
        self.logger.info(json.dumps(event.to_dict()))
    
    def error(
        self,
        message: str,
        error_type: ErrorTaxonomy = ErrorTaxonomy.RUNTIME,
        error_message: Optional[str] = None,
        error_code: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log error message."""
        event = self._build_event(
            "ERROR",
            message,
            error_type=error_type,
            error_message=error_message,
            error_code=error_code,
            metadata=metadata,
        )
        self.logger.error(json.dumps(event.to_dict()))
    
    def warning(
        self,
        message: str,
        error_type: Optional[ErrorTaxonomy] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log warning message."""
        event = self._build_event("WARNING", message, error_type=error_type, metadata=metadata)
        self.logger.warning(json.dumps(event.to_dict()))
    
    def debug(
        self,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log debug message."""
        event = self._build_event("DEBUG", message, metadata=metadata)
        self.logger.debug(json.dumps(event.to_dict()))


def set_simulation_id(simulation_id: str) -> None:
    """Set the current simulation ID in context."""
    _context["simulation_id"] = simulation_id


def set_job_id(job_id: str) -> None:
    """Set the current job ID in context."""
    _context["job_id"] = job_id


def set_request_id(request_id: Optional[str] = None) -> str:
    """Set the current request ID in context, generating one if needed."""
    if request_id is None:
        request_id = str(uuid.uuid4())
    _context["request_id"] = request_id
    return request_id


def clear_context() -> None:
    """Clear all context."""
    _context.clear()


@contextmanager
def log_context(
    simulation_id: Optional[str] = None,
    job_id: Optional[str] = None,
    request_id: Optional[str] = None,
):
    """Context manager to temporarily set logging context."""
    old_context = _context.copy()
    
    if simulation_id:
        _context["simulation_id"] = simulation_id
    if job_id:
        _context["job_id"] = job_id
    if request_id:
        _context["request_id"] = request_id
    
    try:
        yield
    finally:
        _context.clear()
        _context.update(old_context)


@dataclass
class REDMetrics:
    """RED metrics for an endpoint or operation."""
    name: str
    request_count: int = 0
    error_count: int = 0
    duration_sum_ms: float = 0.0
    error_types: Dict[str, int] = None
    
    def __post_init__(self):
        if self.error_types is None:
            self.error_types = {}
    
    @property
    def request_rate(self) -> float:
        """Requests per second (average over lifetime)."""
        return self.request_count / max(self.duration_sum_ms / 1000, 1)
    
    @property
    def error_rate(self) -> float:
        """Error rate (0-1)."""
        return self.error_count / max(self.request_count, 1)
    
    @property
    def avg_duration_ms(self) -> float:
        """Average duration in milliseconds."""
        return self.duration_sum_ms / max(self.request_count, 1)
    
    def record_request(self, duration_ms: float, error_type: Optional[str] = None) -> None:
        """Record a request."""
        self.request_count += 1
        self.duration_sum_ms += duration_ms
        
        if error_type:
            self.error_count += 1
            self.error_types[error_type] = self.error_types.get(error_type, 0) + 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "request_count": self.request_count,
            "error_count": self.error_count,
            "error_rate": self.error_rate,
            "request_rate": self.request_rate,
            "avg_duration_ms": self.avg_duration_ms,
            "error_types": self.error_types,
        }


class REDMetricsCollector:
    """Collects RED metrics for observability dashboard."""
    
    def __init__(self):
        self.metrics: Dict[str, REDMetrics] = {}
    
    def get_or_create(self, name: str) -> REDMetrics:
        """Get or create metrics for a name."""
        if name not in self.metrics:
            self.metrics[name] = REDMetrics(name)
        return self.metrics[name]
    
    def record_endpoint(
        self,
        endpoint: str,
        duration_ms: float,
        error_type: Optional[str] = None,
    ) -> None:
        """Record endpoint call."""
        metrics = self.get_or_create(f"endpoint:{endpoint}")
        metrics.record_request(duration_ms, error_type)
    
    def record_database_operation(
        self,
        operation: str,
        duration_ms: float,
        error_type: Optional[str] = None,
    ) -> None:
        """Record database operation."""
        metrics = self.get_or_create(f"db:{operation}")
        metrics.record_request(duration_ms, error_type)
    
    def record_external_service(
        self,
        service: str,
        duration_ms: float,
        error_type: Optional[str] = None,
    ) -> None:
        """Record external service call."""
        metrics = self.get_or_create(f"external:{service}")
        metrics.record_request(duration_ms, error_type)
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get all metrics."""
        return {name: metrics.to_dict() for name, metrics in self.metrics.items()}
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get health summary of all metrics."""
        total_requests = sum(m.request_count for m in self.metrics.values())
        total_errors = sum(m.error_count for m in self.metrics.values())
        
        return {
            "total_requests": total_requests,
            "total_errors": total_errors,
            "overall_error_rate": total_errors / max(total_requests, 1),
            "monitored_operations": len(self.metrics),
        }


# Global metrics collector
_metrics_collector = REDMetricsCollector()


def get_metrics_collector() -> REDMetricsCollector:
    """Get the global metrics collector."""
    return _metrics_collector


def get_structured_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance."""
    return StructuredLogger(name)
