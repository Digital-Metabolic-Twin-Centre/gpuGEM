"""
Example: GPU-accelerated FBA on the Harvey whole-body model.

The Harvey model (.mat) is available from the Virtual Metabolic Human database.
Replace ``MODEL_PATH`` with the path to your downloaded file.
"""

import gpugem

MODEL_PATH = "Harvey_1_03c_reduced.mat"

# Load from .mat and solve with auto-selected defaults
arrays = gpugem.loaders.from_mat(MODEL_PATH)
result = gpugem.solve(**arrays)

print(result)
print(f"  Objective          : {result.objective}")
print(f"  Max stoich residual: {result.feasibility.get('stoich_max_residual', 'N/A'):.2e}")
print(f"  Applied settings   : {result.solver_settings}")
