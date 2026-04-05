from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import logging
from pathlib import Path
import random
from typing import Any, Dict, List, Optional, Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.core.config import settings
from app.core.filesystem_hardening import get_safe_artifact_path
from app.experiments.artifact_manifests import build_research_artifact_record, write_research_artifact_index
from app.experiments.metadata import build_provenance
from app.services.simulation_repository import get_simulation_repository
from app.services.simulation_result_repository import get_simulation_result_repository
from app.validation.normalization import build_structured_validation_report

logger = logging.getLogger(__name__)
REPORT_ARTIFACT_MANIFEST_VERSION = "peopleflow-report-manifest-v1"
REPORT_ARTIFACT_INDEX_VERSION = "peopleflow-report-index-v1"


async def _load_report_dataset(simulation_id: str) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    if simulation_id.startswith("mock-"):
        if not settings.IS_DEMO_MODE:
            raise LookupError("Simulation not found")
        return (
            {
                "emergency_type": "fire",
                "num_agents": 100,
                "panic_level": 0.5,
            },
            [],
        )

    simulation_repository = await get_simulation_repository()
    simulation = await simulation_repository.get(simulation_id)
    if not simulation:
        if not settings.IS_DEMO_MODE:
            raise LookupError("Simulation not found")
        logger.warning("Simulation %s not found in repository, generating demo report", simulation_id)
        return None, []

    result_repository = await get_simulation_result_repository()
    frames = await result_repository.list_frames(
        simulation_id,
        limit=None,
        skip=0,
        from_ts=None,
        to_ts=None,
    )
    return simulation, frames


def _report_config_snapshot(simulation_id: str, simulation: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    simulation = simulation or {}
    return {
        "simulation_id": simulation_id,
        "floor_plan_id": simulation.get("floor_plan_id"),
        "seed": simulation.get("seed"),
        "num_agents": simulation.get("num_agents"),
        "emergency_type": simulation.get("emergency_type"),
        "panic_level": simulation.get("panic_level"),
        "metadata": simulation.get("metadata") if isinstance(simulation.get("metadata"), dict) else {},
    }


def _report_floor_plan_revision(simulation: Optional[Dict[str, Any]]) -> Optional[str]:
    if not isinstance(simulation, dict):
        return None
    metadata = simulation.get("metadata") if isinstance(simulation.get("metadata"), dict) else {}
    revision = (
        simulation.get("floor_plan_revision")
        or simulation.get("revision")
        or metadata.get("floor_plan_revision")
        or metadata.get("revision")
        or simulation.get("updated_at")
    )
    return str(revision) if revision is not None else None


def _hash_payload(payload: Dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _sanitize_artifact_type(artifact_type: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in artifact_type).strip("_") or "artifact"


def _report_manifest_path(simulation_id: str, artifact_type: str, artifact_path: Optional[str] = None) -> Path:
    if artifact_type == "pdf" and artifact_path:
        return Path(artifact_path).with_suffix(".manifest.json")
    suffix = _sanitize_artifact_type(artifact_type)
    return get_safe_artifact_path(f"simulation_report_{simulation_id}.{suffix}.manifest.json", subdir="reports")


def _report_index_path(simulation_id: str) -> Path:
    return get_safe_artifact_path(f"simulation_report_{simulation_id}.index.json", subdir="reports")


def _build_report_contract(
    simulation_id: str,
    simulation: Optional[Dict[str, Any]],
    frames: List[Dict[str, Any]],
    *,
    artifact_type: str,
    artifact_path: Optional[str] = None,
    heatmap_points: int = 0,
    survival_score_available: bool = False,
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    config_snapshot = _report_config_snapshot(simulation_id, simulation)
    provenance = build_provenance(
        config_snapshot,
        config_hash=_hash_payload(config_snapshot),
        floor_plan_revision=_report_floor_plan_revision(simulation),
    ).to_dict()
    provenance.update(
        {
            "simulation_id": simulation_id,
            "artifact_type": artifact_type,
            "frame_count": len(frames),
            "heatmap_points": heatmap_points,
        }
    )
    if artifact_path:
        provenance["artifact_path"] = artifact_path

    last_frame = frames[-1] if frames else {}
    dataset_summary = {
        "simulation_id": simulation_id,
        "artifact_type": artifact_type,
        "frame_count": len(frames),
        "heatmap_points": heatmap_points,
        "has_simulation_record": bool(simulation) or simulation_id.startswith(("mock-", "demo-")),
        "has_frame_series": bool(frames),
        "survival_score_available": survival_score_available,
        "total_agents": (simulation or {}).get("num_agents"),
        "last_timestamp": last_frame.get("timestamp"),
        "bottleneck_events": sum(len(frame.get("bottlenecks", [])) for frame in frames),
    }
    checks = {
        "simulation_record_available": {
            "status": "passed" if dataset_summary["has_simulation_record"] else "missing",
            "passed": dataset_summary["has_simulation_record"],
            "score": 1.0 if dataset_summary["has_simulation_record"] else 0.0,
        },
        "frame_series_available": {
            "status": "passed" if dataset_summary["has_frame_series"] else "missing",
            "passed": dataset_summary["has_frame_series"],
            "score": 1.0 if dataset_summary["has_frame_series"] else 0.0,
            "frame_count": len(frames),
        },
        "survival_score_available": {
            "status": "passed" if survival_score_available else "not_run",
            "passed": survival_score_available,
            "score": 1.0 if survival_score_available else 0.0,
        },
    }
    if artifact_type == "heatmap":
        checks["heatmap_density_available"] = {
            "status": "passed" if heatmap_points > 0 else "missing",
            "passed": heatmap_points > 0,
            "score": 1.0 if heatmap_points > 0 else 0.0,
            "heatmap_points": heatmap_points,
        }

    validation = build_structured_validation_report(
        source="report_generation",
        checks=checks,
        score_scale="unit_interval",
        provenance={
            "simulation_id": simulation_id,
            "artifact_type": artifact_type,
        },
    )
    return dataset_summary, provenance, validation


def _write_report_manifest(
    simulation_id: str,
    artifact_type: str,
    artifact_path: str,
    dataset_summary: Dict[str, Any],
    provenance: Dict[str, Any],
    validation: Dict[str, Any],
) -> str:
    manifest_path = _report_manifest_path(simulation_id, artifact_type, artifact_path)
    payload = build_research_artifact_record(
        artifact_id=f"report:{simulation_id}:{artifact_type}",
        artifact_kind="report",
        artifact_type=artifact_type,
        output_path=artifact_path,
        provenance=provenance,
        validation=validation,
        metadata={
            "simulation_id": simulation_id,
            "dataset_summary": dataset_summary,
        },
        generated_at=provenance.get("generated_at"),
    )
    payload.update(
        {
            "manifest_version": REPORT_ARTIFACT_MANIFEST_VERSION,
            "simulation_id": simulation_id,
            "artifact_path": artifact_path,
            "dataset_summary": dataset_summary,
            "provenance": provenance,
            "validation": validation,
        }
    )
    manifest_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return str(manifest_path)


def _write_report_artifact_index(simulation_id: str) -> Dict[str, Any]:
    index_path = _report_index_path(simulation_id)
    payload = write_research_artifact_index(
        source_dir=index_path.parent,
        output_path=index_path,
        metadata={
            "simulation_id": simulation_id,
            "artifact_kind": "report",
            "index_version": REPORT_ARTIFACT_INDEX_VERSION,
        },
        artifact_kind="report",
        filter_fn=lambda record: record.get("simulation_id") == simulation_id,
    )
    payload["simulation_id"] = simulation_id
    return payload


def _persist_heatmap_artifact(
    simulation_id: str,
    heatmap_payload: Dict[str, Any],
    dataset_summary: Dict[str, Any],
    provenance: Dict[str, Any],
    validation: Dict[str, Any],
) -> Tuple[str, str]:
    artifact_path = get_safe_artifact_path(f"simulation_report_{simulation_id}.heatmap.json", subdir="reports")
    artifact_path.write_text(json.dumps(heatmap_payload, indent=2, default=str), encoding="utf-8")
    manifest_path = _write_report_manifest(
        simulation_id,
        "heatmap",
        str(artifact_path),
        dataset_summary,
        provenance,
        validation,
    )
    _write_report_artifact_index(simulation_id)
    return str(artifact_path), manifest_path


async def get_report_artifacts(simulation_id: str) -> Dict[str, Any]:
    payload = _write_report_artifact_index(simulation_id)
    payload["catalog_version"] = REPORT_ARTIFACT_INDEX_VERSION
    return payload


async def generate_pdf_report(simulation_id: str, db=None) -> str:
    del db
    report_path = str(get_safe_artifact_path(f"simulation_report_{simulation_id}.pdf", subdir="reports"))

    doc = SimpleDocTemplate(report_path, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()

    title = Paragraph("PeopleFlow Simulation Report", styles["Title"])
    story.append(title)
    story.append(Spacer(1, 0.2 * inch))

    simulation = None
    frames: List[Dict[str, Any]] = []
    survival_score = None

    try:
        simulation, frames = await _load_report_dataset(simulation_id)
        if simulation_id.startswith("mock-"):
            logger.info("Generating report for mock simulation %s", simulation_id)
    except LookupError:
        raise
    except Exception as exc:
        logger.warning("Error loading simulation data for report %s: %s", simulation_id, exc)

    story.append(Paragraph(f"<b>Simulation ID:</b> {simulation_id}", styles["Normal"]))
    if simulation:
        story.append(Paragraph(f"<b>Emergency Type:</b> {simulation.get('emergency_type', 'fire')}", styles["Normal"]))
        story.append(Paragraph(f"<b>Number of Agents:</b> {simulation.get('num_agents', 0)}", styles["Normal"]))
        story.append(Paragraph(f"<b>Panic Level:</b> {simulation.get('panic_level', 0.5):.2f}", styles["Normal"]))
    else:
        story.append(Paragraph("<b>Status:</b> Demo Simulation", styles["Normal"]))
    story.append(Spacer(1, 0.2 * inch))

    if frames:
        total_agents = simulation.get("num_agents", 0) if simulation else 0
        last_frame = frames[-1]
        evacuated = sum(1 for agent in last_frame.get("agents", []) if agent.get("status") == "evacuated")
        total_time = last_frame.get("timestamp", 0)

        story.append(Paragraph("<b>Simulation Statistics</b>", styles["Heading2"]))
        story.append(Spacer(1, 0.1 * inch))

        data = [
            ["Metric", "Value"],
            ["Total Agents", str(total_agents)],
            ["Evacuated", f"{evacuated} ({round(evacuated / total_agents * 100, 1) if total_agents > 0 else 0}%)"],
            ["Total Time", f"{total_time:.1f} seconds"],
            ["Bottlenecks Detected", str(len(last_frame.get('bottlenecks', [])))],
        ]

        table = Table(data, colWidths=[3 * inch, 2 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 0.3 * inch))
    else:
        story.append(Paragraph("<b>Simulation Statistics</b>", styles["Heading2"]))
        story.append(Spacer(1, 0.1 * inch))
        story.append(
            Paragraph(
                "No simulation data available. This may be a demo simulation or the simulation is still running.",
                styles["Normal"],
            )
        )
        story.append(Spacer(1, 0.3 * inch))

    story.append(PageBreak())
    story.append(Paragraph("<b>Executive Summary</b>", styles["Heading1"]))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("<b>Incident Cause Analysis</b>", styles["Heading2"]))
    if simulation:
        emergency_type = simulation.get("emergency_type", "fire")
        story.append(Paragraph(f"Emergency Type: {emergency_type.upper()}", styles["Normal"]))
        story.append(Paragraph(f"Panic Level: {simulation.get('panic_level', 0.5):.2f}", styles["Normal"]))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("<b>High-Risk Zones</b>", styles["Heading2"]))
    if frames:
        all_bottlenecks = []
        for frame in frames:
            all_bottlenecks.extend(frame.get("bottlenecks", []))

        if all_bottlenecks:
            zone_counts = defaultdict(int)
            for bottleneck in all_bottlenecks:
                key = f"({bottleneck.get('x', 0):.1f}, {bottleneck.get('z', bottleneck.get('y', 0)):.1f})"
                zone_counts[key] += 1

            story.append(Paragraph("Identified high-risk zones:", styles["Normal"]))
            for zone, count in sorted(zone_counts.items(), key=lambda item: item[1], reverse=True)[:5]:
                story.append(Paragraph(f"* Zone {zone}: {count} bottleneck events", styles["Normal"]))
        else:
            story.append(Paragraph("No high-risk zones identified in this simulation.", styles["Normal"]))
    else:
        story.append(Paragraph("No frame series available to compute risk zoning.", styles["Normal"]))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("<b>Building Weakness Index</b>", styles["Heading2"]))
    try:
        from app.services.survival_score import survival_score_engine

        if simulation and frames:
            last_frame = frames[-1] if frames else {}
            survival_score = survival_score_engine.calculate_score(
                simulation,
                last_frame.get("agents", []),
                [],
                last_frame.get("bottlenecks", []),
                simulation.get("emergency_type", "fire"),
            )
            story.append(Paragraph(f"Survival Score: {survival_score.total_score}/100 (Grade: {survival_score.grade})", styles["Normal"]))
            story.append(Paragraph("Key Factors:", styles["Normal"]))
            for factor in survival_score.factors[:5]:
                story.append(Paragraph(f"* {factor}", styles["Normal"]))
        else:
            story.append(Paragraph("Survival score unavailable due to incomplete frame data.", styles["Normal"]))
    except Exception as exc:
        logger.warning("Could not calculate survival score: %s", exc)
        story.append(Paragraph("Survival score calculation unavailable.", styles["Normal"]))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("<b>AI-Generated Recommendations</b>", styles["Heading2"]))
    try:
        if survival_score is not None:
            for recommendation in survival_score.recommendations[:5]:
                story.append(Paragraph(f"* {recommendation}", styles["Normal"]))
        else:
            story.append(Paragraph("* Validate floor plan geometry and exits before rerun", styles["Normal"]))
            story.append(Paragraph("* Collect frame telemetry to enable risk diagnostics", styles["Normal"]))
    except Exception as exc:
        logger.warning("Could not generate recommendations: %s", exc)
        story.append(Paragraph("* Review evacuation routes and exit capacity", styles["Normal"]))
        story.append(Paragraph("* Improve wayfinding and emergency signage", styles["Normal"]))

    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph(f"<i>Report Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</i>", styles["Normal"]))

    doc.build(story)
    dataset_summary, provenance, validation = _build_report_contract(
        simulation_id,
        simulation,
        frames,
        artifact_type="pdf",
        artifact_path=report_path,
        heatmap_points=0,
        survival_score_available=survival_score is not None,
    )
    manifest_path = _write_report_manifest(
        simulation_id,
        "pdf",
        report_path,
        dataset_summary,
        provenance,
        validation,
    )
    _write_report_artifact_index(simulation_id)
    logger.info("Report generated successfully: %s", report_path)
    logger.info("Report manifest generated successfully: %s", manifest_path)
    return report_path


async def build_heatmap_data(simulation_id: str) -> Dict[str, Any]:
    if simulation_id.startswith("mock-") or simulation_id.startswith("demo-"):
        if not settings.IS_DEMO_MODE:
            raise LookupError("Simulation not found")
        mock_heatmap = []
        for _ in range(200):
            mock_heatmap.append(
                {
                    "x": random.uniform(-50, 50),
                    "y": random.uniform(-50, 50),
                    "intensity": random.uniform(0.3, 1.0),
                }
            )
        dataset_summary, provenance, validation = _build_report_contract(
            simulation_id,
            {
                "emergency_type": "fire",
                "num_agents": 100,
                "panic_level": 0.5,
            },
            [],
            artifact_type="heatmap",
            heatmap_points=len(mock_heatmap),
            survival_score_available=False,
        )
        payload = {
            "simulation_id": simulation_id,
            "heatmap_data": mock_heatmap,
            "total_points": len(mock_heatmap),
            "report_summary": dataset_summary,
            "provenance": provenance,
            "validation": validation,
        }
        _persist_heatmap_artifact(simulation_id, payload, dataset_summary, provenance, validation)
        return payload

    simulation_repository = await get_simulation_repository()
    simulation = await simulation_repository.get(simulation_id)
    if not simulation:
        if not settings.IS_DEMO_MODE:
            raise LookupError("Simulation not found")
        dataset_summary, provenance, validation = _build_report_contract(
            simulation_id,
            None,
            [],
            artifact_type="heatmap",
            heatmap_points=0,
            survival_score_available=False,
        )
        payload = {
            "simulation_id": simulation_id,
            "heatmap_data": [],
            "total_points": 0,
            "report_summary": dataset_summary,
            "provenance": provenance,
            "validation": validation,
        }
        _persist_heatmap_artifact(simulation_id, payload, dataset_summary, provenance, validation)
        return payload

    result_repository = await get_simulation_result_repository()
    frames = await result_repository.list_frames(
        simulation_id,
        limit=None,
        skip=0,
        from_ts=None,
        to_ts=None,
    )

    heatmap_data = []
    for frame in frames:
        for agent in frame.get("agents", []):
            heatmap_data.append(
                {
                    "x": agent.get("x", 0),
                    "y": agent.get("y", 0),
                    "intensity": 1.0,
                }
            )

    dataset_summary, provenance, validation = _build_report_contract(
        simulation_id,
        simulation,
        frames,
        artifact_type="heatmap",
        heatmap_points=len(heatmap_data),
        survival_score_available=False,
    )
    payload = {
        "simulation_id": simulation_id,
        "heatmap_data": heatmap_data,
        "total_points": len(heatmap_data),
        "report_summary": dataset_summary,
        "provenance": provenance,
        "validation": validation,
    }
    _persist_heatmap_artifact(simulation_id, payload, dataset_summary, provenance, validation)
    return payload
