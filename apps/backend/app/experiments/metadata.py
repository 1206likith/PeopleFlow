"""
Experiment metadata utilities for reproducibility.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
import platform
import subprocess
from typing import Any, Dict, Optional

from app.core.config import settings
from .contracts import ExperimentProvenance


def _safe_git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        return None
    return None


@dataclass
class ExperimentMetadata:
    generated_at: str
    git_commit: str | None
    python_version: str
    platform: str
    hostname: str | None
    app_mode: str
    service_version: str
    engine: Optional[str] = None
    engine_version: Optional[str] = None
    seed: Optional[int] = None
    floor_plan_id: Optional[str] = None
    floor_plan_revision: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "generated_at": self.generated_at,
            "git_commit": self.git_commit,
            "python_version": self.python_version,
            "platform": self.platform,
            "hostname": self.hostname,
            "app_mode": self.app_mode,
            "service_version": self.service_version,
        }
        if self.engine is not None:
            payload["engine"] = self.engine
        if self.engine_version is not None:
            payload["engine_version"] = self.engine_version
        if self.seed is not None:
            payload["seed"] = self.seed
        if self.floor_plan_id is not None:
            payload["floor_plan_id"] = self.floor_plan_id
        if self.floor_plan_revision is not None:
            payload["floor_plan_revision"] = self.floor_plan_revision
        return payload


def build_metadata(
    config: Optional[Dict[str, Any]] = None,
    *,
    floor_plan_revision: Optional[str] = None,
    engine_version: Optional[str] = "peopleflow-sim-v1",
) -> ExperimentMetadata:
    config = config or {}
    return ExperimentMetadata(
        generated_at=datetime.now(timezone.utc).isoformat(),
        git_commit=_safe_git_commit(),
        python_version=platform.python_version(),
        platform=platform.platform(),
        hostname=os.environ.get("COMPUTERNAME") or os.environ.get("HOSTNAME"),
        app_mode=settings.APP_MODE,
        service_version=settings.SERVICE_VERSION,
        engine=config.get("engine"),
        engine_version=engine_version,
        seed=config.get("seed"),
        floor_plan_id=config.get("floor_plan_id"),
        floor_plan_revision=floor_plan_revision,
    )


def build_provenance(
    config: Optional[Dict[str, Any]] = None,
    *,
    config_hash: Optional[str] = None,
    floor_plan_revision: Optional[str] = None,
    engine_version: Optional[str] = "peopleflow-sim-v1",
) -> ExperimentProvenance:
    config = config or {}
    metadata = build_metadata(
        config,
        floor_plan_revision=floor_plan_revision,
        engine_version=engine_version,
    )
    run_metadata = config.get("metadata") if isinstance(config.get("metadata"), dict) else {}
    publication_metadata = (
        run_metadata.get("publication")
        if isinstance(run_metadata.get("publication"), dict)
        else {}
    )
    return ExperimentProvenance(
        generated_at=metadata.generated_at,
        git_commit=metadata.git_commit,
        python_version=metadata.python_version,
        platform=metadata.platform,
        hostname=metadata.hostname,
        app_mode=metadata.app_mode,
        service_version=metadata.service_version,
        engine=metadata.engine,
        engine_version=metadata.engine_version,
        seed=metadata.seed,
        floor_plan_id=metadata.floor_plan_id,
        floor_plan_revision=metadata.floor_plan_revision,
        config_hash=config_hash,
        config_snapshot=dict(config),
        run_metadata=dict(run_metadata),
        publication_metadata=dict(publication_metadata),
    )
