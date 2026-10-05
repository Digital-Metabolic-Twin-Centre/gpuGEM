"""gpuGEM — GPU-accelerated Flux Balance Analysis for genome-scale metabolic models."""

from gpugem._deps import DependencyError, require as _require

# numpy/scipy are hard dependencies; fail here with guidance, not with a bare ImportError below.
# cuOpt is deliberately NOT checked at import: it is required only when a solve is requested.
_require("numpy")
_require("scipy")

from gpugem.solver import FBASolver, solve  # noqa: E402
from gpugem.solve_cobra import solve_cobra  # noqa: E402
from gpugem.result import FBAResult  # noqa: E402
from gpugem.scaling import CoefficientScalingMapping, remap_fluxes, scale_model  # noqa: E402
from gpugem.lifting import LiftingMapping, lift_coupling, lift_mass_balance, map_back  # noqa: E402
from gpugem import loaders  # noqa: E402

__version__ = "0.1.0"
__all__ = [
    "DependencyError",
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
