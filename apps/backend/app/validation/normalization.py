"""
Normalization helpers for validation outputs used by experiments and APIs.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional


VALIDATION_SUMMARY_VERSION = "peopleflow-validation-summary-v1"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _status_from_score(overall_score: Optional[float], *, percentage_scale: bool, fallback_passed: bool) -> str:
    if overall_score is None:
        return "passed" if fallback_passed else "needs_review"
    threshold = 70.0 if percentage_scale else 0.7
    return "passed" if overall_score >= threshold else "needs_review"


def _normalize_check_payload(check_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    score = _as_float(payload.get("score"))
    passed = payload.get("passed")
    if passed is None:
        status = str(payload.get("status") or "").strip().lower()
        if status in {"ok", "passed", "success"}:
            passed = True
        elif status in {"poor_fit", "failed", "error", "not_run", "missing"}:
            passed = False
        elif score is not None:
            passed = score >= 0.5
        else:
            passed = False

    normalized_status = str(payload.get("status") or ("passed" if passed else "failed")).strip().lower()
    return {
        "check_id": check_id,
        "status": normalized_status,
        "score": score,
        "passed": bool(passed),
        "details": {
            key: value
            for key, value in payload.items()
            if key not in {"status", "score", "passed"}
        },
    }


def build_structured_validation_report(
    *,
    source: str,
    checks: Dict[str, Dict[str, Any]],
    score_scale: str = "unit_interval",
    overall_score: Optional[float] = None,
    status: Optional[str] = None,
    provenance: Optional[Dict[str, Any]] = None,
    raw: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    normalized_checks = {
        check_id: _normalize_check_payload(check_id, payload)
        for check_id, payload in checks.items()
        if isinstance(payload, dict)
    }
    passed_checks = sum(1 for payload in normalized_checks.values() if payload["passed"])
    total_checks = len(normalized_checks)

    computed_score = overall_score
    if computed_score is None and total_checks > 0:
        if score_scale == "percentage":
            computed_score = (passed_checks / total_checks) * 100.0
        else:
            computed_score = passed_checks / total_checks

    if status is None:
        if total_checks == 0 and computed_score is None:
            status = "not_run"
        else:
            status = _status_from_score(
                computed_score,
                percentage_scale=score_scale == "percentage",
                fallback_passed=passed_checks == total_checks,
            )

    generated_at = _now_iso()
    summary = {
        "schema_version": VALIDATION_SUMMARY_VERSION,
        "source": source,
        "generated_at": generated_at,
        "score_scale": score_scale,
        "overall_score": computed_score,
        "status": status,
        "passed_checks": passed_checks,
        "total_checks": total_checks,
    }
    normalized_provenance = {
        "source": source,
        "generated_at": generated_at,
        **(provenance or {}),
    }

    return {
        **(raw or {}),
        "summary": summary,
        "checks": normalized_checks,
        "provenance": normalized_provenance,
    }


def normalize_literature_validation_report(
    raw: Dict[str, Any],
    *,
    output_path: Optional[str] = None,
) -> Dict[str, Any]:
    checks = {
        check_id: payload
        for check_id, payload in raw.items()
        if check_id not in {"overall_score", "checks", "summary", "provenance"} and isinstance(payload, dict)
    }
    provenance = {"output_path": output_path} if output_path else {}
    return build_structured_validation_report(
        source="literature_validation",
        checks=checks,
        score_scale="unit_interval",
        overall_score=_as_float(raw.get("overall_score")),
        provenance=provenance,
        raw=raw,
    )


def normalize_runtime_validation_report(
    raw: Dict[str, Any],
    *,
    simulation_id: Optional[str] = None,
) -> Dict[str, Any]:
    checks: Dict[str, Dict[str, Any]] = {}
    raw_results = raw.get("results", []) if isinstance(raw.get("results"), list) else []

    for payload in raw_results:
        if not isinstance(payload, dict):
            continue
        check_id = str(payload.get("test_name") or f"check_{len(checks) + 1}")
        checks[check_id] = {
            "status": "passed" if bool(payload.get("passed")) else "failed",
            "score": 1.0 if bool(payload.get("passed")) else 0.0,
            "passed": bool(payload.get("passed")),
            **{
                key: value
                for key, value in payload.items()
                if key not in {"test_name", "passed"}
            },
        }
    provenance = {"simulation_id": simulation_id} if simulation_id else {}
    return build_structured_validation_report(
        source="runtime_validation",
        checks=checks,
        score_scale="percentage",
        overall_score=_as_float(raw.get("overall_score")),
        status=str(raw.get("validation_status")) if raw.get("validation_status") else None,
        provenance=provenance,
        raw=raw,
    )
