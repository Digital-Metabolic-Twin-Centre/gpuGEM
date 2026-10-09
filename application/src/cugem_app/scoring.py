"""
Ranking of candidate disease genes by flux reduction.

For each gene on the inherited-metabolic-disease list, the reactions it
controls are read off the reaction-gene matrix (causal mapping first,
non-causal as a fallback). The gene's summed flux through those reactions is
compared between the wild-type reference and the patient-constrained solution.
Genes whose flux collapses the most are the strongest candidates.

This reproduces the scoring of the COBRA Toolbox implementation, including its
filters and its tie-breaking sort order.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import scipy.sparse as sp

from cugem_app.data import FLUX_TOL, DiseaseEntry, PrecomputedData, WBModel

#: Fluxes with magnitude at or below this are treated as exactly zero.
ZERO_TOL = 1e-6

#: A gene is only reported if its flux fell by at least this much (or to zero).
MIN_FLUX_DIFFERENCE = 1e-3


def build_reaction_index(wbm: WBModel, precomp: PrecomputedData) -> tuple[np.ndarray, np.ndarray]:
    """
    Map rows of the reaction-gene matrix onto columns of the model.

    Returns ``(rg_to_wbm, valid_rows)``: the model reaction index for each
    matrix row (-1 where the reaction is absent from this reduced model) and a
    boolean mask of the rows that did resolve.
    """
    rxn_to_idx = {r: i for i, r in enumerate(wbm.rxns)}
    rg_to_wbm = np.array([rxn_to_idx.get(r, -1) for r in precomp.rxnGenRxns])
    return rg_to_wbm, rg_to_wbm >= 0


def _gene_reactions(
    matrix: sp.csc_matrix, col: int, rg_to_wbm: np.ndarray, valid_rows: np.ndarray
) -> np.ndarray:
    rows = matrix[:, col].nonzero()[0]
    return rows[valid_rows[rows]]


def score_genes(
    wbm: WBModel,
    precomp: PrecomputedData,
    disease_list: list[DiseaseEntry],
    patient_flux: np.ndarray,
    *,
    objective_value: float = np.nan,
    patient_label: str = "patient",
    use_noncausal_fallback: bool = False,
) -> pd.DataFrame:
    """
    Rank candidate genes for one patient.

    ``patient_flux`` is the minimum-norm flux vector from the QP step, over the
    model's own reactions (demand columns excluded).

    Returns a DataFrame sorted by ``FluxReductionPercentage`` descending, with
    ``sumFluxWT`` breaking ties. Columns:

    ``Disease``, ``Gene``, ``DiseaseGene``
        Identity of the candidate, from the disease list.
    ``sumFluxWT``, ``sumFluxD``
        Summed flux through the gene's reactions, wild-type and patient.
    ``FluxDifference``
        ``sumFluxWT - sumFluxD``.
    ``FluxReductionPercentage``
        ``100 * (1 - |sumFluxD| / |sumFluxWT|)``; the ranking key.
    ``NRxns``, ``AvgFluxWT``
        Reaction count and per-reaction mean wild-type flux. Genes replicated
        across many organs accumulate large sums, so the mean is reported for
        context; see the note on the alternative sort below.
    ``Causal``
        False if the gene was only found in the non-causal fallback mapping.
    ``CompositeScore``, ``objD``
        Diagnostics carried over from the original implementation.
    ``IEMRxns``
        Semicolon-separated reaction identifiers behind the score.
    """
    wt_flux = precomp.fbaWT_v
    rg_to_wbm, valid_rows = build_reaction_index(wbm, precomp)
    gene_cols = {g: i for i, g in enumerate(precomp.rxnGenGenes)}

    rows: list[dict] = []
    for entry in disease_list:
        col = gene_cols.get(entry.gene_id)
        if col is None:
            continue

        gene_rows = _gene_reactions(precomp.rxnGenMatrix, col, rg_to_wbm, valid_rows)
        causal = True
        if (len(gene_rows) == 0 and use_noncausal_fallback
                and precomp.rxnGenMatrixNonCausal is not None):
            gene_rows = _gene_reactions(
                precomp.rxnGenMatrixNonCausal, col, rg_to_wbm, valid_rows
            )
            causal = False
        if len(gene_rows) == 0:
            continue

        idx = rg_to_wbm[gene_rows]

        sum_wt = float(np.sum(wt_flux[idx]))
        if abs(sum_wt) <= FLUX_TOL:
            continue  # gene carries no wild-type flux; nothing to reduce

        sum_d = float(np.sum(patient_flux[idx]))
        if abs(sum_d) <= ZERO_TOL:
            sum_d = 0.0

        ratio = (sum_wt / sum_d) if sum_d != 0.0 else np.inf

        rows.append({
            "Disease": entry.name,
            "Gene": entry.gene_symbol,
            "DiseaseGene": entry.gene_id,
            "PatientQuery": patient_label,
            "sumFluxWT": sum_wt,
            "sumFluxD": sum_d,
            "NRxns": len(idx),
            "Causal": causal,
            "objD": objective_value,
            "FluxDifference": sum_wt - sum_d,
            "CompositeScore": (sum_wt - sum_d) * ratio,
            "IEMRxns": ";".join(wbm.rxns[idx]),
        })

    result = pd.DataFrame(rows)
    if result.empty:
        return result

    # Keep genes that were knocked out entirely, or whose flux genuinely moved.
    result = result[
        (result["sumFluxD"] == 0) | (result["FluxDifference"] >= MIN_FLUX_DIFFERENCE)
    ]
    # Keep only reductions: patient flux strictly smaller in magnitude than WT.
    result = result[result["sumFluxD"].abs() < result["sumFluxWT"].abs()]

    result["FluxReductionPercentage"] = 100 * (
        1 - result["sumFluxD"].abs() / result["sumFluxWT"].abs()
    )
    result["AvgFluxWT"] = result["sumFluxWT"] / result["NRxns"]

    # Published sort. Ties on the reduction percentage (common, because a full
    # knockout gives exactly 100%) are broken by total wild-type flux.
    #
    # Sorting on AvgFluxWT instead down-weights genes replicated across many
    # organs, but introduces false positives for high-flux narrow genes. The
    # manuscript reports the sum; change the key here to explore the other.
    result = result.sort_values(
        ["FluxReductionPercentage", "sumFluxWT"], ascending=False
    ).reset_index(drop=True)

    column_order = [
        "Disease", "Gene", "DiseaseGene", "PatientQuery",
        "FluxReductionPercentage", "sumFluxWT", "sumFluxD", "FluxDifference",
        "NRxns", "AvgFluxWT", "Causal", "CompositeScore", "objD", "IEMRxns",
    ]
    return result[column_order]
