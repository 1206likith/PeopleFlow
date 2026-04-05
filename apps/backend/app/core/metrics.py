"""
Prometheus metrics for production monitoring
"""
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# Request metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# Simulation metrics
simulations_started_total = Counter(
    'simulations_started_total',
    'Total simulations started',
    ['emergency_type']
)

simulations_completed_total = Counter(
    'simulations_completed_total',
    'Total simulations completed',
    ['emergency_type', 'status']
)

simulation_agents_total = Histogram(
    'simulation_agents_total',
    'Number of agents per simulation',
    buckets=[10, 50, 100, 200, 500, 1000, 2000, 5000, 10000]
)

simulation_duration_seconds = Histogram(
    'simulation_duration_seconds',
    'Simulation duration in seconds',
    buckets=[10, 30, 60, 120, 300, 600, 1800, 3600]
)

# WebSocket metrics
websocket_connections_active = Gauge(
    'websocket_connections_active',
    'Active WebSocket connections'
)

websocket_messages_total = Counter(
    'websocket_messages_total',
    'Total WebSocket messages',
    ['message_type']
)

# Database metrics
database_operations_total = Counter(
    'database_operations_total',
    'Total database operations',
    ['operation', 'collection']
)

database_operation_duration_seconds = Histogram(
    'database_operation_duration_seconds',
    'Database operation duration',
    ['operation', 'collection'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
)

database_operation_errors_total = Counter(
    'database_operation_errors_total',
    'Database operation errors',
    ['operation', 'collection']
)

# File upload metrics
file_uploads_total = Counter(
    'file_uploads_total',
    'Total file uploads',
    ['file_type', 'status']
)

file_upload_size_bytes = Histogram(
    'file_upload_size_bytes',
    'File upload size in bytes',
    buckets=[1024, 10240, 102400, 1048576, 10485760]  # 1KB to 10MB
)

# Feature flag / audit metrics
feature_flags_changes_total = Counter(
    'feature_flags_changes_total',
    'Feature flag changes',
    ['flag', 'enabled', 'source']
)

feature_flags_active_total = Gauge(
    'feature_flags_active_total',
    'Active feature flags by category',
    ['category']
)

audit_events_total = Counter(
    'audit_events_total',
    'Audit events recorded',
    ['action', 'severity']
)

# Frame ingestion metrics
simulation_frames_ingested_total = Counter(
    'simulation_frames_ingested_total',
    'Simulation frames ingested',
    ['status']
)

# Floor plan processing metrics
floorplan_processing_total = Counter(
    'floorplan_processing_total',
    'Total floor plan processing runs',
    ['pipeline', 'status']
)

floorplan_processing_duration_seconds = Histogram(
    'floorplan_processing_duration_seconds',
    'Floor plan processing duration in seconds',
    ['pipeline'],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

floorplan_quality_score = Histogram(
    'floorplan_quality_score',
    'Floor plan quality score (0-1)',
    buckets=[0.0, 0.25, 0.5, 0.75, 0.9, 1.0]
)

floorplan_wall_count = Histogram(
    'floorplan_wall_count',
    'Detected wall count per floor plan',
    buckets=[0, 5, 10, 25, 50, 100, 200, 500]
)

floorplan_exit_count = Histogram(
    'floorplan_exit_count',
    'Detected exit count per floor plan',
    buckets=[0, 1, 2, 3, 5, 8, 13, 21, 34]
)

# Idempotency + cache metrics
idempotency_replays_total = Counter(
    'idempotency_replays_total',
    'Idempotency replay responses',
    ['endpoint']
)

floorplan_processing_cache_total = Counter(
    'floorplan_processing_cache_total',
    'Floor plan processing cache usage',
    ['source', 'status']
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect HTTP metrics"""

    @staticmethod
    def _endpoint_label(request: Request) -> str:
        route = request.scope.get("route")
        route_path = getattr(route, "path", None)
        if route_path:
            return str(route_path)
        return request.url.path
    
    async def dispatch(self, request: Request, call_next):
        import time
        start_time = time.time()
        
        endpoint = self._endpoint_label(request)
        
        response = await call_next(request)
        
        duration = time.time() - start_time
        
        # Record metrics
        http_requests_total.labels(
            method=request.method,
            endpoint=endpoint,
            status_code=response.status_code
        ).inc()
        
        http_request_duration_seconds.labels(
            method=request.method,
            endpoint=endpoint
        ).observe(duration)
        
        return response


def get_metrics():
    """Get Prometheus metrics"""
    return generate_latest()

