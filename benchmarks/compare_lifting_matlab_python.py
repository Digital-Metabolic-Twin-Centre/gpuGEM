"""Compare the MATLAB-lifted model against gpuGEM's Python lifting, block by block.

Answers, with numbers rather than assertion, two questions that the existing
lifting validation (``run_model_lifting_validation.py``) does *not* answer:

1. Does ``gpugem.lifting`` (the ``reformulate.m`` port) produce the same
   reformulation that the MATLAB pipeline actually produced?  The MATLAB side
   is read from a ``*_lifted.mat`` file exported by that pipeline; the Python
   side is produced here by running ``lift_mass_balance``/``lift_coupling`` on
   the *unlifted* source model.
2. What ill-scaling is left behind *after* each lift -- measured over the
   WHOLE matrix, including the rows neither implementation touched and the
   auxiliary rows the lift itself created.  ``run_model_lifting_validation.py``'s
   ``scale_report`` measures only the rows it lifted, which cannot report a
   failure by construction.

Small coefficients are reported but never lifted by either side:
``reformulate.m`` states in its own header that it "assumes S and C do not
contain very small entries", and the Python port is faithful to that.  The
census here quantifies what that assumption costs on real whole-body models.

MATLAB layout note: the ``*_lifted.mat`` files keep auxiliary variables in the
COBRA ``evars`` blocks (``E`` for stoichiometric rows, ``D`` for coupling rows)
rather than appending columns to ``S``/``C``, so the comparable full matrices
are ``[S | E]`` and ``[C | D]``.  gpuGEM's port appends columns directly.

Usage::

    python benchmarks/compare_lifting_matlab_python.py --model S85 \
        --matlab-lifted /path/to/mWBM_S85_male_lifted.mat
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import scipy.io as sio
import scipy.sparse as sp

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from benchmarks import models as M  # noqa: E402

RESULTS = HERE / "results" / "lifting_matlab_python"
RESULTS.mkdir(parents=True, exist_ok=True)

SMALL = 1e-3  # "very small entry" threshold for the census (reformulate.m's
              # own documented blind spot -- see module docstring)


def _stats(mat, big, small=SMALL):
    """Coefficient census over every stored nonzero of `mat`."""
    d = np.abs(sp.coo_matrix(mat).data)
    d = d[d > 0]
    if d.size == 0:
        return {"shape": list(mat.shape), "nnz": 0}
    return {
        "shape": list(mat.shape),
        "nnz": int(d.size),
        "min_abs": float(d.min()),
        "max_abs": float(d.max()),
        "n_above_big": int((d > big).sum()),
        "n_below_small": int((d < small).sum()),
        "log10_span": float(np.log10(d.max() / d.min())),
    }


def _row_flags(C, d_lb, d_ub, big):
    """Vectorised reproduction of reformulate.m's `cuprow`/`badrow` selection
    (lines 145-158), so we can count what it selects without running the lift."""
    C = sp.csr_matrix(C)
    coo = C.tocoo()
    n = C.shape[0]
    maxabs = np.zeros(n)
    np.maximum.at(maxabs, coo.row, np.abs(coo.data))
    signsum = np.zeros(n)
    np.add.at(signsum, coo.row, np.sign(coo.data))
    nnz_row = np.diff(C.indptr)
    homogeneous = (np.asarray(d_lb) == 0) | (np.asarray(d_ub) == 0)
    return {
        "has_big_entry": maxabs > big,
        "two_nonzeros": nnz_row == 2,
        "opposite_sign": signsum == 0,
        "homogeneous": homogeneous,
        "max_abs": maxabs,
    }


def python_side(lp, big):
    """Run gpuGEM's own lifting and measure the result over the whole matrix."""
    from gpugem.lifting import lift_coupling, lift_mass_balance

    S = sp.csr_matrix(lp["S"])
    C = sp.csr_matrix(lp["C"]) if lp.get("C") is not None else None
    n_mets, n_crows = S.shape[0], (C.shape[0] if C is not None else 0)

    S_lift, _b, mapping = lift_mass_balance(S, np.asarray(lp["b"]), big=big)
    out = {
        "S_before": _stats(S, big),
        "S_after": _stats(S_lift, big),
        "n_mass_balance_rows_lifted": len(mapping.mass_balance_lifted_rows),
    }
    if C is None:
        out["n_aux_vars"] = mapping.n_aux_vars
        return out, mapping

    C_lift, _l, _u, mapping = lift_coupling(
        C, np.asarray(lp["d_lb"]), np.asarray(lp["d_ub"]), big, mapping
    )
    flags = _row_flags(C, lp["d_lb"], lp["d_ub"], big)
    selected = flags["two_nonzeros"] & flags["opposite_sign"] & flags["homogeneous"]
    left = flags["has_big_entry"] & ~selected

    coo = sp.coo_matrix(C_lift)
    over = np.abs(coo.data) > big
    out.update({
        "C_before": _stats(C, big),
        "C_after": _stats(C_lift, big),
        "n_coupling_rows_lifted": len(mapping.coupling_lifted_rows),
        "n_aux_vars": mapping.n_aux_vars,
        # the coverage gap: rows that ARE badly scaled but that reformulate.m's
        # cuprow pattern excludes, so no implementation faithful to it lifts them
        "coupling_rows_big_but_not_selected": int(left.sum()),
        "coupling_left_behind_max_abs": float(flags["max_abs"][left].max()) if left.any() else 0.0,
        "coupling_left_behind_same_sign_pair": int(
            (left & flags["two_nonzeros"] & ~flags["opposite_sign"]).sum()),
        "coupling_left_behind_not_two_nonzeros": int((left & ~flags["two_nonzeros"]).sum()),
        # where the surviving oversized entries live after the lift
        "C_after_over_big_in_original_rows": int((over & (coo.row < n_crows)).sum()),
        "C_after_over_big_in_aux_rows": int((over & (coo.row >= n_crows)).sum()),
    })
    coo_s = sp.coo_matrix(S_lift)
    over_s = np.abs(coo_s.data) > big
    out["S_after_over_big_in_original_rows"] = int((over_s & (coo_s.row < n_mets)).sum())
    out["S_after_over_big_in_aux_rows"] = int((over_s & (coo_s.row >= n_mets)).sum())
    return out, mapping


def matlab_side(path, big):
    """Read a MATLAB `*_lifted.mat` and measure the same quantities.

    Auxiliary variables live in the `E`/`D` evars blocks, so the comparable
    full matrices are [S | E] and [C | D].
    """
    raw = sio.loadmat(str(path), struct_as_record=False, squeeze_me=True)
    S = sp.csr_matrix(raw["S"])
    C = sp.csr_matrix(raw["C"])
    E = sp.csr_matrix(raw["E"]) if "E" in raw else None
    D = sp.csr_matrix(raw["D"]) if "D" in raw else None
    S_full = sp.hstack([S, E], format="csr") if E is not None else S
    C_full = sp.hstack([C, D], format="csr") if D is not None else C

    out = {
        "S_after": _stats(S_full, big),
        "C_after": _stats(C_full, big),
        "n_aux_vars": int(np.asarray(raw["evars"]).size) if "evars" in raw else 0,
        "E_nnz": int(E.nnz) if E is not None else None,
        "D_nnz": int(D.nnz) if D is not None else None,
    }
    # `*_old` fields, when present, are this pipeline's own pre-lift blocks --
    # the only trustworthy "before" for the MATLAB side, since the exported
    # file need not come from the same source revision as the local unlifted copy.
    if "C_old" in raw:
        C_old = sp.csr_matrix(raw["C_old"])
        d_old = np.asarray(raw["d_old"], dtype=float).ravel()
        out["C_before"] = _stats(C_old, big)
        flags = _row_flags(C_old, d_old, d_old, big)
        out["coupling_rows_with_big_entry"] = int(flags["has_big_entry"].sum())
        out["coupling_rows_matching_reformulate_cuprow"] = int(
            (flags["has_big_entry"] & flags["two_nonzeros"] & flags["opposite_sign"]).sum())
        if D is not None:
            touched = np.unique(sp.coo_matrix(D).row)
            orig_touched = touched[touched < C_old.shape[0]]
            out["n_coupling_rows_lifted"] = int(orig_touched.size)
            out["lifted_rows_that_are_same_sign_pairs"] = int(
                (flags["two_nonzeros"][orig_touched] & ~flags["opposite_sign"][orig_touched]).sum())
    return out


def compare(model, matlab_lifted, big):
    lp, prov = M.build_lp(model)
    py, _mapping = python_side(lp, big)
    ml = matlab_side(matlab_lifted, big)

    same_base = (
        "C_before" in ml
        and ml["C_before"]["shape"][0] == py["C_before"]["shape"][0]
    ) if "C_before" in py else None

    return {
        "model": model,
        "big": big,
        "small_threshold": SMALL,
        "unlifted_source": prov.get("source"),
        "matlab_lifted_source": str(matlab_lifted),
        "matlab_base_matches_local_unlifted": same_base,
        "python": py,
        "matlab": ml,
    }


def _fmt(v):
    if isinstance(v, float):
        return "%.4g" % v
    return str(v)


def report(cmp):
    py, ml = cmp["python"], cmp["matlab"]
    big = cmp["big"]
    print("=" * 74)
    print("%s   BIG=%g   small-entry threshold=%g" % (cmp["model"], big, cmp["small_threshold"]))
    print("=" * 74)
    if cmp["matlab_base_matches_local_unlifted"] is False:
        print("NOTE: the MATLAB file's own pre-lift C block has %s rows but the local\n"
              "      unlifted model has %s -- they are not the same source revision, so\n"
              "      row-by-row identity is not expected. Aggregate scale is comparable."
              % (ml["C_before"]["shape"][0], py["C_before"]["shape"][0]))
        print("-" * 74)
    for block in ("S", "C"):
        b, a = py.get(block + "_before"), py.get(block + "_after")
        if b is None:
            continue
        print("[%s block]" % block)
        print("  unlifted        : |coef| %.3e .. %.3e   %d entries > BIG   %d entries < %g"
              % (b["min_abs"], b["max_abs"], b["n_above_big"], b["n_below_small"], cmp["small_threshold"]))
        print("  python lifted   : |coef| %.3e .. %.3e   %d entries > BIG"
              % (a["min_abs"], a["max_abs"], a["n_above_big"]))
        m = ml.get(block + "_after")
        if m:
            print("  MATLAB lifted   : |coef| %.3e .. %.3e   %d entries > BIG"
                  % (m["min_abs"], m["max_abs"], m["n_above_big"]))
    print("-" * 74)
    print("rows lifted   python: mass-balance %s, coupling %s (aux vars %s)"
          % (py.get("n_mass_balance_rows_lifted"), py.get("n_coupling_rows_lifted"),
             py.get("n_aux_vars")))
    print("              MATLAB: mass-balance %s, coupling %s (aux vars %s)"
          % ("0 (E block empty)" if ml.get("E_nnz") == 0 else "see E block",
             ml.get("n_coupling_rows_lifted"), ml.get("n_aux_vars")))
    print("-" * 74)
    print("coverage gap (reformulate.m's cuprow pattern):")
    print("  coupling rows with a >BIG entry            : %s"
          % ml.get("coupling_rows_with_big_entry", py.get("C_before", {}).get("n_above_big")))
    print("  ...matching cuprow (2 nnz, opposite sign)  : %s"
          % ml.get("coupling_rows_matching_reformulate_cuprow"))
    print("  ...lifted by the MATLAB file               : %s" % ml.get("n_coupling_rows_lifted"))
    print("     of which same-sign pairs cuprow excludes: %s"
          % ml.get("lifted_rows_that_are_same_sign_pairs"))
    print("  ...lifted by the python port               : %s" % py.get("n_coupling_rows_lifted"))
    print("  LEFT BEHIND by the python port             : %s (max |coef| %s)"
          % (py.get("coupling_rows_big_but_not_selected"),
             _fmt(py.get("coupling_left_behind_max_abs"))))
    print("     same-sign pairs                         : %s"
          % py.get("coupling_left_behind_same_sign_pair"))
    print("     not exactly two nonzeros                : %s"
          % py.get("coupling_left_behind_not_two_nonzeros"))
    print("-" * 74)
    print("where oversized entries survive the python lift:")
    print("  S: %s in original rows, %s in NEW auxiliary rows"
          % (py.get("S_after_over_big_in_original_rows"), py.get("S_after_over_big_in_aux_rows")))
    print("  C: %s in original rows, %s in NEW auxiliary rows"
          % (py.get("C_after_over_big_in_original_rows"), py.get("C_after_over_big_in_aux_rows")))
    print("-" * 74)
    sb, sa = py.get("S_before"), py.get("S_after")
    print("small coefficients (never lifted by either implementation):")
    print("  S entries < %g : %d before, %d after -- min |coef| stays %.3e"
          % (cmp["small_threshold"], sb["n_below_small"], sa["n_below_small"], sa["min_abs"]))
    print("  S dynamic range: 10^%.1f before -> 10^%.1f after"
          % (sb["log10_span"], sa["log10_span"]))
    print("=" * 74)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=list(M.REGISTRY.keys()))
    ap.add_argument("--matlab-lifted", required=True, type=Path,
                    help="path to the MATLAB pipeline's *_lifted.mat export")
    ap.add_argument("--big", type=float, default=1000.0)
    args = ap.parse_args()

    if not args.matlab_lifted.exists():
        sys.exit("MATLAB lifted model not found: %s" % args.matlab_lifted)

    cmp = compare(args.model, args.matlab_lifted, args.big)
    report(cmp)
    out = RESULTS / (args.model + ".json")
    out.write_text(json.dumps(cmp, indent=2))
    print("wrote %s" % out)


if __name__ == "__main__":
    main()
