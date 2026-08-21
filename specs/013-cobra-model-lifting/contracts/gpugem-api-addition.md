# API Contract: `gpugem.solve()`'s new `lift`/`lift_big` parameters

## Signature change (additive only)

```python
def solve(
    S, b, lb, ub, c, *,
    C=None, d_lb=None, d_ub=None,
    maximize=False,
    time_limit=60.0,
    check_feasibility=True,
    lift: bool = False,        # NEW
    lift_big: float = 1000.0,  # NEW
    **cuopt_kwargs,
) -> FBAResult:
```

- `lift=False` (default): behavior is **byte-for-byte identical** to today's `solve()` — no
  existing caller is affected. `lift_big` is ignored when `lift=False`.
- `lift=True`: before building cuOpt's `DataModel`, `S`/`b`/`C`/`d_lb`/`d_ub` are replaced with
  their lifted equivalents (via `gpugem.lifting`), using `lift_big` as the magnitude threshold.
  cuOpt solves the lifted system. Before returning, `FBAResult.fluxes` is truncated to the
  original variable count (`gpugem.lifting`'s map-back, a literal prefix slice — research.md R5),
  and `FBAResult.feasibility` is recomputed against the **original**, unlifted `S`/`b`/`C` using
  the truncated fluxes (research.md R6) — never the lifted system's own internal residual.
- `lift`/`lift_big` are consumed by `solve()` itself and are **never** forwarded into
  `**cuopt_kwargs`/`SolverSettings.set_parameter` — they are gpuGEM-level pre/post-processing
  controls, not cuOpt solver parameters.

## Inherited, zero-code-change support

Per research.md R4 (confirmed by direct code reading, not assumed):

- `gpugem.solve_cobra(model, lift=True)` — already works once `solve()` has the parameter, since
  `solve_cobra` forwards `**cuopt_kwargs` straight through.
- `gpugem.FBASolver(S, b, lb, ub, c, lift=True)` (as a stored default) or
  `.solve(lift=True)` (per-call override) — already works for the same reason
  (`FBASolver` stores and merges `**cuopt_kwargs`).

No changes to `solve_cobra.py` or the `FBASolver` class are part of this contract — their existing
`**kwargs`-forwarding behavior is the mechanism, not something this feature adds.

## `FBAResult` — unchanged schema, clarified existing contract

No new field is added. Two existing fields' behavior under `lift=True` is clarified (not changed
in shape):

- `fluxes`: already documented as "in the original variable space" — under `lift=True` this
  continues to hold exactly (map-back guarantees it), it just now also covers the internally-lifted
  case, not only the never-lifted case the docstring was originally written for.
- `feasibility`: computed against the original model regardless of whether `lift` was used
  internally — a caller cannot tell, from `FBAResult`'s shape alone, whether lifting happened
  internally; they can only tell that the diagnostics describe the model they asked to solve.

## `gpugem.lifting` — new public module

```python
def lift_mass_balance(S, b, big=1000.0) -> tuple[S_lifted, b_lifted, LiftingMapping]
def lift_coupling(C, d_lb, d_ub, big, mapping) -> tuple[C_lifted, d_lb_lifted, d_ub_lifted, LiftingMapping]
def map_back(fluxes_lifted, mapping) -> np.ndarray   # prefix slice
```

Exported from `gpugem/__init__.py` alongside the existing `scale_model`/`remap_fluxes`/
`CoefficientScalingMapping` exports (same pattern, different names, per research.md R3 — the two
families are never merged into one).
