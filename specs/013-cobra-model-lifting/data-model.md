# Phase 1 Data Model: Opt-In Model Lifting for Badly-Scaled LPs

## LiftingMapping

Returned alongside a lifted LP's arrays by `gpugem.lifting`'s transform functions — the metadata
needed to map a lifted solution back to the original variable space and to verify lifting actually
corrected the model's scale (spec FR-005/FR-007). Mirrors `gpugem/scaling.py`'s existing
`CoefficientScalingMapping` dataclass shape (a deliberate, already-established project
convention for this class of object — see research.md R3 for why the two are separate types
despite the similar shape: they describe genuinely different transforms) without being the same
class, since the two algorithms record different per-entry metadata.

| Field | Type | Notes |
|---|---|---|
| `n_original_vars` | `int` | Original model's variable (reaction) count — map-back is `fluxes[:n_original_vars]` (research R5) |
| `n_original_stoich_rows` | `int` | Original `S` row count, before any auxiliary mass-balance rows were appended |
| `n_original_coupling_rows` | `int \| None` | Original `C` row count, if the model has a coupling block |
| `big` | `float` | The magnitude threshold actually used (recorded, not just referenced, so a `LiftingMapping` is self-describing) |
| `mass_balance_lifted_rows` | `list[int]` | Original-`S`-row indices that had at least one large entry and were lifted |
| `coupling_lifted_rows` | `list[int]` | Original-`C`-row indices lifted (empty if the model has no coupling block, or none of its rows matched the targeted pattern) |
| `n_aux_vars` | `int` | Total new auxiliary variables added across both blocks |
| `n_aux_rows` | `int` | Total new auxiliary constraint rows added across both blocks |

## ScaleReport

Returned by the validation entry point (`benchmarks/run_model_lifting_validation.py`) per model —
the explicit, reportable evidence spec FR-007/SC-002 require ("every coefficient... falls within
the configured magnitude threshold... reported explicitly, not just asserted").

| Field | Type | Notes |
|---|---|---|
| `model` | `str` | |
| `big` | `float` | |
| `mass_balance_max_abs_before` | `float` | Largest `\|S\|` entry among rows flagged for lifting, before |
| `mass_balance_max_abs_after` | `float` | Largest `\|S'\|` entry among the *same* rows' descendants, after — MUST be `<= big` |
| `coupling_max_abs_before` | `float \| None` | Same, for the `C` block, `None` if no coupling block |
| `coupling_max_abs_after` | `float \| None` | |
| `n_mass_balance_rows_lifted` | `int` | |
| `n_coupling_rows_lifted` | `int` | |
| `n_aux_vars_added` | `int` | |

## LiftedSolveComparison

Returned by the validation entry point per model — the correctness evidence spec FR-006/SC-001
require: a lifted-and-mapped-back solve compared directly against the same model's unlifted solve.

| Field | Type | Notes |
|---|---|---|
| `model` | `str` | |
| `unlifted_objective` | `float` | |
| `lifted_objective` | `float` | |
| `objective_agrees` | `bool` | Same tolerance this project already uses everywhere (`benchmarks.residual.objectives_agree`) |
| `unlifted_residual_inf` | `float` | Against the original `S`/`b` |
| `lifted_residual_inf` | `float` | Against the original `S`/`b`, using the **mapped-back** fluxes (research R6 — never the lifted system's own internal residual) |
| `verified_correct` | `bool` | `objective_agrees and lifted_residual_inf <= res_tol` — same gate shape used throughout this project's other benchmarks |
| `unlifted_solve_s` | `float` | Recorded for context; NOT a performance claim (spec FR-009 excludes runtime comparison from this feature's own success criteria) |
| `lifted_solve_s` | `float` | Same caveat |
