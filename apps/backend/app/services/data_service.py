from typing import Any, Dict, List

from app.services.simulation_data_repository import get_simulation_data_repository


async def save_simulation_data(simulation_id: str, data: Dict[str, Any]) -> str:
    """Persist simulation metadata records through the repository boundary."""
    repository = await get_simulation_data_repository()
    return await repository.create(simulation_id, data)


async def get_simulation_data(simulation_id: str) -> List[Dict[str, Any]]:
    """Fetch simulation metadata records through the repository boundary."""
    repository = await get_simulation_data_repository()
    return await repository.list(simulation_id)

