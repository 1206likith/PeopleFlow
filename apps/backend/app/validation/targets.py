"""
Validation target loader.
"""
from __future__ import annotations

from typing import Dict, Any

from app.validation.benchmark_registry import load_validation_targets


def load_targets(path: str = None) -> Dict[str, Any]:
    return load_validation_targets(path)
