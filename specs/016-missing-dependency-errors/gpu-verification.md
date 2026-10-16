# GPU verification of the released package (tasks T015, T016)

Date: 2026-10-14. Package under test: `gpugem==0.1.2` installed **from TestPyPI** (the same two files
that were uploaded for PyPI, built from tag `v0.1.2`) into a fresh venv. Tests and benchmark code came
from a clone of tag `v0.1.2` with its own `gpugem/` directory deleted, so every import resolved to the
installed package (asserted in the script: `"site-packages" in gpugem.__file__`).

Machine: NVIDIA RTX A4500 (20 GB, compute capability 8.6), driver 560.35.05, CUDA 12.6, Python 3.12.3,
Linux 6.5. The machine is shared; another user's process was on the GPU during the small and Harvey runs
but not during the final large-model run. Installed: cuopt-cu12 26.6.0, cobra 0.32.1, numpy 2.4.6,
scipy 1.18.1.

## Test suite

`pytest` on the tag: 197 passed, 2 skipped (Gurobi, not installed), 1 failed. The failure was
`test_import_time_checked_dependencies_are_checked`, which reads the source file `gpugem/__init__.py`
that this setup had deleted. With the source restored that file's 14 tests pass. Effective result:
**198 passed, 2 skipped**. The CPU-only machine gives 190 passed, 10 skipped; the 8 cuOpt tests that
skip without a GPU pass here.

## Models (objective and stoichiometric residual only)

Compared with the committed Gurobi objective in `benchmarks/results/<model>.json`, using the
tolerances stored there (objective 1e-6, residual 1e-4). Shipped defaults, `time_limit` as noted.
PASS requires status Optimal, objective within tolerance and residual within tolerance.

| Model | Rows x cols | Status | Objective | Residual | Solve (s) | Time limit | Committed solve (s) | PASS |
|---|---|---|---|---|---|---|---|---|
| e_coli_core | 72 x 95 | Optimal | 0.8739215057 | 7.8e-9 | 0.46 | 300 | 0.25 | yes |
| iML1515 | 1,877 x 2,712 | Optimal | 0.8769971988 | 3.0e-9 | 3.7 | 300 | 3.75 | yes |
| Harvey | 56,452 x 81,094 | Optimal | 1.0 | 5.6e-9 | 5.9 | 300 | 1.67 | yes |
| Harvetta | 58,851 x 83,521 | Optimal | 1.0 | 3.2e-9 | 4.9 | 300 | 1.42 | yes |
| S9 | 944,232 x 1,111,943 | Optimal | 1.0 | 5.56e-5 | 533.7 | 900 | 534.4 | yes |
| S15 | 918,715 x 1,084,341 | Optimal | 1.0 | **9.94e-5** | 299.4 | 900 | 295.3 | yes (margin 0.6%) |
| S23 | 848,878 x 1,007,742 | Optimal | 1.0 | 1.74e-5 | **881.7** | 900 | 739.9 | yes (time margin 2%) |

Residuals for S9 and S15 equal the committed values to every printed digit.

## What went wrong along the way, and what it means

- A first run of S9/S15/S23 used a 300 s limit that I chose without checking the committed solve times.
  S9 returned `TimeLimit` with residual 0.0497. That was an invalid test (the committed S9 solve takes 534 s),
  not a defect; the run was stopped and repeated with the committed 900 s limit.
- S23 finished in 881.7 s against a 900 s limit. It passed, but any slowdown (a shared GPU, a different
  driver) could make it return `TimeLimit`. The committed run took 739.9 s. Treat S23 as near the limit.
- Small-model and Harvey/Harvetta timings are slower than the committed ones; the GPU was shared at the time.
  No performance claim is made from this run.

## Not covered

- Only objective and residual were compared; no flux vector was compared elementwise (reference flux vectors
  for these models are not in the committed results).
- S83, S84, S85 and the Gurobi side were not run.
- One GPU model, one driver and one cuOpt version (26.6.0).
- `no_gpu` detection with a working `nvidia-smi` but a broken CUDA setup is still untested.

Files: `gpu-verification/` (result JSON, pytest log, the script used).
