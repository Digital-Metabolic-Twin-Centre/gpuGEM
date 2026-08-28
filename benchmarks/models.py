"""Model registry + canonical LP builder for the cuOpt-vs-Gurobi benchmark.

Every model is converted to the SAME LP with the repository's own loaders
(gpugem.loaders.from_cobra / from_mat), so both solvers receive an identical
problem. BiGG models are cached locally for reproducibility.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

import numpy as np
import scipy.io as sio
import scipy.sparse as sp

import gpugem.loaders as L

HERE = Path(__file__).resolve().parent
CACHE = HERE / "model_cache"
CACHE.mkdir(exist_ok=True)

# All benchmark models are vendored in benchmarks/model_cache so the suite is
# reproducible from a clean checkout. The env vars remain as overrides for
# anyone who keeps the originals elsewhere.
MODELS_DIR = Path(os.environ.get("MWBM_DIR", CACHE))
HARVEY_MAT = Path(os.environ.get("HARVEY_MAT", CACHE / "Harvey_1_03c_reduced.mat"))

# order is cosmetic (dict literal position only) -- the comparison figure sorts by
# each model's actual solved n_cols, not by this field (see make_figure.py)
REGISTRY = {
    "e_coli_core": {"scale": "small",      "order": 0, "kind": "cobra", "source": "e_coli_core"},
    "iML1515":     {"scale": "medium",     "order": 1, "kind": "cobra", "source": "iML1515"},
    "Harvey":      {"scale": "whole-body", "order": 2, "kind": "mat",
                    "source": str(HARVEY_MAT), "model_key": "modelReduced",
                    "objective": "Whole_body_objective_rxn"},
    "S84":         {"scale": "microbiome", "order": 3, "kind": "mat",
                    "source": str(CACHE / "mWBM_S84_male.mat"), "model_key": None, "objective": None},
    "S85":         {"scale": "microbiome", "order": 4, "kind": "mat",
                    "source": str(CACHE / "mWBM_S85_male.mat"), "model_key": None, "objective": None},
    "S9":          {"scale": "microbiome", "order": 5, "kind": "mat",
                    "source": str(CACHE / "mWBM_S9_male.mat"), "model_key": None, "objective": None},
    "S15":         {"scale": "microbiome", "order": 6, "kind": "mat",
                    "source": str(CACHE / "mWBM_S15_male.mat"), "model_key": None, "objective": None},
    "S23":         {"scale": "microbiome", "order": 7, "kind": "mat",
                    "source": str(CACHE / "mWBM_S23_male.mat"), "model_key": None, "objective": None},
    "S83":         {"scale": "microbiome", "order": 8, "kind": "mat",
                    "source": str(CACHE / "mWBM_S83_male.mat"), "model_key": None, "objective": None},
    "Harvetta":    {"scale": "whole-body", "order": 9, "kind": "mat",
                    "source": str(CACHE / "Harvetta_1_03d.mat"), "model_key": "female",
                    "objective": "Whole_body_objective_rxn"},
}

ALL_MODELS = list(REGISTRY.keys())


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _mat_rxns(path, model_key):
    raw = sio.loadmat(str(path), struct_as_record=False, squeeze_me=True)
    if model_key and model_key in raw and hasattr(raw[model_key], "_fieldnames"):
        rx = raw[model_key].rxns
    else:
        rx = raw["rxns"]
    return np.array([str(v) for v in np.asarray(rx).ravel()])


def _load_cobra(name):
    """Load a BiGG model, caching the SBML locally (plain .xml) for reproducibility."""
    import cobra

    cache = CACHE / (name + ".xml")
    if cache.exists():
        return cobra.io.read_sbml_model(str(cache)), cache, False

    model = cobra.io.load_model(name)
    cobra.io.write_sbml_model(model, str(cache))
    return model, cache, True

def build_lp(name):
    """Return (lp_dict, provenance_dict) for a registry model.

    lp_dict has keys S, b, lb, ub, c, maximize and, when coupling/inequality
    rows exist, C, d_lb, d_ub -- exactly what gpugem.solve consumes.
    """
    meta = REGISTRY[name]
    prov = {"model": name, "scale": meta["scale"], "kind": meta["kind"]}

    if meta["kind"] == "cobra":
        model, cache, fetched = _load_cobra(meta["source"])
        lp = L.from_cobra(model)
        prov.update(source=meta["source"], cache=cache.name, sha256=sha256(cache),
                    fetched=fetched, cobra_n_rxns=len(model.reactions),
                    cobra_n_mets=len(model.metabolites))
    else:
        path = meta["source"]
        lp = L.from_mat(path, model_key=meta["model_key"] or "model")
        if meta["objective"]:
            rxns = _mat_rxns(path, meta["model_key"])
            hits = np.where(rxns == meta["objective"])[0]
            if len(hits) == 0:
                raise ValueError("objective reaction %r not found in %s" % (meta["objective"], name))
            idx = int(hits[0])
            c = np.zeros(sp.csr_matrix(lp["S"]).shape[1], dtype=np.float64)
            c[idx] = 1.0
            lp["c"] = c
            lp["maximize"] = True
            prov["objective_rxn"] = meta["objective"]
            prov["objective_idx"] = idx
        prov.update(source=path, sha256=sha256(path))

    S = sp.csr_matrix(lp["S"])
    has_C = lp.get("C") is not None
    nnz = int(S.nnz) + (int(sp.csr_matrix(lp["C"]).nnz) if has_C else 0)
    n_rows = int(S.shape[0]) + (int(sp.csr_matrix(lp["C"]).shape[0]) if has_C else 0)
    prov.update(n_cols=int(S.shape[1]), n_eq_rows=int(S.shape[0]), n_total_rows=n_rows,
                nnz=nnz, obj_nonzero=int(np.count_nonzero(lp["c"])), maximize=bool(lp["maximize"]))
    return lp, prov
