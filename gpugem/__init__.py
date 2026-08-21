"""gpuGEM — GPU-accelerated Flux Balance Analysis for genome-scale metabolic models."""

from gpugem.solver import FBASolver, solve
from gpugem.solve_cobra import solve_cobra
from gpugem.result import FBAResult
from gpugem.scaling import CoefficientScalingMapping, remap_fluxes, scale_model
from gpugem.lifting import LiftingMapping, lift_coupling, lift_mass_balance, map_back
from gpugem import loaders

__version__ = "0.1.0"
__all__ = [
    "FBASolver",
    "solve",
    "solve_cobra",
    "FBAResult",
    "CoefficientScalingMapping",
    "scale_model",
    "remap_fluxes",
    "LiftingMapping",
    "lift_mass_balance",
    "lift_coupling",
    "map_back",
    "loaders",
]
