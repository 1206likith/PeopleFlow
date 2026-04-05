"""
Survival Optimization API
AI redesigns building using genetic algorithms
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict
from app.core.request_context import get_request_actor
from app.services.optimization_engine import genetic_optimizer
from app.services.evacuation_parameters import EvacuationPolicy

router = APIRouter()

class OptimizationRequest(BaseModel):
    building_bounds: Dict
    current_exits: List[Dict]
    num_agents: int = 100
    generations: int = 50
    population_size: int = 30

@router.post("/optimize-exits")
async def optimize_exits(
    request: OptimizationRequest,
    current_user: dict = Depends(get_request_actor)
):
    """Optimize exit configuration using genetic algorithm"""
    try:
        result = genetic_optimizer.optimize_exits(
            request.building_bounds,
            request.current_exits,
            request.num_agents,
            None  # simulation_runner would be passed here
        )
        
        return {
            "optimized_exits": result["optimized_exits"],
            "fitness": result["fitness"],
            "improvement": result["improvement"],
            "recommendations": [
                f"Estimated {result['improvement']['improvement_percent']:.1f}% improvement in evacuation time",
                f"Survival rate increase: {result['improvement']['estimated_survival_increase']:.1f}%"
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/compare-policies")
async def compare_policies(
    simulation_id: str,
    current_user: dict = Depends(get_request_actor)
):
    """Compare different evacuation policies"""
    policies = [
        EvacuationPolicy.NEAREST_EXIT,
        EvacuationPolicy.LEAST_CROWDED,
        EvacuationPolicy.FOLLOW_LEADER,
        EvacuationPolicy.RANDOM_PANIC,
        EvacuationPolicy.AUTHORITY_DIRECTED
    ]
    
    # Would run simulation with each policy and compare
    # For now, return policy descriptions
    return {
        "policies": [
            {
                "id": policy.value,
                "name": policy.value.replace("_", " ").title(),
                "description": _get_policy_description(policy)
            }
            for policy in policies
        ]
    }

def _get_policy_description(policy: EvacuationPolicy) -> str:
    """Get description for evacuation policy"""
    descriptions = {
        EvacuationPolicy.NEAREST_EXIT: "Agents choose the nearest exit (fastest individual time)",
        EvacuationPolicy.LEAST_CROWDED: "Agents choose least crowded exit (better load balancing)",
        EvacuationPolicy.FOLLOW_LEADER: "Agents follow leader personalities (group behavior)",
        EvacuationPolicy.RANDOM_PANIC: "Agents make random choices (panic behavior)",
        EvacuationPolicy.AUTHORITY_DIRECTED: "Agents follow authority directives (controlled evacuation)"
    }
    return descriptions.get(policy, "Unknown policy")


