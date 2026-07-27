# Quickstart: S85 Multi-Objective cuOpt vs Gurobi Benchmark

## Prerequisites

- Same GPU host and environment as `002-benchmark-cuopt-gurobi` (NVIDIA GPU + cuOpt, valid
  Gurobi license, `gpugem` installed, repo checked out).
- `MWBM_DIR` pointing at the directory containing `mWBM_S85_male.mat` (same env var
  `benchmarks/models.py` already uses).
- Existing `benchmarks/results/S85.json` from `002` present, so the sweep's baseline objective
  can be cross-checked against it (not required to run, but expected for interpretation).

## 1. Inspect / regenerate the objective set

```bash
python -c "from benchmarks import s85_objectives as O; print(len(O.OBJECTIVES))"
```

Expected: prints `20` (or the actual count if fewer valid candidates exist — see spec Edge
Cases). `benchmarks/results/s85_objectives/objectives.json` is written/refreshed with each
objective's `id`, `reaction`, `category`, `rationale`, `is_baseline`.

## 2. Run the registry validation tests (no GPU required)

```bash
pytest tests/test_s85_objectives.py -v
```

Expected: passes — confirms no duplicate reactions, every reaction resolves in the S85 model,
exactly one `is_baseline`, and the outlier/averaging math is correct on synthetic timing data.

## 3. Run one objective end-to-end (fast sanity check before the full sweep)

```bash
python benchmarks/run_objective_sweep.py --objective whole_body
```

Expected console output (illustrative):
```
[1/1] whole_body (Whole_body_objective_rxn) -- gurobi solving...
[1/1] whole_body -- gurobi done in 52.6s  status=Optimal
[1/1] whole_body (Whole_body_objective_rxn) -- cuopt solving...
[1/1] whole_body -- ...still solving, 30s elapsed
[1/1] whole_body -- ...still solving, 60s elapsed
...
[1/1] whole_body -- cuopt done in 509.4s  status=Optimal
[OK] whole_body  gurobi=52.6s  cuopt=509.4s  ratio=9.68
```
`results/s85_objectives/whole_body.json` is written; its `gurobi`/`cuopt` medians should be
close to the existing `results/S85.json` numbers (~52s / ~509s) since it is the same objective —
this is the check that the new code path reproduces the already-trusted `002` result before
trusting it for the other 19 objectives.

## 4. Run the full sweep (expected: multiple hours)

```bash
nohup python benchmarks/run_objective_sweep.py --all > sweep.log 2>&1 &
tail -f sweep.log
```

Expected: one start/finish pair of lines per objective per solver, in order, with heartbeat
lines during any solve exceeding 30s (spec User Story 2 / SC-002) — sufficient to confirm the
run is progressing rather than hung at any point.

## 5. Resume after an interruption

```bash
python benchmarks/run_objective_sweep.py --all
```

Expected: objectives with an existing JSON print `[skip] <id> (exists; --force to rerun)`;
only the remaining objectives are solved (spec User Story 3 / SC-003).

## 6. Read the aggregated comparison

```bash
python benchmarks/aggregate_sweep.py
column -s, -t < benchmarks/results/s85_objectives/summary.csv | less -S
```

Expected: `summary.json` reports `cuopt_solve_s_mean/median`, `gurobi_solve_s_mean/median`,
`runtime_ratio_median`, `baseline_ratio`, and an `outliers` list — this is the artifact that
answers the motivating question (spec SC-001): whether the baseline's ~10x ratio sits near
`runtime_ratio_median` (gap is real/general) or stands out in `outliers` (gap was
objective-specific).
