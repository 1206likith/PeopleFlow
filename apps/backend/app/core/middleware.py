"""
Production-grade middleware for correlation IDs, logging, and security
"""
import json
import gzip
import uuid
import time
import logging
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from typing import Callable
from datetime import datetime, timezone

from app.core.config import settings

logger = logging.getLogger(__name__)


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Add correlation ID to requests for tracing"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate or get correlation ID
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        
        # Add to request state
        request.state.correlation_id = correlation_id
        
        # Add to response headers
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        
        return response


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Structured logging middleware for production"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        correlation_id = getattr(request.state, "correlation_id", "unknown")
        
        # Extract user info if available
        user_id = getattr(request.state, "user_id", None)
        
        # Log request
        logger.info(
            "Request started",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
                "user_id": user_id,
                "client_ip": request.client.host if request.client else None,
            }
        )
        
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # Log response
            logger.info(
                "Request completed",
                extra={
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "process_time": process_time,
                    "user_id": user_id,
                }
            )
            
            # Add process time header
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                "Request failed",
                extra={
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "process_time": process_time,
                    "user_id": user_id,
                },
                exc_info=True
            )
            raise


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to responses"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-site"
        
        # Only add HSTS in production (HTTPS)
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests larger than a configured byte limit."""

    def __init__(self, app: ASGIApp, max_body_size: int):
        super().__init__(app)
        self.max_body_size = max(0, int(max_body_size or 0))

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if self.max_body_size <= 0:
            return await call_next(request)

        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                if length > self.max_body_size:
                    correlation_id = getattr(request.state, "correlation_id", "unknown")
                    return JSONResponse(
                        status_code=413,
                        content={
                            "detail": "Request body too large",
                            "max_bytes": self.max_body_size,
                            "correlation_id": correlation_id,
                        },
                        headers={
                            "X-Request-Max-Bytes": str(self.max_body_size),
                            "X-Correlation-ID": correlation_id,
                        }
                    )
            except ValueError:
                # Malformed Content-Length, continue and let downstream handle
                pass

        return await call_next(request)


class HttpsOnlyMiddleware(BaseHTTPMiddleware):
    """Enforce HTTPS when configured."""

    def __init__(self, app: ASGIApp, enabled: bool):
        super().__init__(app)
        self.enabled = bool(enabled)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self.enabled:
            return await call_next(request)

        # Let CORS preflight requests pass through so browsers can negotiate policy.
        if request.method.upper() == "OPTIONS":
            return await call_next(request)

        forwarded_proto = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip().lower()
        scheme = (forwarded_proto or request.url.scheme or "").lower()
        if scheme != "https":
            correlation_id = getattr(request.state, "correlation_id", "unknown")
            return JSONResponse(
                status_code=400,
                content={
                    "detail": "HTTPS is required for this service",
                    "correlation_id": correlation_id,
                },
                headers={
                    "X-Correlation-ID": correlation_id,
                }
            )
        return await call_next(request)


class AdminKeyMiddleware(BaseHTTPMiddleware):
    """Protect versioned mutation endpoints with a static admin key."""

    _MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
    _EXEMPT_PREFIXES = (
        "/api/v2/docs",
        "/api/v2/redoc",
        "/api/v2/openapi.json",
        "/api/v3/docs",
        "/api/v3/redoc",
        "/api/v3/openapi.json",
    )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        if not settings.ADMIN_KEY_ENABLED:
            return await call_next(request)
        if not (path.startswith("/api/v2") or path.startswith("/api/v3")):
            return await call_next(request)
        if path.startswith(self._EXEMPT_PREFIXES):
            return await call_next(request)
        if request.method not in self._MUTATING_METHODS:
            return await call_next(request)

        correlation_id = getattr(request.state, "correlation_id", "unknown")
        provided = request.headers.get("X-Admin-Key")
        if not provided:
            return JSONResponse(
                status_code=401,
                content={
                    "code": "admin_key_missing",
                    "message": "Missing X-Admin-Key",
                    "details": {"path": path},
                },
                headers={"X-Correlation-ID": correlation_id},
            )
        if provided != settings.ADMIN_API_KEY:
            return JSONResponse(
                status_code=403,
                content={
                    "code": "admin_key_invalid",
                    "message": "Invalid X-Admin-Key",
                    "details": {"path": path},
                },
                headers={"X-Correlation-ID": correlation_id},
            )

        return await call_next(request)


class ApiV1DeprecationMiddleware(BaseHTTPMiddleware):
    """Attach deprecation headers to legacy v1 API paths."""

    _EXEMPT_PATHS = {
        "/api/health",
        "/api/ready",
        "/api/docs",
        "/api/redoc",
        "/api/openapi.json",
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        path = request.url.path
        if path.startswith("/api/") and not path.startswith("/api/v2") and path not in self._EXEMPT_PATHS:
            response.headers["Deprecation"] = "true"
            response.headers["Sunset"] = "2026-06-30"
            response.headers["Link"] = "/api/v2/docs"
        return response


class ApiV2EnvelopeMiddleware(BaseHTTPMiddleware):
    """Wrap versioned JSON responses in a standard envelope."""

    _EXEMPT_PREFIXES = (
        "/api/v2/docs",
        "/api/v2/redoc",
        "/api/v2/openapi.json",
        "/api/v3/docs",
        "/api/v3/redoc",
        "/api/v3/openapi.json",
    )

    def _meta(self, request: Request) -> dict:
        version = "v3" if request.url.path.startswith("/api/v3") else "v2"
        return {
            "version": version,
            "mode": "demo" if settings.IS_DEMO_MODE else "production",
            "path": request.url.path,
            "correlation_id": getattr(request.state, "correlation_id", "unknown"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _normalize_error_payload(payload: object, status_code: int) -> dict:
        if isinstance(payload, dict):
            code = payload.get("code") or f"http_{status_code}"
            message = payload.get("message") or payload.get("detail") or "Request failed"
            details = payload.get("details")
            if details is None:
                details = payload.get("detail")
            return {
                "code": str(code),
                "message": str(message),
                "status_code": int(status_code),
                "details": details,
            }

        if isinstance(payload, str):
            return {
                "code": f"http_{status_code}",
                "message": payload,
                "status_code": int(status_code),
                "details": payload,
            }

        return {
            "code": f"http_{status_code}",
            "message": "Request failed",
            "status_code": int(status_code),
            "details": payload,
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        try:
            response = await call_next(request)
        except Exception as exc:
            logger.exception("Unhandled downstream exception for %s", path, extra={"correlation_id": getattr(request.state, "correlation_id", "unknown")})
            if (path.startswith("/api/v2") or path.startswith("/api/v3")) and not path.startswith(self._EXEMPT_PREFIXES):
                return JSONResponse(
                    status_code=500,
                    content={
                        "meta": self._meta(request),
                        "error": {
                            "code": "internal_error",
                            "message": "Internal server error",
                            "status_code": 500,
                            "details": str(exc) if settings.DEBUG else None,
                        },
                    },
                )
            raise

        if not (path.startswith("/api/v2") or path.startswith("/api/v3")) or path.startswith(self._EXEMPT_PREFIXES):
            return response

        content_type = (response.headers.get("content-type") or "").lower()
        content_disposition = (response.headers.get("content-disposition") or "").lower()
        if "attachment" in content_disposition:
            return response
        if "application/json" not in content_type:
            return response

        body = b""
        async for chunk in response.body_iterator:
            body += chunk

        content_encoding = (response.headers.get("content-encoding") or "").lower()
        if content_encoding == "gzip" and body:
            try:
                body = gzip.decompress(body)
            except Exception:
                pass

        # Fast path for empty JSON responses
        if not body:
            payload = None
        else:
            try:
                payload = json.loads(body.decode("utf-8"))
            except Exception:
                # Rebuild original response body if parsing fails.
                rebuilt = Response(
                    content=body,
                    status_code=response.status_code,
                    media_type=response.media_type,
                )
                for key, value in response.headers.items():
                    if key.lower() not in ("content-length", "content-encoding"):
                        rebuilt.headers[key] = value
                return rebuilt

        if isinstance(payload, dict) and "meta" in payload and ("data" in payload or "error" in payload):
            wrapped = payload
        elif response.status_code >= 400:
            wrapped = {
                "meta": self._meta(request),
                "error": self._normalize_error_payload(payload, response.status_code),
            }
        else:
            wrapped = {"meta": self._meta(request), "data": payload}

        rebuilt = JSONResponse(status_code=response.status_code, content=wrapped)
        for key, value in response.headers.items():
            if key.lower() not in ("content-length", "content-type", "content-encoding"):
                rebuilt.headers[key] = value
        return rebuilt
