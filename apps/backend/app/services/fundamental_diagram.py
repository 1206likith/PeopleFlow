class FundamentalDiagram:
    """
    Mathematical engine correlating physical density (persons/m^2) to absolute walking velocity.
    Enforces real-world bottleneck physics based on standard crowd dynamics literature.
    """
    
    @staticmethod
    def compute_speed(density: float, v0: float, rho_max: float = 5.4) -> float:
        """
        Calculates pedestrian speed v(ρ) based on local density ρ.
        v(ρ) = v0 * (1 - ρ / ρ_max)
        
        Args:
            density: Local density in persons per square meter
            v0: Agent's desired free-walking speed
            rho_max: Absolute jam density where movement physically halts
        Returns:
            Computed absolute walking speed (capped minimum to allow shuffle).
        """
        if density >= rho_max:
            return 0.1 # Minimum emergent shuffle speed to prevent zero-lock
        new_v = v0 * (1.0 - (density / rho_max))
        return max(0.1, new_v)

    @staticmethod
    def compute_flow(density: float, v0: float, rho_max: float = 5.4) -> float:
        """
        Computes specific flow q(ρ) = ρ * v(ρ)
        """
        v = FundamentalDiagram.compute_speed(density, v0, rho_max)
        return density * v
