"""
Canonical research contracts for reproducible experiment outputs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


EXPERIMENT_RUN_RECORD_VERSION = "peopleflow-experiment-run-v1"
PUBLICATION_BUNDLE_MANIFEST_VERSION = "peopleflow-publication-bundle-v1"
EXPERIMENT_SUITE_SUMMARY_VERSION = "peopleflow-experiment-suite-v1"
EXPERIMENT_INDEX_MANIFEST_VERSION = "peopleflow-experiment-index-v1"
EXPERIMENT_EXPORT_MANIFEST_VERSION = "peopleflow-experiment-export-v1"
RESEARCH_ARTIFACT_RECORD_VERSION = "peopleflow-research-artifact-v1"
RESEARCH_ARTIFACT_INDEX_MANIFEST_VERSION = "peopleflow-research-artifact-index-v1"


@dataclass
class ExperimentProvenance:
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
    config_hash: Optional[str] = None
    config_snapshot: Dict[str, Any] = field(default_factory=dict)
    run_metadata: Dict[str, Any] = field(default_factory=dict)
    publication_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "generated_at": self.generated_at,
            "git_commit": self.git_commit,
            "python_version": self.python_version,
            "platform": self.platform,
            "hostname": self.hostname,
            "app_mode": self.app_mode,
            "service_version": self.service_version,
            "config_snapshot": self.config_snapshot,
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
        if self.config_hash is not None:
            payload["config_hash"] = self.config_hash
        if self.run_metadata:
            payload["run_metadata"] = self.run_metadata
        if self.publication_metadata:
            payload["publication_metadata"] = self.publication_metadata
        return payload


@dataclass
class ExperimentRunRecord:
    config: Dict[str, Any]
    config_hash: str
    metrics: Dict[str, Any]
    metadata: Dict[str, Any]
    provenance: Dict[str, Any]
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


@dataclass
class PublicationBundleManifest:
    layout_version: str
    suite_name: str
    generated_at: str
    run_count: int
    validation_enabled: bool
    copy_run_outputs: bool
    copied_run_count: int
    missing_run_outputs: List[str]
    seeds: List[int]
    variants: List[str]
    paths: Dict[str, str]
    runs: List[Dict[str, Any]] = field(default_factory=list)
    manifest_version: str = PUBLICATION_BUNDLE_MANIFEST_VERSION
    run_record_version: str = EXPERIMENT_RUN_RECORD_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "manifest_version": self.manifest_version,
            "run_record_version": self.run_record_version,
            "layout_version": self.layout_version,
            "suite_name": self.suite_name,
            "generated_at": self.generated_at,
            "run_count": self.run_count,
            "validation_enabled": self.validation_enabled,
            "copy_run_outputs": self.copy_run_outputs,
            "copied_run_count": self.copied_run_count,
            "missing_run_outputs": self.missing_run_outputs,
            "seeds": self.seeds,
            "variants": self.variants,
            "paths": self.paths,
            "runs": self.runs,
        }


@dataclass
class ExperimentSuiteManifest:
    suite_type: str
    generated_at: str
    run_count: int
    source_config_path: Optional[str]
    output_path: str
    provenance: Dict[str, Any]
    results: List[Dict[str, Any]] = field(default_factory=list)
    best: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    summary_version: str = EXPERIMENT_SUITE_SUMMARY_VERSION
    run_record_version: str = EXPERIMENT_RUN_RECORD_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary_version": self.summary_version,
            "run_record_version": self.run_record_version,
            "suite_type": self.suite_type,
            "generated_at": self.generated_at,
            "run_count": self.run_count,
            "source_config_path": self.source_config_path,
            "output_path": self.output_path,
            "provenance": self.provenance,
            "best": self.best,
            "results": self.results,
            "metadata": self.metadata,
        }


@dataclass
class ExperimentIndexManifest:
    generated_at: str
    result_count: int
    source_dir: str
    output_path: str
    results: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    manifest_version: str = EXPERIMENT_INDEX_MANIFEST_VERSION
    run_record_version: str = EXPERIMENT_RUN_RECORD_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "manifest_version": self.manifest_version,
            "run_record_version": self.run_record_version,
            "generated_at": self.generated_at,
            "result_count": self.result_count,
            "source_dir": self.source_dir,
            "output_path": self.output_path,
            "metadata": self.metadata,
            "results": self.results,
        }


@dataclass
class ExperimentExportManifest:
    generated_at: str
    row_count: int
    source_dir: str
    csv_path: str
    columns: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    manifest_version: str = EXPERIMENT_EXPORT_MANIFEST_VERSION
    run_record_version: str = EXPERIMENT_RUN_RECORD_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "manifest_version": self.manifest_version,
            "run_record_version": self.run_record_version,
            "generated_at": self.generated_at,
            "row_count": self.row_count,
            "source_dir": self.source_dir,
            "csv_path": self.csv_path,
            "columns": self.columns,
            "metadata": self.metadata,
        }


@dataclass
class ResearchArtifactRecord:
    artifact_id: str
    artifact_kind: str
    artifact_type: str
    generated_at: str
    output_path: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    provenance: Dict[str, Any] = field(default_factory=dict)
    validation: Optional[Dict[str, Any]] = None
    record_version: str = RESEARCH_ARTIFACT_RECORD_VERSION

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "record_version": self.record_version,
            "artifact_id": self.artifact_id,
            "artifact_kind": self.artifact_kind,
            "artifact_type": self.artifact_type,
            "generated_at": self.generated_at,
            "output_path": self.output_path,
            "metadata": self.metadata,
            "provenance": self.provenance,
        }
        if self.validation is not None:
            payload["validation"] = self.validation
        return payload


@dataclass
class ResearchArtifactIndexManifest:
    generated_at: str
    artifact_count: int
    source_dir: str
    output_path: str
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    manifest_version: str = RESEARCH_ARTIFACT_INDEX_MANIFEST_VERSION
    record_version: str = RESEARCH_ARTIFACT_RECORD_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "manifest_version": self.manifest_version,
            "record_version": self.record_version,
            "generated_at": self.generated_at,
            "artifact_count": self.artifact_count,
            "source_dir": self.source_dir,
            "output_path": self.output_path,
            "metadata": self.metadata,
            "artifacts": self.artifacts,
        }
