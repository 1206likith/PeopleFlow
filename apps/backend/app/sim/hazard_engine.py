import numpy as np
from typing import Tuple, List

class HazardEngine:
    """
    Phase 3: Smoke & Hazard Engine
    Computes real-time spatial smoke propagation using Finite Difference Method
    for the continuous 2D Heat/Diffusion equation: ∂C/∂t = D∇²C + source
    """
    def __init__(self, width: int = 100, height: int = 100, resolution: float = 1.0, diffusion_rate: float = 2.0):
        self.width = width
        self.height = height
        self.resolution = resolution
        self.grid_x = int(width / resolution)
        self.grid_y = int(height / resolution)
        
        # Macroscopic fluid cells representing atmospheric hazard concentration
        self.smoke_grid = np.zeros((self.grid_x, self.grid_y), dtype=np.float32)
        self.diffusion_rate = diffusion_rate
        self.sources: List[Tuple[float, float, float]] = [] # x, y, emission_rate
        
    def add_source(self, x: float, y: float, emission_rate: float):
        """Registers a smoke origin point (like a fire locus)"""
        self.sources.append((x, y, emission_rate))
        
    def update(self, dt: float):
        """Propagates atmospheric diffusion across all fluid cells natively mapped via NumPy."""
        # 1. Add smoke from persistent sources
        for x, y, rate in self.sources:
            gx = int(max(0.0, min(float(self.grid_x - 1), x / self.resolution)))
            gy = int(max(0.0, min(float(self.grid_y - 1), y / self.resolution)))
            self.smoke_grid[gx, gy] += rate * dt
            
        # 2. Fast Finite Difference explicit 5-point diffusion step
        C = self.smoke_grid
        laplacian = (
            np.roll(C, 1, axis=0) + 
            np.roll(C, -1, axis=0) + 
            np.roll(C, 1, axis=1) + 
            np.roll(C, -1, axis=1) - 
            4 * C
        )
        
        # Zero out boundaries to enforce non-wrapping limits (Dirichlet boundaries)
        laplacian[0, :] = 0
        laplacian[-1, :] = 0
        laplacian[:, 0] = 0
        laplacian[:, -1] = 0
        
        self.smoke_grid += self.diffusion_rate * laplacian * dt
        
        # Clamp bounds 0 to 100 concentration limit
        self.smoke_grid = np.clip(self.smoke_grid, 0.0, 100.0)

    def get_concentration(self, x: float, y: float) -> float:
        """Exposes instantaneous local cell toxicity level to Agents routing logic."""
        gx = int(max(0.0, min(float(self.grid_x - 1), x / self.resolution)))
        gy = int(max(0.0, min(float(self.grid_y - 1), y / self.resolution)))
        return float(self.smoke_grid[gx, gy])

    def serialize_grid(self) -> List[List[float]]:
        """Returns raw 2D arrays mapping natively into Unity Shader Graph ingestors."""
        return self.smoke_grid.tolist()
