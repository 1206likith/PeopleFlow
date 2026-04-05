"""
Generate research-ready summary plots and PDF from experiment outputs.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Any

import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def _load_results(output_dir: Path) -> List[Dict[str, Any]]:
    results = []
    for path in output_dir.glob("*.json"):
        if path.name in {"index.json", "metrics.csv", "calibration_summary.json"}:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            results.append(data)
        except Exception:
            continue
    return results


def _plot_metric(results: List[Dict[str, Any]], metric: str, out_path: Path, title: str):
    names = [r.get("config", {}).get("name", "unknown") for r in results]
    values = [r.get("metrics", {}).get(metric, 0) for r in results]
    if not values:
        return None
    plt.figure(figsize=(10, 4))
    plt.bar(names, values)
    plt.xticks(rotation=45, ha="right")
    plt.title(title)
    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=150)
    plt.close()
    return out_path


def generate_report(
    output_dir: str = "research/experiments/output",
    report_dir: str = "research/experiments/output/reports",
    public_report_dir: str = "artifacts/experiments/output/reports",
) -> Path | None:
    out_dir = Path(output_dir)
    results = _load_results(out_dir)
    if not results:
        return None

    report_path = Path(report_dir) / "summary_report.pdf"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    public_report_path = Path(public_report_dir) / "summary_report.pdf"
    public_report_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate plots
    plot_files = []
    plot_files.append(_plot_metric(results, "total_evacuation_time", Path(report_dir) / "total_time.png", "Total Evacuation Time"))
    plot_files.append(_plot_metric(results, "peak_flow_rate", Path(report_dir) / "peak_flow.png", "Peak Flow Rate"))
    plot_files.append(_plot_metric(results, "safety_score", Path(report_dir) / "safety_score.png", "Safety Score"))
    plot_files = [p for p in plot_files if p]

    # Build PDF
    c = canvas.Canvas(str(report_path), pagesize=letter)
    width, height = letter
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, height - 40, "PeopleFlow Experiment Summary")

    y = height - 80
    c.setFont("Helvetica", 10)
    for result in results[:10]:
        name = result.get("config", {}).get("name", "unknown")
        score = result.get("validation", {}).get("overall_score")
        c.drawString(40, y, f"{name} | validation score: {score}")
        y -= 14
        if y < 80:
            c.showPage()
            y = height - 80

    for plot in plot_files:
        c.showPage()
        c.setFont("Helvetica-Bold", 12)
        c.drawString(40, height - 40, plot.stem.replace("_", " ").title())
        c.drawImage(str(plot), 40, 80, width=520, height=280, preserveAspectRatio=True)

    c.save()

    # Copy PDF to artifacts path for UI access
    try:
        public_report_path.write_bytes(report_path.read_bytes())
    except Exception:
        pass

    return report_path


if __name__ == "__main__":
    generate_report()
