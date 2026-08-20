# Quickstart: Cross-Model Objective-Panel Credibility Benchmark

## Prerequisites

- This project's existing `benchmarks/` environment, with every model's `results/<model>.json` already
  present (this feature reuses those settings/tolerances, per research R1).
- The ten curated `benchmarks/objective_candidates/<model>.csv` files already committed.
- Gurobi installed and licensed, and cuOpt installed on a GPU host, only if producing fresh results.
  Regenerating the CSVs or figures from committed results needs neither.
- **Expect a long run.** Per research R4, a full `--all` run across every model's objective panel is
  realistically multi-day wall-clock time, dominated by the six large microbiome models. Run one model at
  a time in the background and monitor via the heartbeat prints, rather than expecting a single foreground
  command to finish quickly.

## Produce results for one model (start small)

```sh
python -m benchmarks.run_objective_panel --model e_coli_core
```

Expected: one `benchmarks/results/objective_panel/e_coli_core/<objective_id>.json` per row in
`objective_candidates/e_coli_core.csv` (10 files). This is the fastest model's full panel and a good way to
confirm the pipeline works end-to-end before committing to a large model.

## Produce results for a large microbiome model (background run)

```sh
python -m benchmarks.run_objective_panel --model S85 &
```

Expected: heartbeat lines every 30s while each solve runs (research R4), and one result JSON written per
objective as it completes -- interrupting this process and re-running the same command later resumes from
whichever objectives already have a result file (spec FR-011/SC-004; verify with `ls
benchmarks/results/objective_panel/S85/ | wc -l` before and after an interruption).

## Produce results for every model

```sh
python -m benchmarks.run_objective_panel --all
```

Expected: every model in `benchmarks.models.ALL_MODELS` gets a full set of per-objective results. Given the
realistic runtime (research R4), this is expected to be run over an extended period, model by model, not as
a single sitting.

## Regenerate the comparison CSVs

```sh
python -m benchmarks.aggregate_objective_panel
```

Expected: `benchmarks/results/objective_panel/objective_runtime.csv` and `benchmark_details.csv`, both per
`contracts/csv-columns.md`. Runs without cuOpt or Gurobi installed (spec SC-001) -- verify by running in an
environment with neither importable.

## Regenerate the figures

```sh
python -m benchmarks.make_objective_panel_figures
```

Expected: one `benchmarks/figures/objective_panel_<model>.png` per model with at least one result,
reproducible byte-for-byte from the committed CSVs alone.

## Validate the correctness gate is enforced, not bypassed

Inspect any model's `results/objective_panel/<model>/<objective_id>.json`: it MUST include `both_feasible`
and per-solver `feasible` booleans computed from *every* repeat, not just the median (research R7). Confirm
`benchmark_details.csv` still lists a `both_feasible=False` combination rather than omitting it, if one
exists.

## Validate no previously-published result changed

```sh
git diff --stat benchmarks/results/*.json benchmarks/results/gurobi_default/*.json
```

Expected: no output (spec FR-009/SC-003) -- this feature only reads each model's already-published settings
and results, it never re-solves or overwrites them.

## Validate no shipped default solver behavior changed

```sh
git diff gpugem/_defaults.py benchmarks/solve.py
```

Expected: no output (spec FR-010/SC-005).
