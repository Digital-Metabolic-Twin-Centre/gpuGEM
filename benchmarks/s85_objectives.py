"""Objective registry for the S85 multi-objective cuOpt-vs-Gurobi sweep.

Answers: is S85's ~10x cuOpt/Gurobi runtime gap (measured on the single
whole-body objective in the 002 cross-scale benchmark) an artifact of that one
objective, or does it hold across the model's biologically distinct
objectives? Every entry here is an existing single-reaction objective already
present in mWBM_S85_male.mat -- selected for diversity across organ systems,
immune-cell types, and gut-microbiome taxa (see specs/003-.../research.md R1),
not constructed or reweighted.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import scipy.sparse as sp

import gpugem.loaders as L
from benchmarks import models as M

HERE = Path(__file__).resolve().parent
RESULTS_DIR = HERE / "results" / "s85_objectives"
OBJECTIVES_JSON = RESULTS_DIR / "objectives.json"

# id, reaction (exact rxns[] id in mWBM_S85_male.mat), category, rationale, is_baseline
OBJECTIVES = [
    {"id": "whole_body", "reaction": "Whole_body_objective_rxn",
     "category": "whole_body", "is_baseline": True,
     "rationale": "The model's own shipped objective; same reaction used for S85 in the "
                  "002 cross-scale benchmark, included so the sweep average can be compared "
                  "back to that ~10x result directly."},

    {"id": "liver_biomass", "reaction": "Liver_biomass_maintenance",
     "category": "organ_biomass", "is_baseline": False,
     "rationale": "Liver is the model's largest, most metabolically central organ "
                  "compartment (highest reaction count of any organ)."},
    {"id": "kidney_biomass", "reaction": "Kidney_biomass_maintenance",
     "category": "organ_biomass", "is_baseline": False,
     "rationale": "Kidney is the second-largest organ compartment and central to "
                  "whole-body nitrogen/electrolyte handling."},
    {"id": "brain_biomass", "reaction": "Brain_biomass_maintenance",
     "category": "organ_biomass", "is_baseline": False,
     "rationale": "Brain has distinct, highly constrained energy metabolism "
                  "(near-exclusive glucose/ketone use) vs. other organs."},
    {"id": "heart_biomass", "reaction": "Heart_biomass_maintenance",
     "category": "organ_biomass", "is_baseline": False,
     "rationale": "Heart is a large, continuously-active muscle compartment with "
                  "fatty-acid-dominant metabolism."},
    {"id": "muscle_biomass", "reaction": "Muscle_biomass_maintenance",
     "category": "organ_biomass", "is_baseline": False,
     "rationale": "Skeletal muscle is the largest body-mass compartment overall, "
                  "dominant in whole-body amino-acid/glucose turnover."},
    {"id": "colon_biomass", "reaction": "Colon_biomass_maintenance",
     "category": "organ_biomass", "is_baseline": False,
     "rationale": "Colon sits directly at the host-microbiome interface, coupling "
                  "host metabolism to gut microbial exchange."},
    {"id": "pancreas_biomass", "reaction": "Pancreas_biomass_maintenance",
     "category": "organ_biomass", "is_baseline": False,
     "rationale": "Pancreas governs whole-body glucose homeostasis (insulin/glucagon "
                  "producing tissue)."},
    {"id": "lung_biomass", "reaction": "Lung_biomass_maintenance",
     "category": "organ_biomass", "is_baseline": False,
     "rationale": "Lung is a large, distinct gas-exchange compartment with its own "
                  "surfactant/lipid metabolism."},
    {"id": "skin_biomass", "reaction": "Skin_biomass_maintenance",
     "category": "organ_biomass", "is_baseline": False,
     "rationale": "Skin is a large peripheral compartment, structurally and "
                  "metabolically distinct from internal organs."},
    {"id": "adipocytes_biomass", "reaction": "Adipocytes_biomass_maintenance",
     "category": "organ_biomass", "is_baseline": False,
     "rationale": "Adipose tissue is the body's primary lipid-storage compartment, "
                  "metabolically distinct from lean organs."},

    {"id": "bcells_biomass", "reaction": "Bcells_biomass_maintenance",
     "category": "immune_cell_biomass", "is_baseline": False,
     "rationale": "B cells represent adaptive humoral immunity, a small peripheral "
                  "compartment contrasting with the large organ objectives."},
    {"id": "cd4tcells_biomass", "reaction": "CD4Tcells_biomass_maintenance",
     "category": "immune_cell_biomass", "is_baseline": False,
     "rationale": "CD4+ T cells represent adaptive cell-mediated immunity."},
    {"id": "nkcells_biomass", "reaction": "Nkcells_biomass_maintenance",
     "category": "immune_cell_biomass", "is_baseline": False,
     "rationale": "NK cells represent innate lymphoid immunity, distinct lineage "
                  "from the adaptive T/B-cell objectives."},
    {"id": "monocyte_biomass", "reaction": "Monocyte_biomass_maintenance",
     "category": "immune_cell_biomass", "is_baseline": False,
     "rationale": "Monocytes represent innate myeloid immunity and phagocytic "
                  "metabolism, distinct from lymphoid cell types."},
    {"id": "platelet_biomass", "reaction": "Platelet_biomass_maintenance_noTrTr",
     "category": "immune_cell_biomass", "is_baseline": False,
     "rationale": "Platelets are anucleate blood cells with minimal biosynthetic "
                  "machinery -- the smallest, most constrained objective in the set."},

    {"id": "microbe_bacteroides_fragilis", "reaction": "panBacteroides_fragilis_biomassPan",
     "category": "microbiome", "is_baseline": False,
     "rationale": "Common gut commensal/opportunistic pathogen; representative "
                  "Bacteroidetes-phylum taxon."},
    {"id": "microbe_faecalibacterium_prausnitzii",
     "reaction": "panFaecalibacterium_prausnitzii_biomassPan",
     "category": "microbiome", "is_baseline": False,
     "rationale": "Major butyrate-producing commensal, widely used as a marker of "
                  "gut health in microbiome studies."},
    {"id": "microbe_escherichia_coli", "reaction": "panEscherichia_coli_biomassPan",
     "category": "microbiome", "is_baseline": False,
     "rationale": "Facultative anaerobe and common gut pathobiont; representative "
                  "Proteobacteria-phylum taxon."},
    {"id": "microbe_akkermansia_muciniphila",
     "reaction": "panAkkermansia_muciniphila_biomassPan",
     "category": "microbiome", "is_baseline": False,
     "rationale": "Mucin-degrading commensal associated with host metabolic health; "
                  "representative Verrucomicrobia-phylum taxon."},
]

_MODEL_NAME = "S85"


def _rxns():
    meta = M.REGISTRY[_MODEL_NAME]
    return M._mat_rxns(meta["source"], meta["model_key"])


def validate_objectives():
    """Raise ValueError if OBJECTIVES violates data-model.md's rules."""
    reactions = [o["reaction"] for o in OBJECTIVES]
    if len(set(reactions)) != len(reactions):
        dupes = {r for r in reactions if reactions.count(r) > 1}
        raise ValueError("duplicate objective reaction(s): %s" % dupes)

    baselines = [o for o in OBJECTIVES if o["is_baseline"]]
    if len(baselines) != 1:
        raise ValueError("expected exactly one is_baseline=True entry, found %d" % len(baselines))

    rxns = _rxns()
    missing = [r for r in reactions if r not in set(rxns)]
    if missing:
        raise ValueError("objective reaction(s) not found in S85 model: %s" % missing)

    if len(OBJECTIVES) < 20:
        raise ValueError(
            "only %d objectives defined (< 20); if this is intentional because fewer "
            "valid candidates exist in the model, update this check's threshold and "
            "document why in this module's docstring" % len(OBJECTIVES))


def write_objectives_json():
    """Serialize OBJECTIVES to results/s85_objectives/objectives.json."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    OBJECTIVES_JSON.write_text(json.dumps(OBJECTIVES, indent=2))
    return OBJECTIVES_JSON


def get_objective(objective_id):
    for o in OBJECTIVES:
        if o["id"] == objective_id:
            return o
    raise KeyError("unknown objective id %r" % objective_id)


def build_lp_for_objective(objective_id):
    """Return (lp_dict, provenance_dict) for S85 with the given objective's
    reaction set as the sole nonzero maximization objective.

    Mirrors benchmarks.models.build_lp's single-objective-override pattern
    (used there for Harvey's Whole_body_objective_rxn) but resolves the
    reaction index from the OBJECTIVES registry instead of a hardcoded name.
    """
    obj = get_objective(objective_id)
    meta = M.REGISTRY[_MODEL_NAME]
    path = meta["source"]

    lp = L.from_mat(path, model_key=meta["model_key"] or "model")
    rxns = _rxns()
    hits = np.where(rxns == obj["reaction"])[0]
    if len(hits) == 0:
        raise ValueError("objective reaction %r not found in %s" % (obj["reaction"], _MODEL_NAME))
    idx = int(hits[0])
    n = sp.csr_matrix(lp["S"]).shape[1]
    c = np.zeros(n, dtype=np.float64)
    c[idx] = 1.0
    lp["c"] = c
    lp["maximize"] = True

    S = sp.csr_matrix(lp["S"])
    has_C = lp.get("C") is not None
    nnz = int(S.nnz) + (int(sp.csr_matrix(lp["C"]).nnz) if has_C else 0)
    n_rows = int(S.shape[0]) + (int(sp.csr_matrix(lp["C"]).shape[0]) if has_C else 0)
    prov = {
        "model": _MODEL_NAME, "scale": meta["scale"], "kind": meta["kind"],
        "source": path, "sha256": M.sha256(path),
        "n_cols": int(S.shape[1]), "n_eq_rows": int(S.shape[0]), "n_total_rows": n_rows,
        "nnz": nnz, "obj_nonzero": int(np.count_nonzero(lp["c"])), "maximize": True,
        "objective_id": obj["id"], "objective_rxn": obj["reaction"], "objective_idx": idx,
    }
    return lp, prov


if __name__ == "__main__":
    validate_objectives()
    p = write_objectives_json()
    print("validated %d objectives; wrote %s" % (len(OBJECTIVES), p))
