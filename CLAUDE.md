# gpuGEM — working rules

GPU-accelerated Flux Balance Analysis for genome-scale metabolic models (cuOpt behind a thin,
COBRApy-compatible wrapper).

`.specify/memory/constitution.md` is authoritative. It is normally read at the `/speckit-plan`
Constitution Check gate — but it binds **all** work, including ad-hoc sessions that never run
`/speckit`. The two principles most often violated outside that gate are reproduced below in
operative form. Read the constitution itself before changing defaults, the public API, or figures.

## Evidence before algorithmic change (Principle VII)

**Do not propose an algorithmic change you have not measured.** LLMs are good at suggesting
algorithm changes; that is exactly why a specific change may only be proposed once numerical
evidence — gathered by running the *current* implementation on this project's real data — shows
it is warranted.

When the evidence needed to choose between options does not exist, **the deliverable is
instrumentation, not an algorithm change**: selectively extend the existing algorithm's
diagnostic output until it produces the evidence that would decide which change is most
beneficial. Then decide.

Three rules that follow, each of which this project has already broken once:

1. **Measure outputs, not only inputs.** Counting what a transform *will* act on is not evidence
   about what it *produced*. Both are required.
2. **Post-conditions cover the whole object and must be able to fail.** Compute them over every
   element — including elements the transform deliberately skipped and auxiliary structure the
   transform itself created — never only the elements it touched. A check scoped so failure is
   impossible is not a check. Failures exit non-zero or fail a test; never a boolean nobody gates
   on.
3. **Report what the transform did NOT do.** Returned metadata records in-scope elements left
   unchanged, and why.

Worked example of the failure mode: `specs/013-cobra-model-lifting` measured which S85 rows its
lifting would select (research.md R2), never measured the result, and scoped `scale_report` to the
rows it had lifted — reporting `coupling_fully_corrected: true` while 37,772 coefficients above the
threshold survived untouched.

## MATLAB ↔ Python translation parity (Principle VIII, NON-NEGOTIABLE)

A translation is proven only by **running both implementations and diffing their real outputs**.
Line-by-line traceability to the source and same-language before/after comparisons are useful, and
are **not** substitutes.

- **Output is a genome-scale model** → compare field by field and element by element. Every matrix
  (`S`, `C`, `E`, `D`, …) on shape, sparsity pattern and every stored value; every vector (`b`,
  `c`, `lb`, `ub`, `d`, `csense`, `dsense`, `rxns`, `mets`, …) elementwise; fields present in one
  and not the other reported as differences. Aggregate summaries (nnz, min/max, row counts) never
  substitute for the elementwise diff.
- **Output is a solution** → compare status, objective, and the full flux vector elementwise
  within the project's correctness tolerance. Matching objectives alone are not sufficient.
- **No environment, no pass.** If this machine cannot run both toolchains, the comparison task is
  **FAILED** — not skipped, waived, or substituted — and the feature is not merged or pushed. An
  Assumption that a toolchain is unavailable identifies work that is not yet done; it does not
  relax the requirement.

## Reporting

State results faithfully. A negative result recorded honestly (see `specs/013`'s tasks.md T020)
is a valid outcome; a green check that could not have gone red is not. New limitations go in
`README.md`'s "Known limitations" (Principle V).

## Practical

- Tests: `python -m pytest tests/ -q`. Lint: `ruff check` (`line-length = 100`). Python floor 3.10.
- `numpy`/`scipy`/`cuopt-cu12` are the only hard deps; `cobra` stays optional.
- Benchmarks read models from `benchmarks/model_cache/`; results are JSON under
  `benchmarks/results/<feature>/`. GPU-dependent tests will fail on a machine without cuOpt —
  report that as unrun, not as passed.
- New features go through `/speckit-specify` → `/speckit-plan` → `/speckit-tasks` →
  `/speckit-implement`.
