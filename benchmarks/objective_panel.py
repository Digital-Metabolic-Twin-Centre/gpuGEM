"""Shared helpers for the cross-model objective-panel credibility benchmark.

Generalizes two already-proven, per-model-kind reaction-lookup mechanisms
(benchmarks.models.build_lp's own meta["objective"] branch for kind="mat",
and cobra's model.reactions order for kind="cobra") to accept an arbitrary
objective reaction instead of a single hardcoded one, and loads each model's
already-curated objective panel and already-published solver settings.

See specs/011-objective-panel-benchmark/.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np
import scipy.sparse as sp

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from benchmarks import models as M

CANDIDATES = HERE / "objective_candidates"
RESULTS_MAIN = HERE / "results"


def _build_lp_with_objective(model, reaction_id):
    """Return (lp, prov) for `model` with `reaction_id` as the sole
    (maximized) objective, overriding whatever objective models.build_lp
    set by default. Resolves the reaction's column index per the model's
    kind -- model.reactions order for kind="cobra", benchmarks.models._mat_rxns
    for kind="mat" (research R2)."""
    meta = M.REGISTRY[model]
    lp, prov = M.build_lp(model)
    n = sp.csr_matrix(lp["S"]).shape[1]

    if meta["kind"] == "cobra":
        cobra_model, _, _ = M._load_cobra(meta["source"])
        rxn_ids = [r.id for r in cobra_model.reactions]
        if reaction_id not in rxn_ids:
            raise ValueError("objective reaction %r not found in %s" % (reaction_id, model))
        idx = rxn_ids.index(reaction_id)
    else:
        rxns = M._mat_rxns(meta["source"], meta["model_key"])
        hits = np.where(rxns == reaction_id)[0]
        if len(hits) == 0:
            raise ValueError("objective reaction %r not found in %s" % (reaction_id, model))
        idx = int(hits[0])

    c = np.zeros(n, dtype=np.float64)
    c[idx] = 1.0
    lp["c"] = c
    lp["maximize"] = True
    prov["objective_rxn"] = reaction_id
    prov["objective_idx"] = idx
    return lp, prov


def _load_panel(model):
    """Read benchmarks/objective_candidates/<model>.csv and return a list of
    {"reaction_id":..., "category":...} dicts in file order (research R3 --
    only these two columns are consumed here). Errors clearly if missing."""
    path = CANDIDATES / (model + ".csv")
    if not path.exists():
        raise FileNotFoundError(
            "%s not found -- this feature reads an already-curated objective panel, "
            "it does not generate one" % path)
    panel = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            panel.append({"reaction_id": row["reaction_id"], "category": row["category"]})
    return panel


def _load_settings(model):
    """Read benchmarks/results/<model>.json and return this model's already
    -published reps/time_limit/res_tol/obj_tol (research R1). Errors clearly
    if missing -- this feature reuses published settings, it does not invent
    its own."""
    path = RESULTS_MAIN / (model + ".json")
    if not path.exists():
        raise FileNotFoundError(
            "%s not found -- run benchmarks/run_benchmark.py for %r first "
            "(this feature reuses the main suite's already-published settings)"
            % (path, model))
    d = json.loads(path.read_text())
    return {
        "reps": d["reps"],
        "time_limit": d["time_limit"],
        "res_tol": d["res_tol"],
        "obj_tol": d["obj_tol"],
    }
