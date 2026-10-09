"""
The candidate-gene pipeline, in one function, with a switchable LP backend.

Four stages:

1. Load the Harvey model, the precomputed wild-type flux and the disease list.
2. Impose the patient's biomarkers and solve the resulting LP. This is the
   expensive stage and the one the backend switch selects: ``'gpugem'`` runs it
   on the GPU, ``'gurobi'`` runs the published CPU baseline.
3. Re-solve as a minimum-norm QP pinned at the LP optimum. The LP optimal face
   of this model is highly degenerate, so without this step the reported fluxes
   depend on which vertex the solver happened to stop at and the ranking is not
   reproducible. This stage is Gurobi-only in both configurations.
4. Score and rank the candidate genes.

Only stage 2 differs between the two configurations, which is what makes their
rankings directly comparable.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional

import numpy as np
import pandas as pd

from cugem_app import biomarkers as bm
from cugem_app import data as dat
from cugem_app import scoring

Backend = Literal["gpugem", "gurobi"]

#: Slack subtracted from the LP optimum when pinning the QP's linear objective.
#: It must exceed the error in ``f*``, which depends on the solver that
#: produced it: Gurobi's simplex optimum is exact to its own tolerance, while
#: PDLP terminates at a first-order optimality tolerance.
LP_SLACK: dict[str, float] = {"gurobi": 1e-6, "gpugem": 1e-5}


@dataclass
class QueryResult:
    """Ranking plus the timings and solver diagnostics behind it."""

    ranking: pd.DataFrame
    backend: str
    objective: Optional[float]
    timings: dict[str, float] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    solver_info: dict = field(default_factory=dict)

    def summary(self) -> str:
        t = self.timings
        lines = [
            f"backend            {self.backend}",
            f"LP objective       {self.objective!r}",
            "",
            f"  load data        {t.get('load', float('nan')):7.2f}s",
            f"  build LP         {t.get('build', float('nan')):7.2f}s",
            f"  LP solve         {t.get('lp', float('nan')):7.2f}s",
            f"  QP solve         {t.get('qp', float('nan')):7.2f}s",
            f"  scoring          {t.get('scoring', float('nan')):7.2f}s",
            f"  total            {t.get('total', float('nan')):7.2f}s",
        ]
        if self.warnings:
            lines += ["", "warnings:"] + [f"  - {w}" for w in self.warnings]
        return "\n".join(lines)


def run_query(
    biomarker_str: str,
    *,
    backend: Backend = "gpugem",
    data_dir: Path = dat.DEFAULT_DATA_DIR,
    wt_method: str = "QP",
    label: str = "patient",
    verbose: bool = False,
) -> QueryResult:
    """
    Rank candidate disease genes for one patient's biomarker pattern.

    Parameters
    ----------
    biomarker_str:
        Semicolon-separated ``metabolite,direction`` tokens, for example
        ``"C02470[bc],incr;kynate[bc],incr"``. See :mod:`cugem_app.biomarkers`.
    backend:
        ``'gpugem'`` solves the LP on the GPU through ``gpugem.solve``;
        ``'gurobi'`` solves it with dual simplex on the CPU. The QP stage uses
        Gurobi either way.
    data_dir:
        Directory holding the Harvey ``.mat`` files. Defaults to the copy
        shipped in ``application/data``.
    wt_method:
        Which precomputed wild-type solution to compare against, ``'QP'`` or
        ``'LP'``. The manuscript uses ``'QP'``.
    """
    if backend not in ("gpugem", "gurobi"):
        raise ValueError(f"backend must be 'gpugem' or 'gurobi', got {backend!r}")

    from cugem_app import gurobi_backend as gb  # imported here so the error is late

    timings: dict[str, float] = {}
    t_start = time.perf_counter()

    # ── 1. Load ───────────────────────────────────────────────────────────────
    t0 = time.perf_counter()
    wbm_raw = dat.load_model(data_dir)
    precomp = dat.load_precomputed(data_dir, wt_method=wt_method)
    disease_list = dat.load_disease_list(data_dir)
    wbm = dat.setup_wildtype_objective(wbm_raw)
    whole_idx = dat.whole_body_indices(wbm)
    timings["load"] = time.perf_counter() - t0

    demands, exchanges, warns = bm.parse_biomarkers(biomarker_str, wbm.mets, wbm.rxns)
    for w in warns:
        print(f"  warning: {w}")

    # ── 2. Build the patient LP ───────────────────────────────────────────────
    # The Gurobi model is built in both configurations: the QP stage needs it.
    t0 = time.perf_counter()
    env = gb.make_env(output=verbose)
    try:
        base, _ = gb.build_base_model(wbm, env, print_level=1 if verbose else 0)
        grb = base.copy()
        grb.Params.OutputFlag = 1 if verbose else 0
        gb.apply_biomarkers(grb, wbm, demands, exchanges, whole_idx)
        timings["build"] = time.perf_counter() - t0

        # ── 3. LP ─────────────────────────────────────────────────────────────
        solver_info: dict = {}
        t0 = time.perf_counter()
        if backend == "gpugem":
            from cugem_app import gpugem_backend as gg

            res = gg.solve_lp(wbm, demands, exchanges)
            if res.objective is None:
                raise RuntimeError(f"gpuGEM LP did not solve: status={res.status}")
            f_star = float(res.objective)
            solver_info = {
                "status": res.status,
                "solver_wall_time_s": res.wall_time_s,
                "settings": res.solver_settings,
                "feasibility": res.feasibility,
            }
        else:
            status, f_star = gb.solve_lp(grb)
            if f_star is None:
                raise RuntimeError(f"Gurobi LP did not solve: status={status}")
            solver_info = {"status": status, "method": "dual simplex"}
        timings["lp"] = time.perf_counter() - t0

        # ── 4. Minimum-norm QP ────────────────────────────────────────────────
        t0 = time.perf_counter()
        qp_status, flux = gb.solve_minnorm_qp(
            grb, wbm, f_star, slack=LP_SLACK[backend]
        )
        if flux is None:
            raise RuntimeError(f"Minimum-norm QP did not solve: status={qp_status}")
        timings["qp"] = time.perf_counter() - t0
    finally:
        env.dispose()

    # ── 5. Score ──────────────────────────────────────────────────────────────
    t0 = time.perf_counter()
    ranking = scoring.score_genes(
        wbm, precomp, disease_list, flux,
        objective_value=f_star, patient_label=label,
    )
    timings["scoring"] = time.perf_counter() - t0
    timings["total"] = time.perf_counter() - t_start

    return QueryResult(
        ranking=ranking,
        backend=backend,
        objective=f_star,
        timings=timings,
        warnings=warns,
        solver_info=solver_info,
    )
