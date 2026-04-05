"""
Background job orchestration for long-running experiment workflows.
"""
from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from threading import RLock
from typing import Any, Callable, Dict, Optional
from uuid import uuid4


JobRunner = Callable[[], Dict[str, Any]]


class ExperimentJobService:
    _SCHEMA_VERSION = "peopleflow-experiment-job-v1"
    _ACTIVE_STATUSES = {"queued", "running"}
    _RESTART_FAILURE = {
        "type": "ProcessRestartInterrupted",
        "message": "Job was active when the backend process restarted and must be relaunched.",
    }

    def __init__(
        self,
        *,
        max_workers: int = 2,
        storage_path: Optional[str | Path] = None,
        max_history: int = 250,
    ) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max(1, int(max_workers)), thread_name_prefix="peopleflow-exp-job")
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._futures: Dict[str, Future] = {}
        self._lock = RLock()
        self._max_history = max(10, int(max_history))
        self._storage_path = self._resolve_storage_path(storage_path)
        self._load_jobs()

    @staticmethod
    def _resolve_storage_path(storage_path: Optional[str | Path]) -> Optional[Path]:
        if storage_path is not None:
            return Path(storage_path).expanduser().resolve()

        override = os.getenv("PEOPLEFLOW_EXPERIMENT_JOB_STORE_PATH", "").strip()
        if override:
            return Path(override).expanduser().resolve()

        if "pytest" in sys.modules:
            return None

        return (Path.home() / ".peopleflow" / "runtime" / "experiment_jobs.json").resolve()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _copy(value: Any) -> Any:
        return deepcopy(value)

    def _persist_locked(self) -> None:
        if self._storage_path is None:
            return

        rows = [self._copy(job) for job in self._jobs.values()]
        rows.sort(key=lambda item: str(item.get("submitted_at") or ""), reverse=True)

        active_rows = [row for row in rows if str(row.get("status") or "").lower() in self._ACTIVE_STATUSES]
        completed_rows = [row for row in rows if str(row.get("status") or "").lower() not in self._ACTIVE_STATUSES]
        persisted_rows = active_rows + completed_rows[: self._max_history]

        payload = {
            "job_schema_version": self._SCHEMA_VERSION,
            "persisted_at": self._now(),
            "job_count": len(persisted_rows),
            "jobs": persisted_rows,
        }

        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self._storage_path.with_suffix(f"{self._storage_path.suffix}.tmp")
        temp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temp_path.replace(self._storage_path)

    def _load_jobs(self) -> None:
        if self._storage_path is None or not self._storage_path.exists():
            return

        try:
            payload = json.loads(self._storage_path.read_text(encoding="utf-8-sig"))
        except Exception:
            return

        rows = payload.get("jobs") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            return

        now = self._now()
        recovered_active = False
        with self._lock:
            self._jobs.clear()
            for row in rows:
                if not isinstance(row, dict):
                    continue
                job_id = str(row.get("job_id") or "").strip()
                if not job_id:
                    continue
                job = self._copy(row)
                status = str(job.get("status") or "").lower()
                if status in self._ACTIVE_STATUSES:
                    recovered_active = True
                    job["status"] = "failed"
                    job["completed_at"] = job.get("completed_at") or now
                    job["updated_at"] = now
                    job["error"] = self._copy(self._RESTART_FAILURE)
                self._jobs[job_id] = job

            if recovered_active:
                self._persist_locked()

    @staticmethod
    def _result_summary(execution_type: str, result: Dict[str, Any]) -> Dict[str, str]:
        if execution_type == "benchmark":
            benchmark_name = str(result.get("benchmark") or "run").strip() or "run"
            return {
                "title": f"Benchmark {benchmark_name}",
                "detail": str(result.get("description") or "Benchmark completed."),
            }

        if execution_type == "publication_bundle":
            bundle = result.get("bundle") if isinstance(result.get("bundle"), dict) else {}
            return {
                "title": str(bundle.get("suite_name") or "Publication bundle ready"),
                "detail": str(bundle.get("publication_manifest") or bundle.get("artifact_dir") or "Publication bundle generated."),
            }

        if execution_type == "single_run":
            payload = result.get("result") if isinstance(result.get("result"), dict) else {}
            config = payload.get("config") if isinstance(payload.get("config"), dict) else {}
            return {
                "title": str(config.get("name") or "Experiment run"),
                "detail": str(payload.get("config_hash") or "Single run completed."),
            }

        summary = result.get("summary") if isinstance(result.get("summary"), dict) else {}
        best = summary.get("best") if isinstance(summary.get("best"), dict) else {}
        best_name = str(best.get("name") or "").strip()
        best_score = best.get("score")
        source_path = str(summary.get("source_config_path") or summary.get("output_path") or "").strip()
        detail_parts = []
        if best_name:
            if isinstance(best_score, (int, float)):
                detail_parts.append(f"Best {best_name} ({float(best_score):.2f})")
            else:
                detail_parts.append(f"Best {best_name}")
        if source_path:
            detail_parts.append(source_path)
        return {
            "title": str(summary.get("suite_type") or execution_type).replace("_", " ").title() + " Suite",
            "detail": " | ".join(detail_parts) or "Execution completed.",
        }

    @staticmethod
    def _error_payload(error: Exception) -> Dict[str, str]:
        return {
            "type": type(error).__name__,
            "message": str(error),
        }

    def _job_snapshot(self, job_id: str, *, include_result: bool) -> Dict[str, Any]:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise LookupError("Experiment job not found")
            payload = self._copy(job)
        if not include_result:
            payload.pop("result", None)
        return payload

    def _run_job(self, job_id: str, runner: JobRunner) -> None:
        started_at = self._now()
        with self._lock:
            job = self._jobs[job_id]
            job["status"] = "running"
            job["started_at"] = started_at
            job["updated_at"] = started_at
            self._persist_locked()

        try:
            result = runner()
        except Exception as exc:
            completed_at = self._now()
            with self._lock:
                job = self._jobs[job_id]
                job["status"] = "failed"
                job["completed_at"] = completed_at
                job["updated_at"] = completed_at
                job["error"] = self._error_payload(exc)
                job["result_summary"] = None
                self._persist_locked()
            return

        completed_at = self._now()
        with self._lock:
            job = self._jobs[job_id]
            job["status"] = "completed"
            job["completed_at"] = completed_at
            job["updated_at"] = completed_at
            job["error"] = None
            job["result"] = self._copy(result)
            job["result_summary"] = self._result_summary(str(job.get("execution_type") or "unknown"), result if isinstance(result, dict) else {})
            self._persist_locked()

    def submit_job(
        self,
        *,
        execution_type: str,
        requested_by: str,
        runner: JobRunner,
        input_summary: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        now = self._now()
        job_id = f"expjob-{uuid4().hex[:12]}"
        job = {
            "job_schema_version": self._SCHEMA_VERSION,
            "job_id": job_id,
            "execution_type": execution_type,
            "status": "queued",
            "background": True,
            "requested_by": requested_by,
            "input_summary": self._copy(input_summary or {}),
            "submitted_at": now,
            "updated_at": now,
            "started_at": None,
            "completed_at": None,
            "result_summary": None,
            "result": None,
            "error": None,
        }

        with self._lock:
            self._jobs[job_id] = job
            self._persist_locked()
            self._futures[job_id] = self._executor.submit(self._run_job, job_id, runner)

        return self._job_snapshot(job_id, include_result=False)

    def list_jobs(self, *, limit: int = 20, status: Optional[str] = None) -> Dict[str, Any]:
        normalized_limit = max(1, min(int(limit or 20), 200))
        status_filter = str(status or "").strip().lower()

        with self._lock:
            jobs = [self._copy(job) for job in self._jobs.values()]

        jobs.sort(key=lambda item: str(item.get("submitted_at") or ""), reverse=True)
        if status_filter:
            jobs = [job for job in jobs if str(job.get("status") or "").lower() == status_filter]

        active_count = sum(1 for job in self._jobs.values() if str(job.get("status") or "").lower() in self._ACTIVE_STATUSES)
        summaries = []
        for job in jobs[:normalized_limit]:
            job.pop("result", None)
            summaries.append(job)

        return {
            "job_schema_version": self._SCHEMA_VERSION,
            "job_count": len(jobs),
            "active_count": active_count,
            "jobs": summaries,
        }

    def get_job(self, job_id: str) -> Dict[str, Any]:
        return self._job_snapshot(job_id, include_result=True)

    def wait_for_completion(self, job_id: str, timeout: float = 5.0) -> Dict[str, Any]:
        with self._lock:
            future = self._futures.get(job_id)
        if future is None:
            raise LookupError("Experiment job not found")
        future.result(timeout=timeout)
        return self.get_job(job_id)


experiment_job_service = ExperimentJobService()
