# Quickstart: Opt-In Model Lifting for Badly-Scaled LPs

## Prerequisites

- Repo checked out, `gpugem` installed with this feature's additions.
- For the S85 validation step: same GPU host and environment as prior benchmark features (NVIDIA
  GPU + cuOpt, S85's `.mat` file resolvable via `benchmarks.models.build_lp("S85")`, matching
  every other feature that already validates against this model).
- No MATLAB/Octave required — see `research.md` R7 for why (traceable translation +
  hand-verifiable linear algebra + solve-and-compare, not a live reference-output diff).

## 1. Run the unit tests (no GPU required)

```bash
pytest tests/test_lifting.py -v
```

Expected: passes — confirms the mass-balance transform, the coupling transform, and the map-back
slice are each correct on small, hand-verified examples (research.md R7 layer 2), and that
`gpugem.solve(..., lift=True)` round-trips correctly end-to-end on `e_coli_core`.

## 2. Confirm lifting is a safe no-op on a well-conditioned small model

```bash
python -c "
import gpugem, cobra
model = cobra.io.read_sbml_model('e_coli_core.xml')  # or wherever this project caches it
r_unlifted = gpugem.solve_cobra(model)
r_lifted   = gpugem.solve_cobra(model, lift=True)
print(r_unlifted)
print(r_lifted)
assert abs(r_unlifted.objective - r_lifted.objective) < 1e-9
"
```

Expected: both results report the same objective; `lift=True` introduces zero auxiliary
variables for this model (no coefficient exceeds the default `lift_big=1000.0`).

## 3. Run the full validation against S85 (badly-scaled, both blocks exercised)

```bash
python -m benchmarks.run_model_lifting_validation --model S85
python -m benchmarks.run_model_lifting_validation --model e_coli_core
```

Expected console output (illustrative, not a prediction):
```
[S85] unlifted: objective=1.0  solve_s=513.5s  residual=8.87e-05
[S85] lifting: 1234 mass-balance rows lifted, 68259 coupling rows lifted, 45678 aux vars added
[S85] scale check: mass-balance max|coef| 2.0e+05 -> 987.3 (<= big=1000.0)
[S85] scale check: coupling max|coef|     2.0e+04 -> 912.1 (<= big=1000.0)
[S85] lifted+mapped-back: objective=1.0  solve_s=...s  residual=...
[OK] S85 verified-correct: lifted result matches unlifted within tolerance
wrote benchmarks/results/model_lifting/S85.json
```

Expected: `[OK] verified-correct` for both models; the scale-check lines show every
previously-badly-scaled coefficient now `<= lift_big` (spec FR-007/SC-002); a `[FAILED]` line and
non-zero exit would mean the translation has a bug — this is not a case where "close enough" is
acceptable (spec FR-006 Acceptance Scenario 3).

## 4. Inspect what changed structurally

```bash
python -c "
import json
d = json.loads(open('benchmarks/results/model_lifting/S85.json').read())
print('n_aux_vars_added:', d['scale_report']['n_aux_vars_added'])
print('mass_balance max before/after:', d['scale_report']['mass_balance_max_abs_before'],
      '->', d['scale_report']['mass_balance_max_abs_after'])
"
```

Expected: a concrete before/after coefficient-range comparison — the artifact spec SC-002 asks
for, committed alongside the correctness result so both can be reviewed together.

## Not covered by this quickstart

Runtime/performance comparison between lifted and unlifted solves is explicitly out of this
feature's scope (spec FR-009) — `unlifted_solve_s`/`lifted_solve_s` are recorded in the output for
context only, not as a claim either is faster. That comparison is deferred future work.
