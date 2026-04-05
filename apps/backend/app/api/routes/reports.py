from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
import logging
import os

from app.core.config import settings
from app.core.request_context import get_request_actor
from app.services.report_service import build_heatmap_data, generate_pdf_report, get_report_artifacts

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{simulation_id}/pdf")
async def generate_report(
    simulation_id: str,
    current_user: dict = Depends(get_request_actor),
):
    """Generate PDF report for a simulation."""
    del current_user
    if (simulation_id.startswith("demo-") or simulation_id.startswith("mock-")) and not settings.IS_DEMO_MODE:
        raise HTTPException(status_code=404, detail="Simulation not found")

    try:
        report_path = await generate_pdf_report(simulation_id)
        if not os.path.exists(report_path):
            raise HTTPException(status_code=500, detail="Failed to generate report")

        return FileResponse(
            report_path,
            media_type="application/pdf",
            filename=f"simulation_report_{simulation_id}.pdf",
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error generating report: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(exc)}")


@router.get("/{simulation_id}/heatmap")
async def get_heatmap_data(
    simulation_id: str,
    current_user: dict = Depends(get_request_actor),
):
    """Get heatmap data for visualization."""
    del current_user
    try:
        return await build_heatmap_data(simulation_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.warning("Database unavailable for get_heatmap: %s", exc)
        if not settings.IS_DEMO_MODE:
            raise HTTPException(status_code=503, detail="Database unavailable")
        return {
            "simulation_id": simulation_id,
            "heatmap_data": [],
            "total_points": 0,
        }


@router.get("/{simulation_id}/artifacts")
async def get_report_artifact_catalog(
    simulation_id: str,
    current_user: dict = Depends(get_request_actor),
):
    """Get indexed report artifacts for a simulation."""
    del current_user
    try:
        return await get_report_artifacts(simulation_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error("Error loading report artifacts: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Report artifact lookup failed: {str(exc)}")
