"""
Application service for batch simulation orchestration and persistence.
"""
from __future__ import annotations

import csv
import io
import json
import random
import statistics
import time
import uuid
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder

from app.experiments.metadata import build_provenance
from app.services.audit_log import record_event
from app.services.batch_repository import get_batch_repository
from app.validation.normalization import build_structured_validation_report


BATCH_RECORD_VERSION = "peopleflow-batch-run-v1"


def _safe_audit(
    action: str,
    actor: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    severity: str = "info",
) -> None:
    try:
        record_event(action=action, actor=actor, metadata=metadata, severity=severity)
    except Exception:
        pass


class SimulationBatchApplicationService:
    async def fetch_batch_doc(self, batch_id: str) -> Optional[dict]:
        if not batch_id:
            return None
        repository = await get_batch_repository()
        return await repository.get(batch_id)

    async def persist_batch_doc(self, doc: dict) -> None:
        batch_id = doc.get("batch_id")
        if not batch_id:
            return
        repository = await get_batch_repository()
        await repository.save(batch_id, doc)

    async def list_batch_docs(self, skip: int, limit: int) -> List[dict]:
        repository = await get_batch_repository()
        return await repository.list(skip=skip, limit=limit)

    def normalize_batch_doc(self, batch_doc: Optional[dict]) -> Optional[dict]:
        if not batch_doc:
            return batch_doc
        normalized = dict(batch_doc)
        if normalized.get("_id"):
            normalized["id"] = str(normalized["_id"])
            del normalized["_id"]
        return self._ensure_batch_research_contracts(normalized)

    async def get_batch_doc_or_404(self, batch_id: str) -> dict:
        batch_doc = await self.fetch_batch_doc(batch_id)
        if not batch_doc:
            raise HTTPException(status_code=404, detail="Batch not found")
        normalized = self.normalize_batch_doc(batch_doc)
        if not normalized:
            raise HTTPException(status_code=404, detail="Batch not found")
        return normalized

    async def run_batch_simulation(self, batch: Any, user_id: str) -> dict:
        from app.services.floorplan_loader import load_floor_plan_data
        from app.services.mock_simulation import run_mock_simulation

        base_config = batch.config
        emergency_type_value = (
            base_config.emergency_type.value
            if hasattr(base_config.emergency_type, "value")
            else str(base_config.emergency_type)
        )

        hazards = [
            h.model_dump() if hasattr(h, "model_dump") else h.dict()
            for h in (base_config.hazards or [])
        ]
        agent_profiles = [
            p.model_dump() if hasattr(p, "model_dump") else p.dict()
            for p in (base_config.agent_profiles or [])
        ]
        blocked_exits = list(base_config.blocked_exits or [])
        parameter_overrides = dict(base_config.parameter_overrides or {})
        ablation = (
            base_config.ablation.model_dump()
            if hasattr(base_config.ablation, "model_dump")
            else (base_config.ablation or None)
        )

        floor_plan_data, exits = await load_floor_plan_data(
            base_config.floor_plan_id,
            base_config.floor_number,
            base_config.exits,
        )
        base_config_payload = jsonable_encoder(base_config)

        batch_id = f"batch-{uuid.uuid4().hex[:10]}"
        results = []
        start_time = time.perf_counter()

        for index in range(batch.runs):
            if batch.seed_start is not None:
                seed = batch.seed_start + index * batch.seed_step
            elif base_config.seed is not None:
                seed = base_config.seed + index * batch.seed_step
            else:
                seed = random.randint(0, 2**31 - 1)

            simulation_id = f"{batch_id}-run-{index + 1}"
            summary = await run_mock_simulation(
                simulation_id=simulation_id,
                num_agents=base_config.num_agents,
                emergency_type=emergency_type_value,
                callback=None,
                floor_number=base_config.floor_number or 1,
                exits=exits,
                floor_plan_data=floor_plan_data,
                seed=seed,
                hazards=hazards,
                agent_profiles=agent_profiles,
                blocked_exits=blocked_exits,
                parameter_overrides=parameter_overrides,
                ablation=ablation,
                realtime=batch.realtime,
                return_summary=True,
                max_iterations=batch.max_iterations or 1000,
                max_runtime_seconds=base_config.max_runtime_seconds,
            )
            summary["seed"] = seed
            results.append(summary)

        duration = time.perf_counter() - start_time
        created_at = datetime.now(timezone.utc)
        aggregate = self._build_aggregate(results)
        status_counts = self._count_statuses(results)
        run_manifest = self._build_run_manifest(results)
        seeds = [int(item["seed"]) for item in run_manifest if item.get("seed") is not None]
        config_hash = self._hash_config(base_config_payload)
        provenance = self._build_batch_provenance(
            batch_id=batch_id,
            base_config_payload=base_config_payload,
            config_hash=config_hash,
            user_id=user_id,
            mode="realtime" if batch.realtime else "fast",
            runtime_seconds=duration,
            seeds=seeds,
            created_at=created_at,
            floor_plan_data=floor_plan_data if isinstance(floor_plan_data, dict) else None,
        )
        validation = self._build_batch_validation(
            batch_id=batch_id,
            run_manifest=run_manifest,
            aggregate=aggregate,
            runtime_seconds=duration,
        )

        batch_doc = {
            "record_version": BATCH_RECORD_VERSION,
            "batch_id": batch_id,
            "tenant_id": "global",
            "runs": batch.runs,
            "mode": "realtime" if batch.realtime else "fast",
            "runtime_seconds": duration,
            "status_counts": status_counts,
            "aggregate": aggregate,
            "run_manifest": run_manifest,
            "results": results,
            "user_id": user_id,
            "base_config": base_config_payload,
            "provenance": provenance,
            "validation": validation,
            "created_at": created_at,
        }

        await self.persist_batch_doc(batch_doc)
        _safe_audit(
            "simulation_batch_started",
            actor=user_id,
            metadata={
                "batch_id": batch_id,
                "runs": batch.runs,
                "mode": batch_doc.get("mode"),
                "runtime_seconds": duration,
                "base_config": base_config_payload,
            },
        )
        return batch_doc

    def build_batch_csv(self, batch_doc: dict) -> str:
        results = batch_doc.get("run_manifest") or self._build_run_manifest(batch_doc.get("results", []))
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "simulation_id",
                "seed",
                "status",
                "total_agents",
                "evacuated",
                "completion_percentage",
                "total_time",
            ],
        )
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "simulation_id": result.get("simulation_id"),
                    "seed": result.get("seed"),
                    "status": result.get("status"),
                    "total_agents": result.get("total_agents"),
                    "evacuated": result.get("evacuated"),
                    "completion_percentage": result.get("completion_percentage"),
                    "total_time": result.get("total_time"),
                }
            )
        return output.getvalue()

    def _ensure_batch_research_contracts(self, batch_doc: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(batch_doc)
        results = list(normalized.get("results") or [])
        normalized["record_version"] = normalized.get("record_version") or BATCH_RECORD_VERSION
        normalized["aggregate"] = normalized.get("aggregate") or self._build_aggregate(results)
        normalized["status_counts"] = normalized.get("status_counts") or self._count_statuses(results)
        normalized["run_manifest"] = normalized.get("run_manifest") or self._build_run_manifest(results)
        total_runs = int(normalized.get("runs") or len(normalized["run_manifest"]) or 0)
        completed_runs = int(
            normalized.get("completed_runs")
            or (normalized.get("aggregate") or {}).get("completed_runs")
            or 0
        )
        normalized["completed_runs"] = completed_runs
        if not normalized.get("status"):
            if total_runs > 0 and completed_runs >= total_runs:
                normalized["status"] = "completed"
            elif completed_runs > 0:
                normalized["status"] = "partial"
            elif total_runs > 0:
                normalized["status"] = "running"
            else:
                normalized["status"] = "pending"
        metrics = dict(normalized.get("metrics") or {})
        evac_time = (normalized.get("aggregate") or {}).get("evacuation_time") or {}
        if metrics.get("best_evac_time") is None and evac_time.get("min") is not None:
            metrics["best_evac_time"] = evac_time.get("min")
        if metrics:
            normalized["metrics"] = metrics

        if not isinstance(normalized.get("provenance"), dict):
            created_at = normalized.get("created_at")
            if not isinstance(created_at, datetime):
                created_at = datetime.now(timezone.utc)
            base_config_payload = dict(normalized.get("base_config") or {})
            normalized["provenance"] = self._build_batch_provenance(
                batch_id=str(normalized.get("batch_id") or ""),
                base_config_payload=base_config_payload,
                config_hash=self._hash_config(base_config_payload),
                user_id=str(normalized.get("user_id") or "unknown"),
                mode=str(normalized.get("mode") or "fast"),
                runtime_seconds=float(normalized.get("runtime_seconds") or 0.0),
                seeds=[int(item["seed"]) for item in normalized["run_manifest"] if item.get("seed") is not None],
                created_at=created_at,
                floor_plan_data=None,
            )

        if not isinstance(normalized.get("validation"), dict):
            normalized["validation"] = self._build_batch_validation(
                batch_id=str(normalized.get("batch_id") or ""),
                run_manifest=normalized["run_manifest"],
                aggregate=normalized["aggregate"],
                runtime_seconds=float(normalized.get("runtime_seconds") or 0.0),
            )
        return normalized

    def _build_aggregate(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        completed = [r for r in results if r.get("status") in ("completed", "max_iterations", "stopped")]
        times = [r.get("final_stats", {}).get("total_time", 0.0) for r in completed]
        rates = [
            (
                r.get("final_stats", {}).get("evacuated", 0)
                / max(1, r.get("final_stats", {}).get("total_agents", 1))
            )
            for r in completed
        ]

        exit_usage_total: Dict[str, int] = {}
        profile_counts_total: Dict[str, int] = {}
        for result in completed:
            stats = result.get("final_stats", {})
            for exit_id, count in (stats.get("exit_usage") or {}).items():
                exit_usage_total[exit_id] = exit_usage_total.get(exit_id, 0) + int(count)
            for profile, count in (stats.get("profile_counts") or {}).items():
                profile_counts_total[profile] = profile_counts_total.get(profile, 0) + int(count)

        return {
            "evacuation_time": self._stats(times),
            "evacuation_rate": self._stats(rates),
            "exit_usage": exit_usage_total,
            "profile_counts": profile_counts_total,
            "completed_runs": len(completed),
            "failed_runs": max(0, len(results) - len(completed)),
        }

    def _count_statuses(self, results: List[Dict[str, Any]]) -> Dict[str, int]:
        status_counts: Dict[str, int] = {}
        for result in results:
            status = result.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
        return status_counts

    def _build_run_manifest(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        manifest: List[Dict[str, Any]] = []
        for result in results:
            final_stats = result.get("final_stats", {}) or {}
            manifest.append(
                {
                    "simulation_id": result.get("simulation_id"),
                    "seed": result.get("seed"),
                    "status": result.get("status"),
                    "total_agents": final_stats.get("total_agents"),
                    "evacuated": final_stats.get("evacuated"),
                    "completion_percentage": final_stats.get("completion_percentage"),
                    "total_time": final_stats.get("total_time"),
                }
            )
        return manifest

    def _hash_config(self, config_payload: Dict[str, Any]) -> str:
        return hashlib.sha256(
            json.dumps(config_payload or {}, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()

    def _build_batch_provenance(
        self,
        *,
        batch_id: str,
        base_config_payload: Dict[str, Any],
        config_hash: str,
        user_id: str,
        mode: str,
        runtime_seconds: float,
        seeds: List[int],
        created_at: datetime,
        floor_plan_data: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        floor_plan_revision = None
        if isinstance(floor_plan_data, dict):
            floor_plan_revision = (
                floor_plan_data.get("revision")
                or floor_plan_data.get("version")
                or floor_plan_data.get("updated_at")
            )
        provenance = build_provenance(
            base_config_payload,
            config_hash=config_hash,
            floor_plan_revision=str(floor_plan_revision) if floor_plan_revision is not None else None,
        ).to_dict()
        provenance.update(
            {
                "generated_at": created_at.isoformat(),
                "batch_id": batch_id,
                "actor_id": user_id,
                "execution_mode": mode,
                "runtime_seconds": runtime_seconds,
                "seed_sequence": seeds,
                "runs_requested": len(seeds),
            }
        )
        return provenance

    def _build_batch_validation(
        self,
        *,
        batch_id: str,
        run_manifest: List[Dict[str, Any]],
        aggregate: Dict[str, Any],
        runtime_seconds: float,
    ) -> Dict[str, Any]:
        total_runs = len(run_manifest)
        completed_runs = int(aggregate.get("completed_runs") or 0)
        has_times = bool((aggregate.get("evacuation_time") or {}).get("mean") is not None)
        all_seeded = total_runs > 0 and all(item.get("seed") is not None for item in run_manifest)
        all_completed = total_runs > 0 and completed_runs == total_runs
        checks = {
            "seed_traceability": {
                "status": "passed" if all_seeded else "failed",
                "passed": all_seeded,
                "score": 1.0 if all_seeded else 0.0,
                "seeded_runs": sum(1 for item in run_manifest if item.get("seed") is not None),
                "total_runs": total_runs,
            },
            "run_completion": {
                "status": "passed" if all_completed else "needs_review",
                "passed": all_completed,
                "score": (completed_runs / total_runs) if total_runs else 0.0,
                "completed_runs": completed_runs,
                "total_runs": total_runs,
            },
            "aggregate_metrics_available": {
                "status": "passed" if has_times else "failed",
                "passed": has_times,
                "score": 1.0 if has_times else 0.0,
                "runtime_seconds": runtime_seconds,
            },
        }
        return build_structured_validation_report(
            source="batch_execution",
            checks=checks,
            score_scale="unit_interval",
            provenance={
                "batch_id": batch_id,
                "run_count": total_runs,
                "completed_runs": completed_runs,
            },
        )

    @staticmethod
    def _stats(values: List[float]) -> Optional[Dict[str, float]]:
        if not values:
            return None
        values_sorted = sorted(values)

        def _pct(pct: float) -> float:
            if not values_sorted:
                return 0.0
            k = int(round((pct / 100.0) * (len(values_sorted) - 1)))
            return float(values_sorted[max(0, min(len(values_sorted) - 1, k))])

        mean_val = statistics.mean(values)
        variance_val = statistics.pvariance(values) if len(values) > 1 else 0.0
        stdev_val = statistics.pstdev(values) if len(values) > 1 else 0.0
        return {
            "mean": mean_val,
            "variance": variance_val,
            "stdev": stdev_val,
            "min": min(values),
            "max": max(values),
            "p50": _pct(50),
            "p90": _pct(90),
            "p99": _pct(99),
        }


simulation_batch_application_service = SimulationBatchApplicationService()
