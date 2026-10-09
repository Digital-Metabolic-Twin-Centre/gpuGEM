"""
Gene-knockout signatures: precomputation and query.

This is the second half of the application. Where :mod:`cugem_app.pipeline`
answers "given this patient, which genes lose the most flux?" one query at a
time, this module precomputes a reusable table so that ranking becomes a
numpy lookup with no solve at all.

The aggregation that makes it affordable
----------------------------------------
The naive formulation asks, for every (gene, metabolite) pair, whether
knocking out the gene changes that metabolite's producibility: roughly 450
genes x 979 blood metabolites, about 221,000 LPs. Instead, one LP per gene
maximises the *sum* of all 979 blood demand fluxes at once, and every
metabolite is classified from that single solution. The solve count drops to
one per gene, roughly 450. This is the reduction the manuscript refers to.

Classification
--------------
Each metabolite is compared between its wild-type and knockout state. The
three-way rule exists because a zero flux in an LP solution is ambiguous: it
can mean "cannot be produced" or "can be produced, but this particular optimal
vertex happens not to". The reduced cost separates the two.

===========================  =======================================  ======
Wild-type state              Knockout condition                       Signal
===========================  =======================================  ======
produced (flux > BC_TOL)     ko/wt < RATIO_LO                         -1
produced (flux > BC_TOL)     ko/wt > RATIO_HI                         +1
degenerate (flux 0, RC ~ 0)  no longer producible                     -1
not producible               flux > BC_TOL or RC ~ 0                  +1
===========================  =======================================  ======

Why this stage has no GPU path
------------------------------
It depends on reduced costs, and on dual-simplex warm starts between
consecutive knockouts. Reduced costs are a property of a basic solution;
cuOpt's PDLP is a first-order method that returns primal and dual iterates but
no basis and no reduced costs, and it has no warm-start interface. The
aggregation above is therefore a Gurobi-only algorithm by construction, not an
accident of how it was written. gpuGEM accelerates the per-query LP in
:mod:`cugem_app.pipeline`; this precomputation is CPU work, run once.

Run the precomputation once::

    python precompute_knockouts.py --workers 2

then query it as often as you like::

    python query_knockouts.py "phe_L[bc],increased;tyr_L[bc],decreased"
"""

from __future__ import annotations

import copy
import json
import multiprocessing as mp
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import scipy.sparse as sp

from .data import (
    DEFAULT_DATA_DIR,
    WHOLE_BODY_KEYWORD,
    load_disease_list,
    load_model,
    load_precomputed,
)

DEFAULT_SIGNATURE_FILE = DEFAULT_DATA_DIR / "knockout_signatures.npz"
DEFAULT_NAME_CACHE = DEFAULT_DATA_DIR / "bc_met_names.json"

BC_TOL = 1e-6      # demand flux at or below this counts as zero
RC_TOL = 1e-6      # |reduced cost| below this counts as degenerate, not blocked
RATIO_LO = 0.5     # ko/wt below this is a decrease
RATIO_HI = 2.0     # ko/wt above this is an increase

DIRECTION_MAP = {
    "incr": 1, "increased": 1, "increase": 1, "up": 1,
    "decr": -1, "decreased": -1, "decrease": -1, "down": -1,
}


@dataclass
class KnockoutSignatures:
    """The precomputed table and the metadata needed to interpret it."""

    gene_ids: np.ndarray           # (n_genes,) disease gene identifiers
    bc_met_ids: np.ndarray         # (n_bc,) blood-compartment metabolite ids
    wt_bc_flux: np.ndarray         # (n_bc,) wild-type production, 1.0 sentinel
    signatures: sp.csr_matrix      # (n_genes, n_bc) int8 of -1 / 0 / +1
    infeasible: np.ndarray         # (n_genes,) knockout made the model infeasible


# --------------------------------------------------------------------------
# Precomputation
# --------------------------------------------------------------------------

def _add_bc_demand_vars(grb, bc_rows: np.ndarray, met_ids: np.ndarray) -> list:
    """
    Add one demand variable per blood metabolite, each with objective 1.

    Maximising their sum is what lets a single LP report on every metabolite.
    """
    dm_vars = [
        grb.addVar(lb=0.0, ub=1000.0, obj=1.0, name=f"DM_{met_id}")
        for met_id in met_ids
    ]
    grb.update()
    for var, row in zip(dm_vars, bc_rows):
        constr = grb.getConstrByName(f"s{int(row)}")
        if constr is None:
            raise RuntimeError(
                f"Stoichiometric row s{int(row)} not found; the base model was "
                "not built by gurobi_backend.build_base_model()."
            )
        grb.chgCoeff(constr, var, -1.0)
    grb.update()
    return dm_vars


def _build_scan_model(data_dir: Path):
    """
    Build the whole-body LP with the objective pinned, ready for demand vars.

    Returns ``(grb, env, wbm, bc_rows, orig_lb, orig_ub)``. The bounds are kept
    so a knockout can be undone without rebuilding the model.
    """
    from gurobipy import GRB

    from .gurobi_backend import build_base_model, make_env

    wbm = copy.copy(load_model(data_dir))
    whole_mask = np.array([WHOLE_BODY_KEYWORD in r for r in wbm.rxns])
    wbm.lb, wbm.ub = wbm.lb.copy(), wbm.ub.copy()
    wbm.c = np.zeros(wbm.n_rxns, dtype=float)
    wbm.lb[whole_mask] = 1.0
    wbm.ub[whole_mask] = 1.0
    wbm.c[whole_mask] = 1.0
    wbm.osenseStr = "max"

    bc_rows = np.array([i for i, m in enumerate(wbm.mets) if "[bc]" in m])

    env = make_env()
    grb, _ = build_base_model(wbm, env, print_level=0)
    grb.ModelSense = GRB.MAXIMIZE
    grb.Params.Method = 1        # dual simplex: warm-starts across knockouts
    grb.Params.TimeLimit = 120.0

    all_vars = grb.getVars()[: wbm.n_rxns]
    orig_lb = np.array([v.LB for v in all_vars])
    orig_ub = np.array([v.UB for v in all_vars])
    return grb, env, wbm, bc_rows, orig_lb, orig_ub


def scan_wildtype(data_dir: Path = DEFAULT_DATA_DIR, *, verbose: bool = True):
    """
    Solve the wild-type sum-max LP and classify every blood metabolite.

    Returns ``(bc_rows, bc_met_ids, wt_flux, wt_active)``. ``wt_flux`` is the
    LP value and is zero both for degenerate and for non-producible
    metabolites; ``wt_active`` is what separates them.
    """
    from gurobipy import GRB

    grb, env, wbm, bc_rows, _, _ = _build_scan_model(data_dir)
    n_bc = len(bc_rows)
    if verbose:
        print(f"  wild-type scan: {n_bc} blood metabolites, one LP")

    dm_vars = _add_bc_demand_vars(grb, bc_rows, wbm.mets[bc_rows])
    grb.optimize()
    if grb.Status not in (GRB.OPTIMAL, GRB.SUBOPTIMAL):
        raise RuntimeError(f"wild-type scan LP failed with Gurobi status {grb.Status}")

    wt_flux = np.zeros(n_bc, dtype=float)
    wt_active = np.zeros(n_bc, dtype=bool)
    for k, var in enumerate(dm_vars):
        if var.X > BC_TOL:
            wt_flux[k], wt_active[k] = var.X, True
        elif abs(var.RC) < RC_TOL:
            wt_active[k] = True      # producible, but this vertex chose zero

    bc_met_ids = wbm.mets[bc_rows]
    grb.dispose()
    env.dispose()
    if verbose:
        print(f"  producible: {wt_active.sum()}/{n_bc} "
              f"(carrying flux: {(wt_flux > BC_TOL).sum()})")
    return bc_rows, bc_met_ids, wt_flux, wt_active


def _classify(dm_vars, wt_flux_all, wt_active_all, n_bc) -> np.ndarray:
    """Apply the three-way rule to one solved knockout LP."""
    sig = np.zeros(n_bc, dtype=np.int8)
    for i, (var, wt_flux, wt_active) in enumerate(
        zip(dm_vars, wt_flux_all, wt_active_all)
    ):
        ko_flux, ko_rc = var.X, var.RC
        ko_active = (ko_flux > BC_TOL) or (abs(ko_rc) < RC_TOL)
        if wt_flux > BC_TOL:
            ratio = ko_flux / wt_flux
            if ratio < RATIO_LO:
                sig[i] = -1
            elif ratio > RATIO_HI:
                sig[i] = 1
        elif wt_active:
            if not ko_active:
                sig[i] = -1
        elif ko_active:
            sig[i] = 1
    return sig


def _worker(chunk, worker_id, data_dir, bc_rows, bc_met_ids,
            wt_flux, wt_active, n_bc, queue) -> None:
    """Score one chunk of genes in its own process."""
    from gurobipy import GRB

    grb, env, wbm, _, orig_lb, orig_ub = _build_scan_model(data_dir)
    all_vars = grb.getVars()
    dm_vars = _add_bc_demand_vars(grb, bc_rows, bc_met_ids)

    gene_ids_out, sig_rows, infeasible_flags = [], [], []
    t0 = time.time()

    for k, (gene_id, gene_symbol, rxn_indices) in enumerate(chunk):
        for idx in rxn_indices:
            v = all_vars[int(idx)]
            v.LB = v.UB = 0.0
        grb.update()
        grb.optimize()

        infeasible = grb.Status not in (GRB.OPTIMAL, GRB.SUBOPTIMAL)
        if infeasible:
            # An essential gene. Everything producible in the wild type is lost.
            sig = np.where(wt_active, -1, 0).astype(np.int8)
        else:
            sig = _classify(dm_vars, wt_flux, wt_active, n_bc)

        for idx in rxn_indices:
            v = all_vars[int(idx)]
            v.LB, v.UB = float(orig_lb[idx]), float(orig_ub[idx])
        grb.update()

        gene_ids_out.append(gene_id)
        sig_rows.append(sig)
        infeasible_flags.append(infeasible)

        eta = (time.time() - t0) / (k + 1) * (len(chunk) - k - 1)
        print(f"  [w{worker_id} {k + 1}/{len(chunk)}] {gene_symbol:12s} "
              f"down={int((sig == -1).sum()):3d} up={int((sig == 1).sum()):3d} "
              f"eta {eta / 60:.1f}min", flush=True)

    queue.put((worker_id, gene_ids_out, sig_rows, infeasible_flags))
    grb.dispose()
    env.dispose()


def candidate_genes(data_dir: Path = DEFAULT_DATA_DIR):
    """
    The genes the precomputation will knock out.

    A gene qualifies if it is named by the disease list, has a column in the
    causal reaction-gene matrix, and at least one of those reactions survives
    into the reduced model.
    """
    precomp = load_precomputed(data_dir, wt_method="QP")
    diseases = load_disease_list(data_dir)
    wbm = load_model(data_dir)

    rxn_index = {r: i for i, r in enumerate(wbm.rxns)}
    rg_to_wbm = np.array([rxn_index.get(r, -1) for r in precomp.rxnGenRxns])
    valid = rg_to_wbm >= 0

    seen: set[str] = set()
    out: list[tuple[str, str, np.ndarray]] = []
    for entry in diseases:
        if entry.gene_id in seen:
            continue
        col = np.where(precomp.rxnGenGenes == entry.gene_id)[0]
        if not len(col):
            continue
        rows = precomp.rxnGenMatrix[:, col[0]].nonzero()[0]
        rows = rows[valid[rows]]
        if not len(rows):
            continue
        seen.add(entry.gene_id)
        out.append((entry.gene_id, entry.gene_symbol, rg_to_wbm[rows]))
    return out


def precompute_signatures(
    data_dir: Path = DEFAULT_DATA_DIR,
    out_file: Optional[Path] = None,
    n_workers: int = 2,
) -> Path:
    """
    Build the knockout signature table and save it as a compressed .npz.

    ``n_workers`` processes solve disjoint chunks of genes. Keep it at or below
    the concurrency your Gurobi licence allows; each worker holds its own
    environment and model.
    """
    out_file = Path(out_file) if out_file else DEFAULT_SIGNATURE_FILE

    bc_rows, bc_met_ids, wt_flux, wt_active = scan_wildtype(data_dir)
    n_bc = len(bc_rows)

    # query_signatures distinguishes producible from not by a positive value,
    # so degenerate metabolites get a sentinel rather than their literal zero.
    wt_max = wt_flux.copy()
    wt_max[wt_active & (wt_flux <= BC_TOL)] = 1.0

    genes = candidate_genes(data_dir)
    print(f"  knockouts: {len(genes)} genes x {n_bc} metabolites, "
          f"{n_workers} worker(s)")

    args = (data_dir, bc_rows, bc_met_ids, wt_flux, wt_active, n_bc)
    if n_workers == 1:
        queue: mp.Queue = mp.Queue()
        _worker(genes, 0, *args, queue)
        results = [queue.get()]
    else:
        size = (len(genes) + n_workers - 1) // n_workers
        chunks = [genes[i:i + size] for i in range(0, len(genes), size)]
        ctx = mp.get_context("spawn")
        queue = ctx.Queue()
        procs = [ctx.Process(target=_worker, args=(ch, wid, *args, queue))
                 for wid, ch in enumerate(chunks)]
        for pr in procs:
            pr.start()
        results = [queue.get() for _ in procs]
        for pr in procs:
            pr.join()

    results.sort(key=lambda r: r[0])
    gene_ids, sigs, infeasible = [], [], []
    for _, gids, rows, flags in results:
        gene_ids.extend(gids)
        sigs.extend(rows)
        infeasible.extend(flags)

    matrix = sp.csr_matrix(np.vstack(sigs), dtype=np.int8)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        out_file,
        gene_ids=np.array(gene_ids),
        bc_met_ids=np.asarray(bc_met_ids, dtype=str),
        wt_bc_flux=wt_max,
        sig_data=matrix.data,
        sig_indices=matrix.indices,
        sig_indptr=matrix.indptr,
        sig_shape=np.array(matrix.shape),
        infeasible=np.array(infeasible),
    )
    print(f"  wrote {len(gene_ids)} signatures to {out_file} "
          f"({int(np.sum(infeasible))} essential)")
    return out_file


# --------------------------------------------------------------------------
# Query
# --------------------------------------------------------------------------

def load_signatures(sig_file: Path = DEFAULT_SIGNATURE_FILE) -> KnockoutSignatures:
    """Read back the table written by :func:`precompute_signatures`."""
    sig_file = Path(sig_file)
    if not sig_file.exists():
        raise FileNotFoundError(
            f"No knockout signatures at {sig_file}. Build them first with\n"
            "    python precompute_knockouts.py"
        )
    npz = np.load(sig_file, allow_pickle=False)
    return KnockoutSignatures(
        gene_ids=npz["gene_ids"].astype(str),
        bc_met_ids=npz["bc_met_ids"].astype(str),
        wt_bc_flux=npz["wt_bc_flux"],
        signatures=sp.csr_matrix(
            (npz["sig_data"], npz["sig_indices"], npz["sig_indptr"]),
            shape=tuple(npz["sig_shape"]), dtype=np.int8,
        ),
        infeasible=npz["infeasible"].astype(bool),
    )


def parse_directions(biomarker_str: str) -> dict[str, int]:
    """Parse ``"met[bc],incr;met[bc],decr"`` into ``{met_id: +1/-1}``."""
    out: dict[str, int] = {}
    for token in biomarker_str.split(";"):
        token = token.strip()
        if not token:
            continue
        parts = token.split(",")
        direction = DIRECTION_MAP.get(parts[1].strip().lower()) if len(parts) > 1 else None
        if direction is not None:
            out[parts[0].strip()] = direction
    return out


def query_signatures(
    biomarker_str: str,
    patient_label: str = "patient",
    sig_file: Path = DEFAULT_SIGNATURE_FILE,
    data_dir: Path = DEFAULT_DATA_DIR,
    min_wt_production: float = 1e-6,
    exclude_infeasible: bool = True,
):
    """
    Rank diseases by how well each gene's knockout signature matches the
    patient's biomarker directions. No solve: this is a table lookup.

    ``MatchScore`` is the fraction of queried biomarkers whose direction the
    knockout reproduces.

    Genes whose knockout makes the whole model infeasible are excluded by
    default. They are essential genes, so they register as losing every
    metabolite and would otherwise top any query containing a decrease,
    regardless of the patient.
    """
    import pandas as pd

    sigs = load_signatures(sig_file)
    diseases = load_disease_list(data_dir)

    by_gene: dict[str, list] = {}
    for entry in diseases:
        by_gene.setdefault(entry.gene_id, []).append(entry)

    wanted = parse_directions(biomarker_str)
    if not wanted:
        raise ValueError(
            f"No biomarker with a recognised direction in {biomarker_str!r}. "
            'Expected "met[bc],incr;met[bc],decr".'
        )

    col_of = {m: i for i, m in enumerate(sigs.bc_met_ids)}
    cols, dirs, unknown, skipped = [], [], [], []
    for met_id, direction in wanted.items():
        if met_id not in col_of:
            unknown.append(met_id)
            continue
        col = col_of[met_id]
        if sigs.wt_bc_flux[col] < min_wt_production and direction != 1:
            # Not produced in the wild type, so it cannot decrease further.
            skipped.append(met_id)
            continue
        cols.append(col)
        dirs.append(direction)

    if unknown:
        print(f"  warning: not blood metabolites in this model: {unknown}")
    if skipped:
        print(f"  warning: not produced in the wild type, decrease ignored: {skipped}")
    if not cols:
        raise ValueError("No queried biomarker is usable against this model.")

    sub = sigs.signatures[:, np.array(cols)].toarray()
    hits = (sub == np.array(dirs, dtype=np.int8)[None, :]).sum(axis=1)
    scores = hits / len(cols)

    rows = []
    for g, gene_id in enumerate(sigs.gene_ids):
        if exclude_infeasible and sigs.infeasible[g]:
            continue
        if scores[g] == 0:
            continue
        for entry in by_gene.get(gene_id, []):
            rows.append({
                "Disease": entry.name,
                "Gene": entry.gene_symbol,
                "DiseaseGene": gene_id,
                "PatientLabel": patient_label,
                "MatchScore": float(scores[g]),
                "MatchCount": int(hits[g]),
                "TotalBiomarkers": len(cols),
                "Essential": bool(sigs.infeasible[g]),
            })

    result = pd.DataFrame(rows)
    if not result.empty:
        result = result.sort_values(
            ["MatchScore", "MatchCount", "Gene"], ascending=[False, False, True]
        ).reset_index(drop=True)
    return result


def search_metabolites(
    keyword: str,
    sig_file: Path = DEFAULT_SIGNATURE_FILE,
    name_cache: Path = DEFAULT_NAME_CACHE,
) -> list[tuple[str, str]]:
    """
    Find blood metabolites whose identifier or common name contains ``keyword``.

    Common-name search needs the optional BiGG name cache; without it only
    identifiers are matched.
    """
    sigs = load_signatures(sig_file)
    names: dict[str, str] = {}
    if Path(name_cache).exists():
        with open(name_cache) as fh:
            names = {k: (v.get("name") or "") for k, v in json.load(fh).items()}

    kw = keyword.lower()
    hits = [
        (met_id, names.get(met_id.replace("[bc]", ""), ""))
        for met_id in sigs.bc_met_ids
        if kw in met_id.lower()
        or kw in names.get(met_id.replace("[bc]", ""), "").lower()
    ]
    return sorted(hits)
