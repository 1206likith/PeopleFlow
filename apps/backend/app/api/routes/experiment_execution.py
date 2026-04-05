"""
Experiment execution API.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool

from app.core.request_context import get_request_actor
from app.experiments.config import ExperimentConfig
from app.services.experiment_execution_service import experiment_execution_service
from app.services.experiment_job_service import experiment_job_service

router = APIRouter()


class BackgroundExecutionRequest(BaseModel):
    background: bool = False


class ExperimentRunRequest(BackgroundExecutionRequest):
    model_config = ConfigDict(populate_by_name=True)

    config: ExperimentConfig
    validation_enabled: bool = Field(default=False, alias="validate")


class ExperimentAblationRequest(BackgroundExecutionRequest):
    model_config = ConfigDict(populate_by_name=True)

    base_config: ExperimentConfig
    validation_enabled: bool = Field(default=False, alias="validate")


class ExperimentCalibrationRequest(BackgroundExecutionRequest):
    base_config: ExperimentConfig
    calibration_config: Optional[Dict[str, Any]] = None
    calibration_config_path: Optional[str] = None


class ExperimentOptimizationRequest(BackgroundExecutionRequest):
    base_config: ExperimentConfig
    optimization_config: Optional[Dict[str, Any]] = None
    optimization_config_path: Optional[str] = None


class PublicationBundleExecutionRequest(BackgroundExecutionRequest):
    model_config = ConfigDict(populate_by_name=True)

    batch_config: Optional[Dict[str, Any]] = None
    batch_config_path: Optional[str] = None
    validation_enabled: bool = Field(default=True, alias="validate")
    artifacts_root: Optional[str] = None
    copy_run_outputs: bool = True


class BenchmarkExecutionRequest(BackgroundExecutionRequest):
    num_agents: Optional[int] = Field(default=None, ge=1, le=10000)


def _failure_detail(prefix: str, exc: Exception) -> str:
    message = str(exc).strip() or exc.__class__.__name__
    return f"{prefix}: {message}"


def _actor_id(current_user: dict) -> str:
    return str(current_user.get("_id") or current_user.get("id") or current_user.get("actor_id") or "unknown")


def _background_response(
    *,
    execution_type: str,
    current_user: dict,
    runner,
    input_summary: Dict[str, Any],
) -> JSONResponse:
    job = experiment_job_service.submit_job(
        execution_type=execution_type,
        requested_by=_actor_id(current_user),
        runner=runner,
        input_summary=input_summary,
    )
    return JSONResponse(status_code=202, content=job)


@router.get("/benchmarks")
async def list_executable_benchmarks(current_user: dict = Depends(get_request_actor)):
    """List executable research benchmarks exposed by the backend."""
    del current_user
    return experiment_execution_service.list_benchmarks()


@router.get("/jobs")
async def list_experiment_jobs(
    limit: int = Query(default=12, ge=1, le=200),
    status: Optional[str] = Query(default=None),
    current_user: dict = Depends(get_request_actor),
):
    """List background experiment jobs without returning full results."""
    del current_user
    try:
        return experiment_job_service.list_jobs(limit=limit, status=status)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=_failure_detail("Experiment job listing failed", exc))


@router.get("/jobs/{job_id}")
async def get_experiment_job(job_id: str, current_user: dict = Depends(get_request_actor)):
    """Fetch full background experiment job status and result payload."""
    del current_user
    try:
        return experiment_job_service.get_job(job_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=_failure_detail("Experiment job lookup failed", exc))


@router.post("/runs")
async def run_experiment(request: ExperimentRunRequest, current_user: dict = Depends(get_request_actor)):
    """Run a single research experiment and refresh artifact catalogs."""
    if request.background:
        return _background_response(
            execution_type="single_run",
            current_user=current_user,
            runner=lambda: experiment_execution_service.run_experiment(
                request.config,
                validate=request.validation_enabled,
            ),
            input_summary={
                "name": request.config.name,
                "floor_plan_id": request.config.floor_plan_id,
                "num_agents": request.config.num_agents,
                "validate": request.validation_enabled,
            },
        )
    try:
        return await run_in_threadpool(
            experiment_execution_service.run_experiment,
            request.config,
            validate=request.validation_enabled,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=_failure_detail("Experiment execution failed", exc))


@router.post("/ablations")
async def run_ablation(request: ExperimentAblationRequest, current_user: dict = Depends(get_request_actor)):
    """Run an ablation grid and refresh artifact catalogs."""
    if request.background:
        return _background_response(
            execution_type="ablation",
            current_user=current_user,
            runner=lambda: experiment_execution_service.run_ablation(
                request.base_config,
                validate=request.validation_enabled,
            ),
            input_summary={
                "name": request.base_config.name,
                "floor_plan_id": request.base_config.floor_plan_id,
                "num_agents": request.base_config.num_agents,
                "validate": request.validation_enabled,
            },
        )
    try:
        return await run_in_threadpool(
            experiment_execution_service.run_ablation,
            request.base_config,
            validate=request.validation_enabled,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=_failure_detail("Ablation execution failed", exc))


@router.post("/calibrations")
async def run_calibration(request: ExperimentCalibrationRequest, current_user: dict = Depends(get_request_actor)):
    """Run calibration search against literature validation targets."""
    if request.background:
        return _background_response(
            execution_type="calibration",
            current_user=current_user,
            runner=lambda: experiment_execution_service.run_calibration(
                request.base_config,
                calibration_config=request.calibration_config,
                calibration_config_path=request.calibration_config_path,
            ),
            input_summary={
                "name": request.base_config.name,
                "floor_plan_id": request.base_config.floor_plan_id,
                "num_agents": request.base_config.num_agents,
                "calibration_config_path": request.calibration_config_path,
                "inline_config": request.calibration_config is not None,
            },
        )
    try:
        return await run_in_threadpool(
            experiment_execution_service.run_calibration,
            request.base_config,
            calibration_config=request.calibration_config,
            calibration_config_path=request.calibration_config_path,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=_failure_detail("Calibration execution failed", exc))


@router.post("/optimizations")
async def run_optimization(request: ExperimentOptimizationRequest, current_user: dict = Depends(get_request_actor)):
    """Run optimization search and refresh experiment artifact catalogs."""
    if request.background:
        return _background_response(
            execution_type="optimization",
            current_user=current_user,
            runner=lambda: experiment_execution_service.run_optimization(
                request.base_config,
                optimization_config=request.optimization_config,
                optimization_config_path=request.optimization_config_path,
            ),
            input_summary={
                "name": request.base_config.name,
                "floor_plan_id": request.base_config.floor_plan_id,
                "num_agents": request.base_config.num_agents,
                "optimization_config_path": request.optimization_config_path,
                "inline_config": request.optimization_config is not None,
            },
        )
    try:
        return await run_in_threadpool(
            experiment_execution_service.run_optimization,
            request.base_config,
            optimization_config=request.optimization_config,
            optimization_config_path=request.optimization_config_path,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=_failure_detail("Optimization execution failed", exc))


@router.post("/publication-bundles")
async def create_publication_bundle(
    request: PublicationBundleExecutionRequest,
    current_user: dict = Depends(get_request_actor),
):
    """Create a publication-ready bundle from inline or file-backed paper suite config."""
    if request.background:
        return _background_response(
            execution_type="publication_bundle",
            current_user=current_user,
            runner=lambda: experiment_execution_service.run_publication_bundle(
                batch_config=request.batch_config,
                batch_config_path=request.batch_config_path,
                validate=request.validation_enabled,
                artifacts_root=request.artifacts_root,
                copy_run_outputs=request.copy_run_outputs,
            ),
            input_summary={
                "batch_config_path": request.batch_config_path,
                "inline_config": request.batch_config is not None,
                "validate": request.validation_enabled,
                "copy_run_outputs": request.copy_run_outputs,
            },
        )
    try:
        return await run_in_threadpool(
            experiment_execution_service.run_publication_bundle,
            batch_config=request.batch_config,
            batch_config_path=request.batch_config_path,
            validate=request.validation_enabled,
            artifacts_root=request.artifacts_root,
            copy_run_outputs=request.copy_run_outputs,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=_failure_detail("Publication bundle execution failed", exc))


@router.post("/benchmarks/{benchmark_name}/run")
async def run_benchmark(
    benchmark_name: str,
    request: BenchmarkExecutionRequest,
    current_user: dict = Depends(get_request_actor),
):
    """Run a named executable benchmark scenario."""
    try:
        benchmark_definition = experiment_execution_service.get_benchmark_definition(benchmark_name)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    if request.background:
        return _background_response(
            execution_type="benchmark",
            current_user=current_user,
            runner=lambda: experiment_execution_service.run_benchmark(
                benchmark_name,
                num_agents=request.num_agents,
            ),
            input_summary={
                "benchmark": benchmark_definition["name"],
                "description": benchmark_definition["description"],
                "num_agents": request.num_agents or benchmark_definition["default_num_agents"],
            },
        )
    try:
        return await run_in_threadpool(
            experiment_execution_service.run_benchmark,
            benchmark_name,
            num_agents=request.num_agents,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=_failure_detail("Benchmark execution failed", exc))
