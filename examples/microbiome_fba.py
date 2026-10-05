"""
Example: GPU-accelerated FBA on a personalised microbiome whole-body model.

Models (mWBM_S84_male_lifted.mat etc.) are available on request from the
Virtual Metabolic Human project.  Replace ``MODEL_PATH`` accordingly.
"""

import sys

import gpugem
from gpugem._deps import DependencyError, require

try:
    require("cuopt")   # fail before loading the model if the GPU solver is unusable
except DependencyError as err:
    sys.exit(str(err))

MODEL_PATH = "mWBM_S84_male_lifted.mat"

# Load lifted model (includes evars / ctrs coupling block)
arrays = gpugem.loaders.from_mat(MODEL_PATH)
print(f"  Variables   : {arrays['S'].shape[1]}")
print(f"  Constraints : {arrays['S'].shape[0] + (arrays['C'].shape[0] if 'C' in arrays else 0)}")

# Solve — PaPILO presolve is selected automatically because n_vars > 100K
result = gpugem.solve(**arrays, time_limit=60.0)

print(result)
print(f"  Objective          : {result.objective}")
print(f"  Max stoich residual: {result.feasibility.get('stoich_max_residual', 'N/A'):.2e}")
print(f"  Applied settings   : {result.solver_settings}")

# Override a setting explicitly
result_stable1 = gpugem.solve(**arrays, time_limit=300.0, pdlp_solver_mode=0)
print(f"\nStable1 mode: {result_stable1}")
