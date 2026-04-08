"""
Rate limiting for production API protection
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from typing import Dict
import time
import logging
from collections import defaultdict
from app.core.config import settings

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting (use Redis in production)"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.requests: Dict[str, list] = defaultdict(list)
        self.cleanup_interval = 60  # Clean up old entries every 60 seconds
        self.last_cleanup = time.time()
    
    def _get_client_id(self, request: Request) -> str:
        """Get client identifier for rate limiting"""
        actor_id = request.headers.get("X-Actor-ID", "").strip()
        if actor_id:
            return f"actor:{actor_id}"

        # Use user ID if authenticated, otherwise fallback to IP
        if hasattr(request.state, "user_id") and request.state.user_id:
            return f"user:{request.state.user_id}"
        return f"ip:{request.client.host if request.client else 'unknown'}"
    
    def _evaluate_rate_limit(self, client_id: str, limit: int, window: int = 60) -> tuple[bool, int, int]:
        """Return rate limit state as (is_limited, remaining, reset_epoch_seconds)."""
        now = time.time()
        
        # Clean up old entries periodically
        if now - self.last_cleanup > self.cleanup_interval:
            self._cleanup_old_entries(now - window)
            self.last_cleanup = now
        
        # Get requests in time window
        client_requests = self.requests[client_id]
        window_start = now - window
        
        # Remove old requests
        client_requests[:] = [req_time for req_time in client_requests if req_time > window_start]
        
        if client_requests:
            reset_at = int(client_requests[0] + window)
        else:
            reset_at = int(now + window)

        # Check limit
        if len(client_requests) >= limit:
            return True, 0, reset_at

        # Add current request
        client_requests.append(now)
        remaining = max(0, limit - len(client_requests))
        reset_after_append = int(client_requests[0] + window)
        return False, remaining, reset_after_append
    
    def _cleanup_old_entries(self, cutoff_time: float):
        """Remove old entries to prevent memory leak"""
        for client_id in list(self.requests.keys()):
            self.requests[client_id] = [
                req_time for req_time in self.requests[client_id]
                if req_time > cutoff_time
            ]
            if not self.requests[client_id]:
                del self.requests[client_id]
    
    async def dispatch(self, request: Request, call_next):
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)
        
        client_id = self._get_client_id(request)
        path = request.url.path
        
        # Different limits for mutating and read-heavy paths can be added later.
        # For now use a single policy for all routes.
        limit = settings.RATE_LIMIT_PER_MINUTE
        
        is_limited, remaining, reset_at = self._evaluate_rate_limit(client_id, limit)
        if is_limited:
            logger.warning(
                "Rate limit exceeded",
                extra={
                    "client_id": client_id,
                    "path": path,
                    "limit": limit,
                }
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": f"Rate limit exceeded. Maximum {limit} requests per minute."},
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_at),
                    "RateLimit-Limit": str(limit),
                    "RateLimit-Remaining": "0",
                    "RateLimit-Reset": str(reset_at),
                }
            )
        
        try:
            response = await call_next(request)
            
            # Add rate limit headers
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
            response.headers["X-RateLimit-Reset"] = str(reset_at)
            response.headers["RateLimit-Limit"] = str(limit)
            response.headers["RateLimit-Remaining"] = str(max(0, remaining))
            response.headers["RateLimit-Reset"] = str(reset_at)
            
            return response
        except Exception:
            # Don't block on errors, just pass through
            raise

