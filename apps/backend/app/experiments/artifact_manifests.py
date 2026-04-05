"""
Helpers for writing canonical experiment suite and artifact manifests.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .contracts import (
    EXPERIMENT_RUN_RECORD_VERSION,
    ExperimentExportManifest,
    ExperimentIndexManifest,
    ExperimentSuiteManifest,
    ResearchArtifactIndexManifest,
    ResearchArtifactRecord,
    RESEARCH_ARTIFACT_RECORD_VERSION,
)
from .metadata import build_provenance


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_payload(payload: Dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload or {}, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def is_experiment_run_record(payload: Dict[str, Any]) -> bool:
    if not isinstance(payload, dict):
        return False
    if payload.get("record_version") == EXPERIMENT_RUN_RECORD_VERSION:
        return True
    return isinstance(payload.get("config"), dict) and isinstance(payload.get("metrics"), dict)


def is_research_artifact_record(payload: Dict[str, Any]) -> bool:
    if not isinstance(payload, dict):
        return False
    return payload.get("record_version") == RESEARCH_ARTIFACT_RECORD_VERSION


def build_suite_manifest(
    *,
    suite_type: str,
    base_config_payload: Dict[str, Any],
    results: List[Dict[str, Any]],
    output_path: str,
    source_config_path: Optional[str] = None,
    best: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    provenance = build_provenance(
        base_config_payload,
        config_hash=_hash_payload(base_config_payload),
    ).to_dict()
    provenance.update(
        {
            "suite_type": suite_type,
            "result_count": len(results),
        }
    )
    return ExperimentSuiteManifest(
        suite_type=suite_type,
        generated_at=_now_iso(),
        run_count=len(results),
        source_config_path=source_config_path,
        output_path=output_path,
        provenance=provenance,
        results=results,
        best=best,
        metadata=metadata or {},
    ).to_dict()


def write_suite_manifest(
    *,
    suite_type: str,
    base_config_payload: Dict[str, Any],
    results: List[Dict[str, Any]],
    output_path: Path,
    source_config_path: Optional[str] = None,
    best: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload = build_suite_manifest(
        suite_type=suite_type,
        base_config_payload=base_config_payload,
        results=results,
        output_path=str(output_path),
        source_config_path=source_config_path,
        best=best,
        metadata=metadata,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def build_index_manifest(
    *,
    results: List[Dict[str, Any]],
    source_dir: str,
    output_path: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return ExperimentIndexManifest(
        generated_at=_now_iso(),
        result_count=len(results),
        source_dir=source_dir,
        output_path=output_path,
        results=results,
        metadata=metadata or {},
    ).to_dict()


def build_export_manifest(
    *,
    row_count: int,
    source_dir: str,
    csv_path: str,
    columns: List[str],
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return ExperimentExportManifest(
        generated_at=_now_iso(),
        row_count=row_count,
        source_dir=source_dir,
        csv_path=csv_path,
        columns=columns,
        metadata=metadata or {},
    ).to_dict()


def build_research_artifact_record(
    *,
    artifact_id: str,
    artifact_kind: str,
    artifact_type: str,
    output_path: str,
    provenance: Optional[Dict[str, Any]] = None,
    validation: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    generated_at: Optional[str] = None,
) -> Dict[str, Any]:
    return ResearchArtifactRecord(
        artifact_id=artifact_id,
        artifact_kind=artifact_kind,
        artifact_type=artifact_type,
        generated_at=generated_at or _now_iso(),
        output_path=output_path,
        provenance=provenance or {},
        validation=validation,
        metadata=metadata or {},
    ).to_dict()


def write_research_artifact_record(
    *,
    output_path: Path,
    artifact_id: str,
    artifact_kind: str,
    artifact_type: str,
    artifact_output_path: str,
    provenance: Optional[Dict[str, Any]] = None,
    validation: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    generated_at: Optional[str] = None,
    extra_fields: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload = build_research_artifact_record(
        artifact_id=artifact_id,
        artifact_kind=artifact_kind,
        artifact_type=artifact_type,
        output_path=artifact_output_path,
        provenance=provenance,
        validation=validation,
        metadata=metadata,
        generated_at=generated_at,
    )
    if extra_fields:
        payload.update(extra_fields)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def build_research_artifact_index(
    *,
    artifacts: List[Dict[str, Any]],
    source_dir: str,
    output_path: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return ResearchArtifactIndexManifest(
        generated_at=_now_iso(),
        artifact_count=len(artifacts),
        source_dir=source_dir,
        output_path=output_path,
        artifacts=artifacts,
        metadata=metadata or {},
    ).to_dict()


def write_research_artifact_index(
    *,
    source_dir: Path,
    output_path: Path,
    metadata: Optional[Dict[str, Any]] = None,
    artifact_kind: Optional[str] = None,
    filter_fn: Optional[Callable[[Dict[str, Any]], bool]] = None,
) -> Dict[str, Any]:
    artifacts: List[Dict[str, Any]] = []
    for path in source_dir.glob("*.manifest.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not is_research_artifact_record(payload):
            continue
        if artifact_kind and payload.get("artifact_kind") != artifact_kind:
            continue
        if filter_fn and not filter_fn(payload):
            continue
        artifacts.append(payload)

    artifacts.sort(key=lambda item: item.get("generated_at") or "", reverse=True)
    payload = build_research_artifact_index(
        artifacts=artifacts,
        source_dir=str(source_dir),
        output_path=str(output_path),
        metadata=metadata,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload
