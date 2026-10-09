# Application: candidate-gene prioritisation from patient biomarkers

This directory holds the application reported in the gpuGEM manuscript. It is
self-contained: the model data, the pipeline and the reference results are all
here, so the published application results can be reproduced from this
repository alone.

**What it does.** Given a patient's blood biomarker pattern, it ranks
inherited-metabolic-disease genes by how far that pattern suppresses the
metabolic flux each gene controls. A gene whose reactions carry substantial
flux in the healthy reference but little or none under the patient's
constraints is a strong causal candidate.

The workflow is translated from a COBRA Toolbox implementation and runs on the
Harvey whole-body metabolic model (81,094 reactions, 56,452 metabolites).
gpuGEM's role is the expensive step: the genome-scale linear programme that has
to be re-solved every time the biomarker profile changes.

## How it works

Each query runs four stages.

1. **Load** the Harvey model, the precomputed wild-type flux vector and the
   disease list.
2. **Constrain and solve the LP.** Each biomarker becomes an objective term:
   an elevated metabolite gets a demand reaction rewarded for carrying flux, a
   depleted one is rewarded for the opposite. Maximising that objective finds
   the flux distribution that best explains the observed pattern. **This is the
   stage gpuGEM accelerates.**
3. **Re-solve as a minimum-norm QP** pinned at the LP optimum. This matters for
   correctness, not speed: the LP optimal face of this model is highly
   degenerate, so without it the reported fluxes depend on which vertex the
   solver happened to stop at, and the ranking is not reproducible across
   solvers. This stage uses Gurobi in both configurations (see
   [Solver requirements](#solver-requirements)).
4. **Score and rank** every candidate gene by its flux reduction.

Only stage 2 differs between the two backends, which is what makes the GPU and
CPU rankings directly comparable.

## Install

From the repository root:

```bash
pip install -e .                 # gpuGEM itself
pip install gurobipy             # required: see Solver requirements
```

gpuGEM's GPU path additionally needs `cuopt-cu12` on a CUDA 12 machine with an
NVIDIA GPU. The `gurobi` backend and every offline check run without a GPU.

## Run

```bash
cd application/src

# GPU LP (default backend)
python run_candidate_genes.py "C02470[bc],incr;kynate[bc],incr" \
    --label kynurenic --out ../results/kynurenic_gpugem.csv

# CPU baseline, for comparison
python run_candidate_genes.py "C02470[bc],incr;kynate[bc],incr" \
    --backend gurobi --label kynurenic --out ../results/kynurenic_gurobi.csv
```

Or from Python:

```python
from cugem_app import run_query

result = run_query("phe_L[bc],increased;tyr_L[bc],decreased", backend="gpugem")
print(result.summary())          # stage timings and solver settings
print(result.ranking.head(10))   # the ranked candidates
```

### Biomarker syntax

A semicolon-separated list of `metabolite,direction` tokens:

```
"phe_L[bc],increased;tyr_L[bc],decreased"
```

Directions accept `incr`/`increased`/`increase`/`up` and
`decr`/`decreased`/`decrease`/`down`. Two compartments are handled:

| Tag | Meaning | Effect on the model |
|---|---|---|
| `[bc]` | blood compartment | adds a demand reaction `DM_<met>` |
| `[u]` | urine | retunes the existing `EX_<met>` exchange reaction |

Tokens naming an unknown metabolite are reported as warnings and skipped, so a
partially recognised profile still runs. A query with no usable token raises.

### Output

A CSV ranked by `FluxReductionPercentage` descending, ties broken by
`sumFluxWT`. The columns are documented in the docstring of
`cugem_app.scoring.score_genes`. The ones that matter:

| Column | Meaning |
|---|---|
| `FluxReductionPercentage` | `100 * (1 - abs(sumFluxD) / abs(sumFluxWT))`, the ranking key |
| `sumFluxWT`, `sumFluxD` | summed flux through the gene's reactions, wild-type and patient |
| `NRxns`, `AvgFluxWT` | reaction count and per-reaction mean wild-type flux |
| `Causal` | `False` if the gene was only found via the non-causal fallback mapping |

A note on reading the ranking: genes expressed across many organs accumulate
large flux sums simply because the whole-body model replicates their reactions
per tissue, and a full knockout gives exactly 100% for every gene it hits, so
the tie-break on `sumFluxWT` does real work at the top of the table.
`AvgFluxWT` is reported alongside for that reason.

## Solver requirements

**Gurobi is required, for both backends.** The minimum-norm QP in stage 3 has
no GPU path: forming its normal-equations matrix on the Harvey model produces
roughly 5.2e8 nonzeros, which cuOpt's direct solver cannot allocate regardless
of free device memory. A GPU QP path is future work. What the backend switch
selects is which solver runs the *LP*:

| Backend | Stage 2 (LP) | Stage 3 (QP) |
|---|---|---|
| `gpugem` | gpuGEM / cuOpt PDLP on the GPU | Gurobi |
| `gurobi` | Gurobi dual simplex | Gurobi |

No licence credentials are stored in this repository. The application creates a
default Gurobi environment, which picks up whatever licence your own
installation is configured with (`GRB_LICENSE_FILE`, `~/gurobi.lic`, or a Web
Licence Service configuration). Gurobi's free academic licence covers models of
this size.

### Solver settings

The application overrides **no** solver parameters beyond a time limit.
gpuGEM's size-adaptive defaults for a model of this size already resolve to the
configuration the manuscript reports: PDLP in double precision, primal and dual
tolerances of 1e-8, with max-norm convergence checking. The application
therefore exercises the package exactly as shipped.

One correction worth recording, since the research code this was ported from
says otherwise in a comment: cuOpt's `pdlp_precision=1` is its **Double** mode,
not a mixed FP32/FP64 mode. Single precision does not converge at the
tolerances this model needs. gpuGEM's defaults carry the corrected reading.

## Data

Five files in [`data/`](data), 8.5 MB total, documented in
[`data/PROVENANCE.md`](data/PROVENANCE.md) with checksums in
[`data/SHA256SUMS`](data/SHA256SUMS).

The disease list names 1,818 distinct genes. Of these, 781 appear in the
reaction-gene matrices and **449 carry at least one causal reaction mapping**;
those 449 are the candidate set the application can score. Genes without a
causal mapping fall back to the non-causal matrix.

The wild-type reference is a precomputed minimum-norm (QP) solution rather than
an LP vertex, for the same degeneracy reason that stage 3 exists: a vertex is
not reproducible across solvers on this model.

## Tests

```bash
python application/tests/smoke_test.py
```

Covers everything that needs neither a GPU nor a Gurobi licence: loading, the
wild-type objective setup, biomarker parsing, the array augmentation handed to
`gpugem.solve`, and the scoring stage. It runs in a few seconds under 0.2 GB.

Two of its checks are worth knowing about, because they pin down assumptions
the GPU backend relies on:

- The model's stoichiometric rows are all equalities and its coupling rows are
  all one-sided, so it maps onto `gpugem.solve`'s `S v = b` plus two-sided
  coupling block with **no reformulation**. The backend raises a clear error
  rather than silently mis-stating the problem if that ever stops being true.
- Scoring is checked against two analytically known cases: halving every flux
  must give a uniform 50% reduction, and a total knockout must give 100% for
  every gene with ties ordered by `sumFluxWT`.

## Layout

```
application/
  data/        Harvey model, wild-type flux, reaction-gene matrices,
               disease list, PROVENANCE.md, SHA256SUMS
  src/
    run_candidate_genes.py   command-line entry point
    cugem_app/
      data.py                model and disease-list loading
      biomarkers.py          biomarker string -> model modifications
      gpugem_backend.py      the GPU LP, via gpugem.solve
      gurobi_backend.py      the CPU LP and the minimum-norm QP
      scoring.py             gene ranking
      pipeline.py            the four stages, with the backend switch
  tests/       smoke_test.py
  results/     reference results from the published runs
  figures/     timing comparison figure
```
