"""
Experiment result data model and helpers.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, Optional

from .contracts import EXPERIMENT_RUN_RECORD_VERSION


@dataclass
class ExperimentResult:
    config: Dict[str, Any]
    config_hash: str
    metrics: Dict[str, Any]
    metadata: Dict[str, Any]
    provenance: Dict[str, Any] = field(default_factory=dict)
    validation: Optional[Dict[str, Any]] = None
    artifacts: Dict[str, Any] = field(default_factory=dict)
    record_version: str = EXPERIMENT_RUN_RECORD_VERSION

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "record_version": self.record_version,
            "config": self.config,
            "config_hash": self.config_hash,
            "metrics": self.metrics,
            "metadata": self.metadata,
            "provenance": self.provenance,
            "artifacts": self.artifacts,
        }
        if self.validation is not None:
            payload["validation"] = self.validation
        return payload
