# CLI Contract: cuOpt-Native Settings Tuning

## `python -m benchmarks.run_cuopt_tuning`

```text
--baseline              Solve the fresh baseline candidate only (large-model default, unchanged)
--settings              Run every User-Story-1 settings-sweep candidate (research.md R2/R3/R4)
--upgrade-venv PATH     Re-run the baseline + best verified-correct settings candidate(s) under
                         the cuOpt release installed at PATH's venv (User Story 2). PATH must
                         already exist (provisioned separately per quickstart.md's setup step —
                         this command does not create the venv itself, keeping "provision an
                         isolated env" and "run candidates in it" as separately-reviewable steps)
--preprocessing          Run the one last-resort preprocessing candidate (User Story 3). Only
                         meaningful — and only prints a non-trivial result — once --settings and
                         --upgrade-venv results already exist; does not block on that, but the
                         final report labels a preprocessing result found without them as
                         "evaluated out of order"
--all                    --baseline, then --settings, then --preprocessing (never --upgrade-venv,
                         which always needs an explicit, pre-provisioned PATH)
--force                  Re-run a candidate whose results/cuopt_tuning/<id>.json already exists
--time-limit SECONDS     cuOpt-level time limit per candidate phase (default 900.0, matching 002/
                         004/010/011's convention)
```

Skips a candidate whose `results/cuopt_tuning/<id>.json` already exists unless `--force` — same
resumability convention as every other `benchmarks/run_*.py` script in this project.

Calls `aggregate_cuopt_tuning.main()` at the end, same as `run_objective_panel.py` does for its
own aggregator (011's established pattern).

## `python -m benchmarks.aggregate_cuopt_tuning`

No arguments. Reads whichever `results/cuopt_tuning/<id>.json` files exist, writes
`results/cuopt_tuning/summary.json` and `summary.csv`. No GPU/Gurobi required — regenerable from
committed results alone, matching `aggregate_solver_modes.py`/`aggregate_objective_panel.py`'s
existing contract.

## Exit codes

- `0`: every requested candidate produced a `CandidateResult` (a candidate that failed its
  correctness gate or timed out is still success at the CLI level — it produced a result, it's
  just `verified_correct=False`; per spec Edge Cases this is expected, honest output, not a CLI
  failure).
- Non-zero: a candidate's subprocess could not even be launched (e.g. `--upgrade-venv PATH` where
  `PATH` doesn't exist) — a setup problem distinct from an experimental outcome.
