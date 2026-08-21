# Quickstart: cuOpt-Native Settings Tuning for Large Microbiome Models

## Prerequisites

- Same GPU host and environment as `002`/`004`/`010`/`011` (NVIDIA GPU + cuOpt 26.6.0, valid
  Gurobi license, repo checked out). Confirmed single-GPU host (`nvidia-smi`): one RTX A4500,
  20 GB.
- S85's `.mat` file resolvable the same way `002` already does (`MWBM_DIR` or the committed
  `benchmarks/model_cache/` copy).
- S85's already-published Gurobi result (`benchmarks/results/S85.json`) present — this feature
  never re-solves Gurobi, only reads it as the correctness oracle (research.md R7).

## 1. Confirm the candidate registry against cuOpt's live parameter list

```bash
python -c "
from cuopt.linear_programming.solver_settings.solver_settings import get_solver_parameter_names
from benchmarks.cuopt_tuning_candidates import CANDIDATES
names = set(get_solver_parameter_names())
for c in CANDIDATES:
    bad = [k for k in c['cuopt_kwargs'] if k not in names]
    assert not bad, (c['id'], bad)
print('all', len(CANDIDATES), 'candidates use real cuOpt parameters')
"
```

## 2. Run the registry + ranking-math tests (no GPU required)

```bash
pytest tests/test_cuopt_tuning.py -v
```

Expected: passes — confirms the candidate registry is well-formed (including warm-start pairing),
and the speedup/ranking math is correct on synthetic data.

## 3. Sanity-check the fresh baseline alone

```bash
python -m benchmarks.run_cuopt_tuning --baseline
```

Expected: `results/cuopt_tuning/baseline.json` has `solve_s` close to the already-published
`results/S85.json` cuOpt figure (~505-520s per `specs/004-.../research.md`'s own baseline
cross-check) — the same "reproduce the trusted number before trusting anything new" check `004`
already established.

## 4. Run the full settings sweep (User Story 1)

```bash
python -m benchmarks.run_cuopt_tuning --settings
```

Expected console output (illustrative, not a prediction):
```
[1/12] baseline              -- launching subprocess (time_limit=900s)...
[1/12] baseline              -- Completed in 509.4s  status=Optimal
[2/12] pdlp_mode_fast1       -- Completed in 210.8s  status=Optimal   [verified_correct]
[3/12] pdlp_precision_mixed  -- Completed in 480.1s  status=Optimal   [verified_correct]
[4/12] pdlp_precision_single -- Completed in 900.0s  status=TimeLimit [NOT verified_correct]
[5/12] presolve_pslp_retest  -- Completed in 44.2s    status=Infeasible [NOT verified_correct]
[6/12] warm_start_stable2    -- cold phase 512.0s, warm phase 88.3s   [verified_correct]
...
wrote results/cuopt_tuning/summary.json
```

## 5. Evaluate the cuOpt 26.8.0 upgrade (User Story 2) — isolated venv, never the shared env

```bash
python3 -m venv /tmp/cuopt-26.8-venv
/tmp/cuopt-26.8-venv/bin/pip install cuopt-cu12==26.8.0 numpy scipy
python -m benchmarks.run_cuopt_tuning --upgrade-venv /tmp/cuopt-26.8-venv
```

Expected: re-runs the baseline and the best verified-correct settings candidate(s) from step 4
under `26.8.0`, writing `results/cuopt_tuning/<id>_26.8.0.json` alongside the `26.6.0` results —
never overwriting them. The shared conda `base` environment used by every other published
benchmark is untouched (verify: `python -c "import cuopt; print(cuopt.__version__)"` outside the
venv still prints `26.6.0` after this step).

## 6. Evaluate the preprocessing fallback (User Story 3) — only if 4/5 produced no win

```bash
python -m benchmarks.run_cuopt_tuning --preprocessing
```

Expected: the one candidate's reconstructed result is checked against the correctness gate
**before** its speed is reported at all (spec FR-008/SC-003) — if `reconstruction_verified=False`,
the result is recorded as disqualified, and no speed number is treated as meaningful.

## 7. Resume after an interruption

```bash
python -m benchmarks.run_cuopt_tuning --all
```

Expected: candidates with an existing JSON print `[skip] <id> (exists; --force to rerun)`; only
missing candidates are (re-)run — same resumability convention as `002`/`004`/`010`/`011`.

## 8. Read the final ranked comparison

```bash
python -m benchmarks.aggregate_cuopt_tuning
column -s, -t < benchmarks/results/cuopt_tuning/summary.csv | less -S
```

Expected: `summary.json` reports the best verified-correct candidate across all attempted user
stories (or states plainly that none beat the baseline, matching `004`'s honest-null-result
precedent) — this is the artifact that answers the motivating question (spec SC-001/SC-004). It
also prints, as its own headline line, whether **any** verified-correct candidate actually beats
Gurobi (`speedup_vs_gurobi > 1`) — the project's real preferred goal for whole-body/microbiome
models, not just an improvement over cuOpt's own prior baseline.
