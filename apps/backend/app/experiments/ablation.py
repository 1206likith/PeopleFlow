"""
Ablation configuration for simulation components.
"""
from pydantic import BaseModel


class AblationConfig(BaseModel):
    use_social_force: bool = True
    use_pathfinding: bool = True
    use_behavioral_decisions: bool = True
    use_hazard_effects: bool = True
