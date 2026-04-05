"""
Application service for experiment artifact and publication bundle discovery.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.experiments import ARTIFACTS_EXPERIMENT_DIR, OUTPUT_DIR, ROOT_DIR
from app.experiments.artifact_manifests import (
    build_research_artifact_index,
    build_research_artifact_record,
    is_experiment_run_record,
    is_research_artifact_record,
)
from app.experiments.contracts import (
    EXPERIMENT_SUITE_SUMMARY_VERSION,
    PUBLICATION_BUNDLE_MANIFEST_VERSION,
)
from app.experiments.indexer import build_index
from app.experiments.metrics_export import export_csv


EXPERIMENT_ARTIFACT_CATALOG_VERSION = "peopleflow-experiment-artifact-catalog-v1"
PUBLICATION_BUNDLE_CATALOG_VERSION = "peopleflow-publication-bundle-catalog-v1"


class ExperimentArtifactService:
    def __init__(self) -> None:
        self.output_dir = OUTPUT_DIR
        self.artifact_dir = ARTIFACTS_EXPERIMENT_DIR
        self.paper_results_dir = ROOT_DIR / "artifacts" / "paper_results"

    @staticmethod
    def _load_json(path: Path) -> Optional[Dict[str, Any]]:
        if not path.exists() or not path.is_file():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            return None
        return payload if isinstance(payload, dict) else None

    def _suite_manifests(self) -> List[Dict[str, Any]]:
        manifests: List[Dict[str, Any]] = []
        if not self.output_dir.exists():
            return manifests
        for path in self.output_dir.glob("*.json"):
            payload = self._load_json(path)
            if not payload or payload.get("summary_version") != EXPERIMENT_SUITE_SUMMARY_VERSION:
                continue
            manifests.append(
                {
                    "suite_type": payload.get("suite_type"),
                    "summary_version": payload.get("summary_version"),
                    "run_count": payload.get("run_count"),
                    "generated_at": payload.get("generated_at"),
                    "output_path": payload.get("output_path", str(path)),
                    "source_config_path": payload.get("source_config_path"),
                    "best": payload.get("best"),
                    "metadata": payload.get("metadata", {}),
                }
            )
        manifests.sort(key=lambda item: item.get("generated_at") or "", reverse=True)
        return manifests

    def _artifact_manifest_paths(self) -> List[Path]:
        if not self.output_dir.exists():
            return []
        return sorted(self.output_dir.glob("*.manifest.json"), key=lambda path: path.as_posix())

    def _run_record_paths(self) -> List[Path]:
        if not self.output_dir.exists():
            return []
        return sorted(
            [
                path
                for path in self.output_dir.glob("*.json")
                if path.name not in {"index.json", "artifacts_index.json"} and not path.name.endswith(".manifest.json")
            ],
            key=lambda path: path.as_posix(),
        )

    @staticmethod
    def _summarize_mapping(payload: Dict[str, Any], *, allowed_keys: List[str]) -> Dict[str, Any]:
        summary: Dict[str, Any] = {}
        for key in allowed_keys:
            value = payload.get(key)
            if isinstance(value, (str, int, float, bool)) or value is None:
                if value is not None:
                    summary[key] = value
            elif isinstance(value, list):
                summary[key] = {
                    "count": len(value),
                    "preview": value[:3],
                }
            elif isinstance(value, dict):
                nested = {
                    nested_key: nested_value
                    for nested_key, nested_value in value.items()
                    if isinstance(nested_value, (str, int, float, bool)) or nested_value is None
                }
                if nested:
                    summary[key] = nested
        if not summary and payload:
            summary["field_count"] = len(payload)
            summary["keys"] = sorted(payload.keys())[:8]
        return summary

    def _summarize_artifact_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        artifact_id = str(record.get("artifact_id", "")).strip()
        summary = {
            "record_version": record.get("record_version"),
            "artifact_id": artifact_id,
            "artifact_kind": record.get("artifact_kind"),
            "artifact_type": record.get("artifact_type"),
            "generated_at": record.get("generated_at"),
            "output_path": record.get("output_path"),
            "metadata": self._summarize_mapping(
                record.get("metadata", {}) if isinstance(record.get("metadata"), dict) else {},
                allowed_keys=[
                    "benchmark_name",
                    "suite_name",
                    "bundle_id",
                    "run_count",
                    "validation_enabled",
                    "output_name",
                    "report_name",
                    "simulation_id",
                    "manifest_path",
                    "publication_manifest_version",
                ],
            ),
            "provenance": self._summarize_mapping(
                record.get("provenance", {}) if isinstance(record.get("provenance"), dict) else {},
                allowed_keys=[
                    "generated_at",
                    "suite_name",
                    "run_count",
                    "validation_enabled",
                    "bundle_id",
                    "benchmark_name",
                    "seed",
                    "engine_version",
                ],
            ),
            "detail_path": f"/api/v2/experiments/artifacts/records/{artifact_id}",
            "download_path": f"/api/v2/experiments/artifacts/records/{artifact_id}/download",
        }
        validation = record.get("validation")
        if isinstance(validation, dict):
            summary["validation"] = self._summarize_mapping(
                validation.get("summary", validation) if isinstance(validation, dict) else {},
                allowed_keys=["overall_score", "status", "exit89", "fundamental"],
            )
        return summary

    def _resolve_path_within_allowed_roots(self, path_value: str) -> Path:
        raw = Path(path_value)
        candidate = raw if raw.is_absolute() else (ROOT_DIR / raw)
        resolved = candidate.resolve()
        allowed_roots = [
            ROOT_DIR.resolve(),
            self.output_dir.resolve(),
            self.artifact_dir.resolve(),
            self.paper_results_dir.resolve(),
        ]
        if not any(resolved == root or root in resolved.parents for root in allowed_roots):
            raise LookupError("Artifact path is outside the configured PeopleFlow artifact roots")
        if not resolved.exists() or not resolved.is_file():
            raise LookupError("Artifact file not found")
        return resolved

    def _load_experiment_artifact_record(self, artifact_id: str) -> tuple[Dict[str, Any], Path]:
        normalized_id = artifact_id.strip()
        for manifest_path in self._artifact_manifest_paths():
            manifest = self._load_json(manifest_path)
            if not manifest or not is_research_artifact_record(manifest):
                continue
            if str(manifest.get("artifact_id", "")).strip() == normalized_id:
                return manifest, manifest_path
        raise LookupError("Experiment artifact not found")

    def _collect_experiment_artifact_records(self, *, summarize_records: bool) -> List[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []
        for manifest_path in self._artifact_manifest_paths():
            manifest = self._load_json(manifest_path)
            if not manifest or not is_research_artifact_record(manifest):
                continue
            records.append(self._summarize_artifact_record(manifest) if summarize_records else manifest)
        records.sort(key=lambda item: item.get("generated_at") or "", reverse=True)
        return records

    def _build_experiment_artifact_index(self, *, summarize_records: bool = True) -> Dict[str, Any]:
        artifact_index_path = self.artifact_dir / "artifacts_index.json"
        payload = build_research_artifact_index(
            artifacts=self._collect_experiment_artifact_records(summarize_records=summarize_records),
            source_dir=str(self.output_dir),
            output_path=str(artifact_index_path),
            metadata={
                "artifact_scope": "experiments_output",
                "catalog_version": EXPERIMENT_ARTIFACT_CATALOG_VERSION,
            },
        )
        artifact_index_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_index_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        payload["catalog_version"] = EXPERIMENT_ARTIFACT_CATALOG_VERSION
        return payload

    @staticmethod
    def _bundle_id_from_manifest_path(path: Path) -> str:
        return path.parents[1].name

    def _publication_bundle_record(self, manifest_path: Path, manifest: Dict[str, Any]) -> Dict[str, Any]:
        bundle_id = self._bundle_id_from_manifest_path(manifest_path)
        bundle_dir = manifest_path.parents[1]
        provenance = {
            "generated_at": manifest.get("generated_at"),
            "suite_name": manifest.get("suite_name"),
            "run_count": manifest.get("run_count"),
            "validation_enabled": manifest.get("validation_enabled"),
            "bundle_id": bundle_id,
        }
        metadata = {
            "bundle_id": bundle_id,
            "suite_name": manifest.get("suite_name"),
            "run_count": manifest.get("run_count"),
            "validation_enabled": manifest.get("validation_enabled"),
            "copy_run_outputs": manifest.get("copy_run_outputs"),
            "seeds": manifest.get("seeds", []),
            "variants": manifest.get("variants", []),
            "manifest_path": str(manifest_path),
            "paths": manifest.get("paths", {}),
            "publication_manifest_version": manifest.get("manifest_version"),
        }
        record = build_research_artifact_record(
            artifact_id=f"publication_bundle:{bundle_id}",
            artifact_kind="publication_bundle",
            artifact_type="bundle",
            output_path=str(bundle_dir),
            provenance=provenance,
            metadata=metadata,
            generated_at=manifest.get("generated_at"),
        )
        record["bundle_id"] = bundle_id
        record["detail_path"] = f"/api/v2/experiments/publication-bundles/{bundle_id}"
        record["download_path"] = f"/api/v2/experiments/publication-bundles/{bundle_id}/download"
        return record

    def _publication_manifest_paths(self) -> List[Path]:
        if not self.paper_results_dir.exists():
            return []
        return sorted(
            self.paper_results_dir.glob("*/metadata/publication_manifest.json"),
            key=lambda path: path.as_posix(),
        )

    def _build_publication_bundle_index(self) -> Dict[str, Any]:
        artifacts: List[Dict[str, Any]] = []
        for manifest_path in self._publication_manifest_paths():
            manifest = self._load_json(manifest_path)
            if not manifest or manifest.get("manifest_version") != PUBLICATION_BUNDLE_MANIFEST_VERSION:
                continue
            artifacts.append(self._publication_bundle_record(manifest_path, manifest))

        artifacts.sort(key=lambda item: item.get("generated_at") or "", reverse=True)
        output_path = self.paper_results_dir / "artifacts_index.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = build_research_artifact_index(
            artifacts=artifacts,
            source_dir=str(self.paper_results_dir),
            output_path=str(output_path),
            metadata={
                "artifact_scope": "paper_results",
                "catalog_version": PUBLICATION_BUNDLE_CATALOG_VERSION,
            },
        )
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        payload["catalog_version"] = PUBLICATION_BUNDLE_CATALOG_VERSION
        return payload

    def build_catalog(self) -> Dict[str, Any]:
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        run_index = build_index(output_dir=str(self.output_dir), out_path=str(self.artifact_dir / "index.json"))
        export_manifest = export_csv(
            output_dir=str(self.output_dir),
            csv_path=str(self.artifact_dir / "metrics.csv"),
        )
        artifact_index = self._build_experiment_artifact_index()
        publication_bundles = self._build_publication_bundle_index()
        return {
            "catalog_version": EXPERIMENT_ARTIFACT_CATALOG_VERSION,
            "experiments_output": {
                "output_dir": str(self.output_dir),
                "artifact_dir": str(self.artifact_dir),
                "run_index": run_index,
                "metrics_export": export_manifest,
                "artifact_index": artifact_index,
                "suite_manifests": self._suite_manifests(),
            },
            "publication_bundles": publication_bundles,
        }

    def build_catalog_summary(self) -> Dict[str, Any]:
        run_count = 0
        for path in self._run_record_paths():
            payload = self._load_json(path)
            if payload and is_experiment_run_record(payload):
                run_count += 1

        artifact_count = 0
        for manifest_path in self._artifact_manifest_paths():
            manifest = self._load_json(manifest_path)
            if manifest and is_research_artifact_record(manifest):
                artifact_count += 1

        suite_manifests = self._suite_manifests()

        publication_bundle_count = 0
        for manifest_path in self._publication_manifest_paths():
            manifest = self._load_json(manifest_path)
            if manifest and manifest.get("manifest_version") == PUBLICATION_BUNDLE_MANIFEST_VERSION:
                publication_bundle_count += 1

        return {
            "catalog_version": EXPERIMENT_ARTIFACT_CATALOG_VERSION,
            "run_count": run_count,
            "artifact_count": artifact_count,
            "suite_manifest_count": len(suite_manifests),
            "publication_bundle_count": publication_bundle_count,
        }

    def list_publication_bundles(self) -> Dict[str, Any]:
        return self._build_publication_bundle_index()

    def get_publication_bundle(self, bundle_id: str) -> Dict[str, Any]:
        manifest_path = self.paper_results_dir / bundle_id / "metadata" / "publication_manifest.json"
        manifest = self._load_json(manifest_path)
        if not manifest or manifest.get("manifest_version") != PUBLICATION_BUNDLE_MANIFEST_VERSION:
            raise LookupError("Publication bundle not found")
        return {
            "bundle_id": bundle_id,
            "record": self._publication_bundle_record(manifest_path, manifest),
            "manifest": manifest,
            "manifest_path": str(manifest_path),
            "download_path": f"/api/v2/experiments/publication-bundles/{bundle_id}/download",
        }

    def list_experiment_artifacts(self) -> Dict[str, Any]:
        return self._build_experiment_artifact_index(summarize_records=True)

    def get_experiment_artifact(self, artifact_id: str) -> Dict[str, Any]:
        record, manifest_path = self._load_experiment_artifact_record(artifact_id)
        return {
            "artifact_id": artifact_id,
            "summary": self._summarize_artifact_record(record),
            "record": record,
            "manifest_path": str(manifest_path),
        }

    def resolve_experiment_artifact_download(self, artifact_id: str, *, kind: str = "artifact") -> Path:
        record, manifest_path = self._load_experiment_artifact_record(artifact_id)
        if kind == "manifest":
            return manifest_path.resolve()
        if kind != "artifact":
            raise LookupError("Unsupported artifact download kind")
        output_path = str(record.get("output_path", "")).strip()
        if not output_path:
            raise LookupError("Artifact output path not found")
        return self._resolve_path_within_allowed_roots(output_path)

    def resolve_publication_bundle_download(self, bundle_id: str, *, kind: str = "manifest") -> Path:
        if kind != "manifest":
            raise LookupError("Unsupported publication bundle download kind")
        manifest_path = self.paper_results_dir / bundle_id / "metadata" / "publication_manifest.json"
        manifest = self._load_json(manifest_path)
        if not manifest or manifest.get("manifest_version") != PUBLICATION_BUNDLE_MANIFEST_VERSION:
            raise LookupError("Publication bundle not found")
        return manifest_path.resolve()


experiment_artifact_service = ExperimentArtifactService()
