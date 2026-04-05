"""
Forensic Replay API
Timeline scrubber, agent decision replay, density evolution
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from app.core.request_context import get_request_actor
from app.services.forensic_replay import forensic_replay

router = APIRouter()

@router.get("/timeline/{simulation_id}")
async def get_timeline(
    simulation_id: str,
    start_time: Optional[float] = 0.0,
    end_time: Optional[float] = None,
    current_user: dict = Depends(get_request_actor)
):
    """Get replay timeline for simulation"""
    try:
        frames = forensic_replay.get_timeline(start_time, end_time)
        return {
            "simulation_id": simulation_id,
            "frames": [
                {
                    "timestamp": frame.timestamp,
                    "agent_count": len(frame.agents),
                    "bottleneck_count": len(frame.bottlenecks),
                    "peak_density": max(frame.density_map.values()) if frame.density_map else 0.0
                }
                for frame in frames
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agent/{simulation_id}/{agent_id}")
async def get_agent_timeline(
    simulation_id: str,
    agent_id: int,
    current_user: dict = Depends(get_request_actor)
):
    """Get complete timeline for a specific agent"""
    try:
        timeline = forensic_replay.get_agent_timeline(agent_id)
        return {
            "simulation_id": simulation_id,
            "agent_id": agent_id,
            "timeline": timeline
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/report/{simulation_id}")
async def get_replay_report(
    simulation_id: str,
    current_user: dict = Depends(get_request_actor)
):
    """Get comprehensive replay report"""
    try:
        report = forensic_replay.generate_replay_report()
        return {
            "simulation_id": simulation_id,
            **report
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/density-evolution/{simulation_id}")
async def get_density_evolution(
    simulation_id: str,
    current_user: dict = Depends(get_request_actor)
):
    """Get density evolution over time"""
    try:
        evolution = forensic_replay.get_density_evolution()
        return {
            "simulation_id": simulation_id,
            "evolution": evolution
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/death-zones/{simulation_id}")
async def get_death_zones(
    simulation_id: str,
    current_user: dict = Depends(get_request_actor)
):
    """Get identified death zones"""
    try:
        death_zones = forensic_replay.get_death_zones()
        return {
            "simulation_id": simulation_id,
            "death_zones": death_zones
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

