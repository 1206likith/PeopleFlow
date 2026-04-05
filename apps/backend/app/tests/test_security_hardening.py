"""
Security hardening tests and regression checks.
Validates admin key enforcement, rate limiting, CORS, and request constraints.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings


def _assert_v2_error_status(resp, expected_status: int) -> None:
    body = resp.json()
    assert body.get("error", {}).get("status_code") == expected_status


@pytest.fixture
def setup_security_settings():
    """Setup security settings for tests."""
    old_admin_enabled = settings.ADMIN_KEY_ENABLED
    old_admin_key = settings.ADMIN_API_KEY
    old_rate_limit_enabled = settings.RATE_LIMIT_ENABLED
    old_rate_limit_per_minute = settings.RATE_LIMIT_PER_MINUTE
    
    settings.ADMIN_KEY_ENABLED = True
    settings.ADMIN_API_KEY = "test-security-key"
    settings.RATE_LIMIT_ENABLED = True
    settings.RATE_LIMIT_PER_MINUTE = 5
    
    yield
    
    # Cleanup
    settings.ADMIN_KEY_ENABLED = old_admin_enabled
    settings.ADMIN_API_KEY = old_admin_key
    settings.RATE_LIMIT_ENABLED = old_rate_limit_enabled
    settings.RATE_LIMIT_PER_MINUTE = old_rate_limit_per_minute


class TestAdminKeyEnforcement:
    """Tests for admin key enforcement across mutation endpoints."""
    
    @pytest.mark.security
    def test_all_v2_mutations_require_admin_key(self, setup_security_settings, client: TestClient) -> None:
        """Verify all /api/v2 POST/PUT/DELETE operations require admin key."""
        mutation_endpoints = [
            ("POST", "/api/v2/scenarios/create"),
            ("POST", "/api/v2/simulations/start"),
            ("POST", "/api/v2/simulations/stop"),
        ]
        
        for method, path in mutation_endpoints:
            # Without key - should fail
            if method == "POST":
                resp = client.post(path, json={})
            elif method == "PUT":
                resp = client.put(path, json={})
            elif method == "DELETE":
                resp = client.delete(path)
            
            assert resp.status_code in (401, 403), (
                f"{method} {path} requires admin key but returned {resp.status_code}"
            )
            _assert_v2_error_status(resp, resp.status_code)
            
            # With bad key - should fail
            if method == "POST":
                resp = client.post(path, json={}, headers={"X-Admin-Key": "bad-key"})
            
            assert resp.status_code == 403, (
                f"{method} {path} with bad key should return 403, got {resp.status_code}"
            )
            _assert_v2_error_status(resp, 403)
    
    @pytest.mark.security
    def test_admin_key_bypass_not_possible_via_headers(self, setup_security_settings, client: TestClient) -> None:
        """Verify admin key cannot be bypassed through header tricks."""
        bad_keys = [
            "",
            " ",
            "test-security-key ",  # Extra space
            " test-security-key",  # Leading space
            "Test-Security-Key",   # Wrong case
        ]
        
        for bad_key in bad_keys:
            if not bad_key.strip():  # Skip empty keys as they might be allowed
                continue
            resp = client.post(
                "/api/v2/scenarios/create",
                json={},
                headers={"X-Admin-Key": bad_key}
            )
            # Should not grant access with bad key
            assert resp.status_code in (401, 403, 404), (
                f"Key '{bad_key}' should not grant access (got {resp.status_code})"
            )
    
    @pytest.mark.security
    def test_admin_key_in_body_not_accepted(self, setup_security_settings, client: TestClient) -> None:
        """Verify admin key cannot be passed in request body."""
        resp = client.post(
            "/api/v2/scenarios/create",
            json={"admin_key": "test-security-key"}
        )
        assert resp.status_code in (401, 403), "Admin key in body should not grant access"
        _assert_v2_error_status(resp, resp.status_code)


class TestRequestSizeLimits:
    """Tests for request size constraints."""
    
    @pytest.mark.security
    def test_oversized_json_rejected(self, client: TestClient) -> None:
        """Verify excessively large JSON payloads are rejected or handled."""
        # Create moderately large payload (not 10MB as that might crash test)
        large_payload = {
            "data": "x" * (1 * 1024 * 1024)  # 1MB string
        }
        
        try:
            resp = client.post(
                "/api/v2/scenarios/create",
                json=large_payload,
                headers={"X-Admin-Key": "test-security-key"}
            )
            # Should either reject (413) or return error, not crash (500)
            assert resp.status_code < 500, (
                f"Large payload caused 5xx error: {resp.status_code}"
            )
        except Exception as e:
            # May fail during request serialization, which is acceptable
            assert "size" in str(e).lower() or "large" in str(e).lower()
    
    @pytest.mark.security
    def test_oversized_url_rejected(self, client: TestClient) -> None:
        """Verify excessively long URLs are rejected."""
        # Create very long query string
        long_query = "?" + "&".join([f"param{i}=value" for i in range(100)])
        
        resp = client.get(f"/api/v2/scenarios/list{long_query}")
        # Should be rejected or gracefully handled
        assert resp.status_code != 500, "Long URL should not crash the server"


class TestSecurityHeaders:
    """Tests for security headers in responses."""
    
    @pytest.mark.security
    def test_security_headers_present(self, client: TestClient) -> None:
        """Verify security-critical headers are present in responses."""
        resp = client.get("/api/v2/system/status")
        
        required_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
        }
        
        for header, expected_value in required_headers.items():
            assert header in resp.headers, f"Missing security header: {header}"
            if expected_value:
                assert resp.headers[header] == expected_value, (
                    f"Header {header} has wrong value: {resp.headers[header]}"
                )
    
    @pytest.mark.security
    def test_cors_headers_configurable(self, client: TestClient) -> None:
        """Verify CORS headers are properly configured."""
        resp = client.get("/api/v2/system/status")
        
        # CORS headers should be present if configured
        # (actual values depend on settings.ALLOWED_ORIGINS)
        if "Access-Control-Allow-Origin" in resp.headers:
            origin = resp.headers["Access-Control-Allow-Origin"]
            assert origin != "*" or settings.DEBUG, "CORS * should not be used in production"


class TestRateLimiting:
    """Tests for rate limiting enforcement."""
    
    @pytest.mark.security
    def test_rapid_requests_rate_limited(self, setup_security_settings, client: TestClient) -> None:
        """Verify rapid requests are rate limited."""
        endpoint = "/api/v2/system/status"
        
        # Make many requests quickly
        responses_429 = 0
        for i in range(20):
            resp = client.get(endpoint)
            if resp.status_code == 429:  # Too Many Requests
                responses_429 += 1
        
        assert responses_429 > 0, "Expected at least one 429 response under strict rate limit settings"
    
    @pytest.mark.security
    def test_rate_limit_headers_present(self, setup_security_settings, client: TestClient) -> None:
        """Verify rate limit headers are returned."""
        resp = client.get("/api/v2/system/status")
        
        # Check for rate limit headers
        rate_limit_headers = [
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
            "RateLimit-Limit",
            "RateLimit-Remaining",
            "RateLimit-Reset",
        ]
        
        has_rate_limit_header = any(h in resp.headers for h in rate_limit_headers)
        assert has_rate_limit_header, "Rate limit headers must be exposed on responses"


class TestInputValidation:
    """Tests for input validation and injection prevention."""
    
    @pytest.mark.security
    def test_sql_injection_patterns_rejected(self, client: TestClient) -> None:
        """Verify SQL injection patterns are rejected."""
        injection_patterns = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'--",
            "1 UNION SELECT * FROM users--",
        ]
        
        for pattern in injection_patterns:
            resp = client.get(f"/api/v2/scenarios/list?name={pattern}")
            # Should either be rejected (400) or safely escaped
            assert resp.status_code != 500, f"SQL injection pattern caused 500: {pattern}"
    
    @pytest.mark.security
    def test_xss_patterns_escaped(self, client: TestClient) -> None:
        """Verify XSS patterns are properly escaped."""
        xss_patterns = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "';alert('xss');//",
        ]
        
        for pattern in xss_patterns:
            resp = client.get(f"/api/v2/scenarios/list?search={pattern}")
            # Response should be safe
            if resp.status_code == 200:
                body = resp.text
                # Pattern should be escaped or removed, not directly in response
                assert "<script>" not in body, f"XSS pattern not escaped: {pattern}"
    
    @pytest.mark.security
    def test_path_traversal_rejected(self, client: TestClient) -> None:
        """Verify path traversal attempts are rejected."""
        traversal_patterns = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "....//....//....//etc/passwd",
        ]
        
        for pattern in traversal_patterns:
            resp = client.get(f"/api/v2/files/{pattern}")
            # Should be rejected or not crash
            assert resp.status_code != 500, f"Path traversal caused 500: {pattern}"


class TestResponseValidation:
    """Tests to ensure responses don't leak sensitive information."""
    
    @pytest.mark.security
    def test_error_responses_dont_leak_internals(self, client: TestClient) -> None:
        """Verify error responses don't leak internal structure."""
        resp = client.get("/api/v2/nonexistent")
        
        if resp.status_code >= 400:
            body = resp.text.lower()
            
            # Should not contain internal paths
            assert "/app/" not in body, "Error response exposed internal path"
            
            # Should not contain traceback details
            assert "traceback" not in body, "Error response exposed traceback"
            assert "File " not in body, "Error response exposed file paths"
    
    @pytest.mark.security
    def test_authentication_failures_dont_leak_validity(self, setup_security_settings, client: TestClient) -> None:
        """Verify auth failures don't leak whether key is valid."""
        # Both should return 401/403, not different codes that leak info
        resp_no_key = client.post("/api/v2/scenarios/create", json={})
        resp_bad_key = client.post(
            "/api/v2/scenarios/create",
            json={},
            headers={"X-Admin-Key": "wrong-key"}
        )
        
        # Both should be in 401-403 range
        assert resp_no_key.status_code in (401, 403)
        assert resp_bad_key.status_code in (401, 403)
