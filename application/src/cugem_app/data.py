"""
Loading of the Harvey whole-body model and its precomputed companions.

Translated from the COBRA Toolbox implementation of the candidate-gene
prioritisation workflow. The MATLAB files this module reads are documented in
``application/data/PROVENANCE.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import scipy.io
import scipy.sparse as sp

#: Default location of the Harvey model data shipped with the repository.
DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data"

#: Reaction-name keyword identifying the whole-body objective reaction.
WHOLE_BODY_KEYWORD = "Whole"

#: Flux magnitudes at or below this are treated as zero, matching the MATLAB original.
FLUX_TOL = 1e-5


@dataclass
class WBModel:
    """Whole-body metabolic model fields needed to state the LP."""

    S: sp.csc_matrix      # stoichiometric matrix            (m x n)
    C: sp.csc_matrix      # coupling constraint matrix       (k x n)
    b: np.ndarray         # RHS of S v = b                   (m,)
    d: np.ndarray         # RHS of C v {<=,>=,=} d           (k,)
    lb: np.ndarray        # reaction lower bounds            (n,)
    ub: np.ndarray        # reaction upper bounds            (n,)
    c: np.ndarray         # objective coefficients           (n,)
    csense: np.ndarray    # 'E'/'L'/'G' per stoichiometric row
    dsense: np.ndarray    # 'E'/'L'/'G' per coupling row
    rxns: np.ndarray      # reaction identifiers             (n,)
    mets: np.ndarray      # metabolite identifiers           (m,)
    genes: np.ndarray     # gene identifiers
    grRules: np.ndarray   # gene-protein-reaction rules      (n,)
    osenseStr: str        # 'min' or 'max'

    @property
    def n_rxns(self) -> int:
        return len(self.rxns)

    @property
    def n_mets(self) -> int:
        return len(self.mets)


@dataclass
class PrecomputedData:
    """Matrices precomputed once so that each query does not recompute them."""

    fbaWT_v: np.ndarray                # wild-type flux vector              (n,)
    rxnGenMatrix: sp.csc_matrix        # causal reaction-to-gene mapping    (n x g)
    rxnGenGenes: np.ndarray            # gene identifiers for the columns   (g,)
    rxnGenRxns: np.ndarray             # reaction identifiers for the rows  (n,)
    rxnGenMatrixNonCausal: Optional[sp.csc_matrix] = None


@dataclass(frozen=True)
class DiseaseEntry:
    """One row of the inherited-metabolic-disease list."""

    name: str
    gene_id: str
    abbr: str
    gene_symbol: str


def _load_mat(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(
            f"Model data file not found: {path}\n"
            f"Expected it under {DEFAULT_DATA_DIR}. See application/data/PROVENANCE.md."
        )
    return scipy.io.loadmat(str(path), struct_as_record=False, squeeze_me=True)


def _to_str_array(x) -> np.ndarray:
    """
    Turn a MATLAB cell-of-strings into a numpy array of Python strings.

    The dtype is deliberately ``object`` rather than ``str``. Numpy's fixed
    width string dtype pads every element to the longest one, and the longest
    ``grRules`` entry in the Harvey model is over 56,000 characters: a fixed
    width array of 81,094 reactions would demand 16.9 GiB. Object dtype stores
    one pointer per entry and supports the elementwise ``==`` this module and
    its callers rely on.
    """
    arr = np.asarray(x, dtype=object)
    return np.array([str(v) for v in arr.flat], dtype=object).reshape(arr.shape)


def load_model(data_dir: Path = DEFAULT_DATA_DIR) -> WBModel:
    """Load ``Harvey_1_03c_reduced.mat`` into a :class:`WBModel`."""
    raw = _load_mat(Path(data_dir) / "Harvey_1_03c_reduced.mat")
    m = raw["modelReduced"]

    return WBModel(
        S=sp.csc_matrix(m.S),
        C=sp.csc_matrix(m.C),
        b=np.asarray(m.b, dtype=float).ravel(),
        d=np.asarray(m.d, dtype=float).ravel(),
        lb=np.asarray(m.lb, dtype=float).ravel(),
        ub=np.asarray(m.ub, dtype=float).ravel(),
        c=np.asarray(m.c, dtype=float).ravel(),
        csense=_to_str_array(m.csense).ravel(),
        dsense=_to_str_array(m.dsense).ravel(),
        rxns=_to_str_array(m.rxns).ravel(),
        mets=_to_str_array(m.mets).ravel(),
        genes=_to_str_array(m.genes).ravel(),
        grRules=_to_str_array(m.grRules).ravel(),
        osenseStr=str(m.osenseStr).strip(),
    )


def load_precomputed(
    data_dir: Path = DEFAULT_DATA_DIR, wt_method: str = "QP"
) -> PrecomputedData:
    """
    Load the precomputed wild-type flux vector and the reaction-gene matrices.

    ``wt_method`` selects which precomputed wild-type file to read. 'QP' is the
    one used in the manuscript: the minimum-norm solution is unique, whereas an
    LP vertex is not reproducible across solvers on this degenerate model.
    """
    wt_raw = _load_mat(Path(data_dir) / f"fbaWT_{wt_method}_gurobi_Harvey_1_03c.mat")
    fbaWT_v = np.asarray(wt_raw["fbaWT"].v, dtype=float).ravel()
    fbaWT_v[np.abs(fbaWT_v) <= 1e-6] = 0.0

    rxn_raw = _load_mat(Path(data_dir) / "rxnGenMatrixCausalMatrix.mat")
    nc_raw = _load_mat(Path(data_dir) / "rxnGenMatrixNonCausalMatrix.mat")

    return PrecomputedData(
        fbaWT_v=fbaWT_v,
        rxnGenMatrix=sp.csc_matrix(rxn_raw["rxnGenMatrixCausal"]),
        rxnGenGenes=_to_str_array(rxn_raw["rxnGenMatrixGenes"]).ravel(),
        rxnGenRxns=_to_str_array(rxn_raw["rxnGenMatrixRxns"]).ravel(),
        rxnGenMatrixNonCausal=sp.csc_matrix(nc_raw["rxnGenMatrixNonCausal"]),
    )


def load_disease_list(data_dir: Path = DEFAULT_DATA_DIR) -> list[DiseaseEntry]:
    """
    Parse ``diseaseListFile.m`` into :class:`DiseaseEntry` records.

    The file holds a MATLAB cell array of four single-quoted fields per row:
    disease name, gene identifier, abbreviation, gene symbol.
    """
    import re

    m_file = Path(data_dir)
    if m_file.is_dir():
        m_file = m_file / "diseaseListFile.m"
    if not m_file.exists():
        raise FileNotFoundError(f"Disease list not found: {m_file}")

    text = m_file.read_text(encoding="utf-8")
    match = re.search(r"disease\s*=\s*\{(.*?)\};", text, re.DOTALL)
    if not match:
        raise ValueError(f"Could not find the 'disease' cell array in {m_file}")

    row_re = re.compile(r"'([^']*)'\s+'([^']*)'\s+'([^']*)'\s+'([^']*)'")
    return [
        DiseaseEntry(name=g[0], gene_id=g[1], abbr=g[2], gene_symbol=g[3])
        for g in row_re.findall(match.group(1))
    ]


def setup_wildtype_objective(wbm: WBModel) -> WBModel:
    """
    Apply the wild-type objective setup from the MATLAB original.

    Fixes the whole-body objective reaction at a flux of 1 and makes it the
    sole objective, maximised. Returns a copy; the input is left untouched.
    """
    import copy

    whole_mask = np.array([WHOLE_BODY_KEYWORD in r for r in wbm.rxns])
    if not whole_mask.any():
        raise ValueError(
            f"No reaction name contains '{WHOLE_BODY_KEYWORD}'; "
            "cannot identify the whole-body objective reaction."
        )

    out = copy.copy(wbm)
    out.osenseStr = "max"
    out.lb = wbm.lb.copy()
    out.ub = wbm.ub.copy()
    out.c = np.zeros(wbm.n_rxns, dtype=float)
    out.lb[whole_mask] = 1.0
    out.ub[whole_mask] = 1.0
    out.c[whole_mask] = 1.0
    return out


def whole_body_indices(wbm: WBModel) -> np.ndarray:
    """Indices of the whole-body objective reaction(s)."""
    return np.where(np.array([WHOLE_BODY_KEYWORD in r for r in wbm.rxns]))[0]
