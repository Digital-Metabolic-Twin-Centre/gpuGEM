# Contract: dependency errors

## Public API

```python
gpugem.DependencyError   # subclass of RuntimeError; attributes dependency, kind, detected, required, remedy
```

No other public name is added. `FBASolver`, `solve`, `solve_cobra`, `FBAResult` signatures unchanged.

## Raise points

| Call | Condition | kind |
|---|---|---|
| `solve`, `FBASolver.solve`, `solve_cobra` | cuopt absent | `not_installed` |
| same | cuopt import raises anything but not-found | `broken` |
| same | installed < minimum | `version` |
| same | device probe fails after successful import | `no_gpu` |
| `loaders.from_cobra`, `solve_cobra` | cobra absent | `not_installed` (remedy names extra `gpugem[cobra]`) |
| `loaders.from_mat` | corrupt file / MATLAB v7.3 file | `broken`, names the file and the fix (a missing file stays `FileNotFoundError`) |
| `benchmarks.models` download | network failure | `network` (remedy: place file in `benchmarks/model_cache/`) |

## Message shape

```
gpuGEM cannot run: <dependency> is <state>.
  Needed for: <purpose>
  Fix: <remedy>
  (details: <original exception text, if any>)
```

## Script contract

A benchmark/figure/example script whose dependency is missing exits with code 3 before reading any
model or writing any result, message on stderr in the shape above. (Code 2 is already used by the benchmarks for a failed correctness gate.) Optional metadata probes never
abort; they record `<field>_unavailable_reason`.

## Unchanged

Successful-path numerical output, `FBAResult` fields, `status` values.
