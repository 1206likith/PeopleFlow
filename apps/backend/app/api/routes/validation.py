"""
Validation & Benchmark API
Model validation against published evacuation data
"""
from fastapi import APIRouter, Depends, HTTPException
from app.core.request_context import get_request_actor
from app.services.validation_application_service import validation_application_service

router = APIRouter()

@router.post("/validate/{simulation_id}")
async def validate_simulation(
    simulation_id: str,
    current_user: dict = Depends(get_request_actor)
):
    """Validate simulation against research benchmarks"""
    try:
        del current_user
        return await validation_application_service.validate_simulation_by_id(simulation_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/benchmarks")
async def get_benchmarks(current_user: dict = Depends(get_request_actor)):
    """Get available research benchmarks"""
    del current_user
    return validation_application_service.list_benchmarks()

