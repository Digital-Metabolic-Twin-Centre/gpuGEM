# Quickstart: S85 Alternative Solver-Mode Experiment

## Prerequisites

- Same GPU host and environment as `002`/`003` (NVIDIA GPU + cuOpt, valid Gurobi license,
  `gpugem` installed with the `solved_by` addition from this feature, repo checked out).
- `MWBM_DIR` pointing at the directory containing `mWBM_S85_male.mat`.
- The `003` sweep's `whole_body` objective result (`benchmarks/results/s85_objectives/
  whole_body.json`) present for a sanity cross-check, though not required to run.

## 1. Confirm the variant registry against cuOpt's live parameter list

```bash
python -c "
from cuopt.linear_programming.solver_settings.solver_settings import get_solver_parameter_names
from benchmarks.solver_mode_variants import SOLVER_MODE_VARIANTS
names = set(get_solver_parameter_names())
for v in SOLVER_MODE_VARIANTS:
    bad = [k for k in v['cuopt_kwargs'] if k not in names]
    assert not bad, (v['id'], bad)
print('all variant kwargs are real cuOpt parameters')
"
```

## 2. Run the registry + comparison-math tests (no GPU required)

```bash
pytest tests/test_solver_mode_variants.py tests/test_solver.py -v
```

Expected: passes — confirms the variant registry is well-formed, the speedup/best-candidate math
is correct on synthetic data, and `FBAResult.solved_by` behaves as documented
(`contracts/gpugem-api-addition.md`).

## 3. Sanity-check the baseline variant alone

```bash
python -m benchmarks.run_solver_mode_experiment --force
```
(first run — nothing exists yet, so this runs all 4; for a baseline-only sanity check, temporarily
comment out the other 3 in `solver_mode_variants.py`, or just let it run to completion per step 4)

Expected: `results/s85_solver_modes/baseline.json` has `solve_s` close to the existing
`results/s85_objectives/whole_body.json` cuOpt figure (~509-520s) and `solved_by="PDLP"` — this is
the check that the new subprocess-based worker reproduces the already-trusted result before
trusting it for the untested candidates.

## 4. Run the full experiment (expected: baseline ~500s + 3 candidates, each up to ~15min budget)

```bash
python -m benchmarks.run_solver_mode_experiment
```

Expected console output (illustrative):
```
[gurobi] reference solve: 54.2s  objective=1.0
[1/4] baseline    -- launching subprocess (time_limit=900s)...
[1/4] baseline    -- Completed in 512.3s  status=Optimal  solved_by=PDLP
[2/4] methodical1 -- launching subprocess (time_limit=900s)...
[2/4] methodical1 -- Completed in 341.7s  status=Optimal  solved_by=PDLP
[3/4] concurrent  -- launching subprocess (time_limit=900s)...
[3/4] concurrent  -- Completed in 58.9s   status=Optimal  solved_by=Barrier
[4/4] barrier_cold -- launching subprocess (time_limit=900s)...
[4/4] barrier_cold -- DidNotComplete (crashed, exit=-9) -- likely OOM, see results JSON
wrote results/s85_solver_modes/summary.json
```
(Numbers above are illustrative placeholders, not a prediction of the real outcome — that's what
running this answers.)

## 5. Resume after an interruption

```bash
python -m benchmarks.run_solver_mode_experiment
```

Expected: variants with an existing JSON print `[skip] <id> (exists; --force to rerun)`; only
missing variants are (re-)run.

## 6. Read the comparison

```bash
python -m benchmarks.aggregate_solver_modes
column -s, -t < benchmarks/results/s85_solver_modes/summary.csv | less -S
```

Expected: `summary.json` reports `best_candidate_id`/`best_candidate_speedup` if any candidate
beat the baseline while remaining `verified_correct`, or states plainly that none did — this is
the artifact that answers the motivating question (spec SC-001).
