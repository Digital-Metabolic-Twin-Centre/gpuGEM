"""Shared helpers for the manuscript figure scripts.

Every figure in the paper and its supplement is replotted here from the
benchmark results committed under ``benchmarks/results/``.  None of these
scripts solves anything: no GPU, no CUDA toolkit and no commercial solver
licence is needed to regenerate the figures.

Model labelling is deliberately centralised.  The six personalised
microbiome models are numbered PMM1-PMM6 in ascending size order, and the
sample-ID to label mapping lives in ``data/pmm_model_mapping.csv``.  Figure
scripts must take labels from :func:`labels_for` rather than hard-coding
them, so that a renumbering cannot leave a figure out of step with the text.
"""
from pathlib import Path
import argparse
import json

import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
RESULTS = REPO / "benchmarks" / "results"
DATA = HERE / "data"

#: Display names for the four public reference models.
DISPLAY = {
    "e_coli_core": "E. coli core",
    "iML1515": "iML1515",
    "Harvey": "Harvey",
    "Harvetta": "Harvetta",
}


def benchmark():
    """Ten-model headline benchmark, ordered by ascending model size.

    Source: ``benchmarks/results/benchmark.csv`` (benchmarks/run_benchmark.py).
    """
    d = pd.read_csv(RESULTS / "benchmark.csv")
    return d.sort_values("n_cols").reset_index(drop=True)


def highs_baseline():
    """HiGHS CPU baseline, indexed by model.

    Source: ``benchmarks/results/highs_baseline/highs_baseline.json``
    (benchmarks/run_highs_baseline.py).  The committed run uses HiGHS's
    default method selection, which resolves to dual simplex on every model.
    """
    rec = json.loads((RESULTS / "highs_baseline" / "highs_baseline.json").read_text())
    return pd.DataFrame(rec["results"]).set_index("model")


def highs_ipm():
    """HiGHS interior-point times used by Figure 1a/b, indexed by model.

    These runs are NOT reproducible from anything committed under
    ``benchmarks/results/``: only the method-comparison subset for the four
    public models is committed, in
    ``benchmarks/results/highs_baseline/highs_method_blocks.csv``.  The
    values here were carried over from the figure that appears in the
    manuscript.  To regenerate them from scratch:

        python benchmarks/run_highs_baseline.py --repo . \\
            --models Harvey Harvetta S84 S85 S23 S15 S9 S83 \\
            --method ipm --out highs_ipm.json

    ``ipm_usable`` is False where HiGHS returned a non-optimal status; those
    models are drawn as open markers in panel (a) and omitted from panel (b).
    """
    return pd.read_csv(DATA / "highs_ipm_fig1.csv").set_index("model")


def pmm_labels():
    """sample_id -> paper label (PMM1-PMM6), validated for ordering."""
    m = pd.read_csv(DATA / "pmm_model_mapping.csv")
    expected = ["PMM%d" % i for i in range(1, 7)]
    assert list(m.sort_values("variables").paper_label) == expected, (
        "PMM labels in data/pmm_model_mapping.csv are not in ascending size order"
    )
    return dict(zip(m.sample_id.astype(str), m.paper_label))


def labels_for(models):
    """Axis labels for a sequence of model identifiers."""
    pmm = pmm_labels()
    return [pmm.get(str(m), DISPLAY.get(str(m), str(m))) for m in models]


def italic_ecoli(labels):
    """Render the E. coli core tick label in italics, over two lines."""
    return [r"$\it{E.\ coli}$" + "\ncore" if s == "E. coli core" else s for s in labels]


def tint(color, f):
    """Blend ``color`` toward white by fraction 1-f.  EPS has no alpha channel."""
    import matplotlib as mpl

    r, g, b = mpl.colors.to_rgb(color)
    return (1 - f + f * r, 1 - f + f * g, 1 - f + f * b)


def outdir_arg(description):
    """Standard --outdir command line for every figure script."""
    ap = argparse.ArgumentParser(description=description)
    ap.add_argument("--outdir", default=str(HERE / "output"),
                    help="directory for the generated figure files")
    return ap.parse_args()


def save(fig, stem, outdir, dpi=350, tight=False):
    """Write PNG, PDF and EPS.  The manuscript embeds the PDF.

    ``tight`` trims the page to the drawn extent (``bbox_inches="tight"``).
    Scripts whose figure size was taken from the published page must leave it
    off, or the page is trimmed a second time.
    """
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    bbox = {"bbox_inches": "tight"} if tight else {}
    written = []
    for ext, kw in ((".png", {"dpi": dpi}), (".pdf", {}), (".eps", {})):
        p = out / (stem + ext)
        fig.savefig(p, **kw, **bbox)
        written.append(p)
    print("wrote " + ", ".join(str(p) for p in written))
    return written


#: Okabe-Ito palette: distinguishable under deuteranopia and protanopia.
C_GPU = "#0072B2"      # gpuGEM (focal series)
C_SIMPLEX = "#D55E00"  # HiGHS dual simplex
C_IPM = "#E69F00"      # HiGHS interior point
C_GUROBI = "#666666"   # Gurobi barrier
C_NOTOL = "#CC79A7"    # gpuGEM with the residual tolerance disabled
