# Quickstart: validating this feature

Prerequisites: a venv with `pip install -e ".[dev]"` (this machine currently lacks `pytest`).
cuOpt is **not** required for steps 1–4; step 5 needs a GPU machine.

1. **Package imports without the solver**
   `python -c "import gpugem"` → exits 0 even with cuOpt absent.
2. **Guided error for a missing solver**
   `python -c "import numpy as np, scipy.sparse as sp, gpugem; gpugem.solve(sp.eye(1), np.zeros(1), np.zeros(1), np.ones(1), np.ones(1))"`
   On a machine without cuOpt: a `gpugem.DependencyError` whose text contains `cuopt`, `Needed for`,
   and `pip install`. No raw `ModuleNotFoundError` as the last line.
3. **Simulated failures (any machine)**
   `python -m pytest tests/test_dependency_errors.py tests/test_dependency_inventory.py -q`
   Expect all pass; temporarily adding `import foo_bar` to any scanned file must make the
   inventory test fail (confirm once manually, then revert).
4. **Script exit**
   `python benchmarks/run_highs_baseline.py` without `highspy` → exit code 3 (`echo $?`), message
   names `highspy` and the install command, no results file written.
5. **Equipped machine regression (GPU required — report as UNRUN if unavailable)**
   `python -m pytest tests/ -q` and one benchmark run; objectives/residuals identical to the
   committed results (SC-005).
6. **GPU-less machine with cuOpt installed (R3 open item)** — run step 2 and record the observed
   exception and resulting `kind`; update README limitation accordingly. Not satisfied by simulation.
