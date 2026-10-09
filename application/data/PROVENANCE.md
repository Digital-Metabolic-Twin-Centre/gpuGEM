# Data provenance

The five files in this directory are the inputs to the candidate-gene
prioritisation application described in the gpuGEM manuscript. They are
MATLAB `.mat` / `.m` files carried over unchanged from the research code in
which the application was developed.

**Licensing.** The gpuGEM source code is MIT licensed (see `LICENSE` at the
repository root). The MIT licence does **not** extend to the model data in
this directory. Harvey and everything derived from it remain subject to the
terms under which the Virtual Metabolic Human resource distributes them. If
you intend to redistribute these files, or to use them commercially, check
those terms at <https://www.vmh.life/> first.

---

## Upstream source

All five files derive from **Harvey version 1.03c**, the male whole-body
metabolic reconstruction distributed through the Virtual Metabolic Human
resource (<https://www.vmh.life/>) and described in Thiele *et al.*,
*Personalized whole-body models integrate metabolism, physiology, and the gut
microbiome*, Molecular Systems Biology (2020) (`thiele_personalized_2020` in
the manuscript bibliography).

The pipeline itself is a Python translation of a COBRA Toolbox
implementation (`heirendt_creation_2019`); see `../README.md`.

---

## Files

| File | SHA-256 (first 16) | Contents |
|---|---|---|
| `Harvey_1_03c_reduced.mat` | `cb095063917b19b3` | Reduced Harvey model, MATLAB struct `modelReduced` |
| `fbaWT_QP_gurobi_Harvey_1_03c.mat` | `cd5943b16e7b933f` | Precomputed wild-type flux vector, struct `fbaWT` |
| `rxnGenMatrixCausalMatrix.mat` | `b8756df85a7299b8` | Causal reaction-to-gene mapping |
| `rxnGenMatrixNonCausalMatrix.mat` | `05cad42a183502e5` | Non-causal reaction-to-gene mapping (fallback) |
| `diseaseListFile.m` | `e2c11e81d4767cd4` | Inherited-metabolic-disease list with gene identifiers |

Full checksums are in `SHA256SUMS`. Verify with `sha256sum -c SHA256SUMS`.

### `Harvey_1_03c_reduced.mat`

A size-reduced form of Harvey 1.03c, prepared in MATLAB with the COBRA
Toolbox. The reduction removed blocked and structurally redundant reactions;
**the reduction script is not part of this repository**, so the reduced model
is distributed as data rather than regenerated. Measured dimensions:

```
S       56,452 x 81,094    283,529 nonzeros    all rows equality (csense 'E'), b = 0
C      103,600 x 81,094    209,602 nonzeros    33,591 rows '>=', 70,009 rows '<=', d = 0
v       81,094 reactions
mets    56,452             of which 979 carry the [bc] (blood compartment) tag
genes    2,071
```

The objective reaction is `Whole_body_objective_rxn`. The all-equality
stoichiometry and the two-sided coupling block are why the model maps
directly onto `gpugem.solve(S, b, lb, ub, c, C=..., d_lb=..., d_ub=...)`
without reformulation.

Total LP size as solved: 81,094 variables and 160,052 constraint rows, plus
one demand column per queried biomarker.

### `fbaWT_QP_gurobi_Harvey_1_03c.mat`

The wild-type reference flux distribution, used as the denominator when
scoring how much each candidate gene knockout reduces biomarker-demand flux.
It is the solution of the minimum-norm QP on the unperturbed model, computed
once with Gurobi so that every query reuses it rather than recomputing it.
81,094 entries, 32,005 of magnitude greater than 1e-6. Entries at or below
1e-6 are zeroed on load, matching the MATLAB original.

Because this is a QP solution rather than an LP vertex it is unique, which
matters: the Harvey LP is degenerate (many optimal vertices at the same
objective value), so an LP-derived wild-type reference would not be
reproducible across solvers.

### `rxnGenMatrixCausalMatrix.mat`, `rxnGenMatrixNonCausalMatrix.mat`

Sparse reaction-by-gene indicator matrices, both 81,094 x 2,071, mapping each
gene to the reactions it controls. The causal matrix (36,098 nonzeros) holds
mappings where the gene is the sole or dominant determinant of the reaction;
the non-causal matrix (95,105 nonzeros) is the permissive mapping used as a
fallback for genes absent from the causal one. Each file also carries the
matching `rxnGenMatrixGenes` and `rxnGenMatrixRxns` label vectors.

### `diseaseListFile.m`

The inherited-metabolic-disease list, a MATLAB cell array of
`{disease name, gene id, abbreviation, gene symbol}` rows. 2,100 rows
covering 1,818 distinct gene identifiers.

Narrowing to what the model can actually score: 781 of those 1,818 genes
appear in the reaction-gene matrices at all, 758 have at least one reaction
under either mapping, and **449 have at least one *causal* reaction**. Those
449 are the candidate set the application ranks, and they are the "449
disease genes" quoted in the manuscript. Genes without a causal mapping fall
back to the non-causal matrix.

---

## What is not here

* **No solver licence file.** The research code read Gurobi WLS credentials
  from a `.lic` file beside the model data. That path has been removed. The
  application uses whatever licence your own Gurobi installation is
  configured with and never reads credentials from this repository.
* **No precomputed knockout signatures.** `precompute_knockouts.py`
  regenerates them; see `../README.md` for the cost.
* **No patient data.** The biomarker profiles used in the manuscript are
  given as command-line strings, not as a dataset.
