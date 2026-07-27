# summary.csv columns (contract)

variant_id, is_baseline, outcome, outcome_reason,
solve_s, status, solved_by, iters, residual_inf, verified_correct,
speedup_vs_baseline, is_best_candidate

- Exactly 4 rows: `baseline`, `methodical1`, `concurrent`, `barrier_cold` — always present
  regardless of outcome (spec Edge Cases: a crashed/timed-out variant is reported, not dropped).
- `speedup_vs_baseline` = `baseline_solve_s / solve_s`; empty for the baseline row itself and for
  any row with `outcome != Completed`.
- `is_best_candidate` = `True` for at most one row: the `verified_correct` candidate with the
  highest `speedup_vs_baseline` among those `> 1`. `False` for every row (including baseline) if
  no candidate qualifies.
- Times in seconds, solver call only (matches `002`/`003`'s convention).
