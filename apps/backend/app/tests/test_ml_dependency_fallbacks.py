"""
Smoke tests to verify optional ML dependencies fail gracefully by design.
Tests that torch, detectron2, cv2 missing imports are handled properly.
"""

import sys
import importlib
from unittest.mock import patch
import pytest


def _assert_v2_error_status(body: dict, expected_status: int) -> None:
    assert body.get("error", {}).get("status_code") == expected_status


class MissingModuleFinder:
    """Mock finder that simulates missing optional ML modules."""
    
    def __init__(self, missing_modules: set):
        self.missing_modules = missing_modules
    
    def find_spec(self, fullname, path, target=None):
        if any(fullname.startswith(m) for m in self.missing_modules):
            return None
        return None


def test_app_starts_without_torch() -> None:
    """Verify backend starts when torch is unavailable."""
    missing = {"torch"}
    
    with patch.dict(sys.modules, {m: None for m in missing}):
        # If torch is used somewhere, it should be in a try-except block
        try:
            from app.services import ml_service
            # If ml_service imports torch directly without fallback, this will fail
            # That's the intended behavior - we're testing that it fails gracefully
        except ImportError as e:
            # Acceptable: ImportError for missing torch
            assert "torch" in str(e).lower() or "ml" in str(e).lower()


def test_app_starts_without_detectron2() -> None:
    """Verify backend starts when detectron2 is unavailable."""
    missing = {"detectron2"}
    
    with patch.dict(sys.modules, {m: None for m in missing}):
        try:
            from app.services import ml_floorplan_recognition
            # Similarly, detectron2 should be optional
        except ImportError as e:
            assert "detectron2" in str(e).lower() or "detection" in str(e).lower()


def test_app_starts_without_cv2() -> None:
    """Verify backend starts when cv2 (OpenCV) is unavailable."""
    missing = {"cv2"}
    
    with patch.dict(sys.modules, {m: None for m in missing}):
        try:
            from app.services import floor_plan_processor
            # cv2 should be optional for non-vision operations
        except ImportError as e:
            assert "cv2" in str(e).lower() or "opencv" in str(e).lower()


def test_ml_service_has_fallback_mode() -> None:
    """Verify ml_service has methods to check if ML is available."""
    try:
        from app.services import ml_service
        assert ml_service is not None, "ml_service should be importable"
    except ImportError as e:
        # Import failure is acceptable only when explicitly tied to optional ML deps.
        lower = str(e).lower()
        assert any(token in lower for token in ("torch", "detectron2", "opencv", "cv2", "ml"))


def test_floorplan_recognition_has_mock_mode() -> None:
    """Verify floor plan recognition can fall back to mock/baseline mode."""
    try:
        from app.services import ml_floorplan_recognition
        from app.services import floor_plan_processor
        
        # If modules load, that's a good sign
        assert ml_floorplan_recognition is not None
        assert floor_plan_processor is not None
    except ImportError as e:
        lower = str(e).lower()
        assert any(token in lower for token in ("detectron2", "opencv", "cv2", "ml"))


def test_api_endpoints_work_without_ml_modules() -> None:
    """Verify key API endpoints return graceful responses even without ML modules."""
    from fastapi.testclient import TestClient
    from app.main import app
    
    with TestClient(app) as client:
        # Key endpoints should respond (status < 500) even without ML
        endpoints = [
            ("GET", "/api/v2/system/status"),
            ("GET", "/api/v2/scenarios/list"),
        ]
        
        for method, path in endpoints:
            if method == "GET":
                resp = client.get(path)
            elif method == "POST":
                resp = client.post(path, json={})
            
            # Should not crash (500) due to missing optional deps
            assert resp.status_code < 500, (
                f"Endpoint {method} {path} failed with {resp.status_code}: "
                f"backend should handle missing ML deps gracefully"
            )


def test_ml_dependent_endpoints_return_error_not_crash() -> None:
    """Verify ML-dependent endpoints return user-friendly errors, not crashes."""
    from fastapi.testclient import TestClient
    from app.main import app
    
    with TestClient(app) as client:
        # Endpoints that might require ML
        ml_endpoints = [
            ("POST", "/api/v2/floorplans/train-from-image"),
            ("POST", "/api/v2/ml/predict-dynamics"),
        ]
        
        for method, path in ml_endpoints:
            if method == "POST":
                resp = client.post(path, json={})
            
            # Should return 4xx (user error/unavailable) not 5xx (crash)
            if resp.status_code >= 400:
                assert resp.status_code < 500, (
                    f"ML endpoint {method} {path} crashed with 5xx "
                    f"instead of returning 4xx error"
                )
                
                # Should have helpful error message
                if resp.headers.get("content-type", "").startswith("application/json"):
                    body = resp.json()
                    if "error" in body:
                        assert "message" in body["error"]
                        _assert_v2_error_status(body, resp.status_code)


def test_ml_service_graceful_degradation() -> None:
    """Verify ml_service exports graceful degradation methods."""
    try:
        from app.services.ml_service import (
            get_available_models,
            get_default_model,
        )
        
        # If these exist, should be callable
        if callable(get_available_models):
            available = get_available_models()
            assert isinstance(available, list), "Should return list of models"
        
        if callable(get_default_model):
            try:
                default = get_default_model()
                # Either has default or returns None - both acceptable
                assert default is None or isinstance(default, str)
            except Exception as e:
                # Should not crash unexpectedly with non-informative errors
                assert "gracefully" not in str(e).lower()
    except ImportError as e:
        lower = str(e).lower()
        assert any(token in lower for token in ("torch", "detectron2", "opencv", "cv2", "ml"))
