"""
Causal-gene prioritisation from patient biomarkers on the Harvey whole-body
metabolic model.

This is the application reported in the gpuGEM manuscript. It ranks inherited
metabolic disease genes by how far a patient's biomarker pattern suppresses the
flux each gene controls, using gpuGEM to solve the genome-scale LP on the GPU.

Quick start::

    from cugem_app import run_query

    result = run_query("C02470[bc],incr;kynate[bc],incr", backend="gpugem")
    print(result.summary())
    print(result.ranking.head(10))

Or from the command line::

    python application/src/run_candidate_genes.py \\
        "C02470[bc],incr;kynate[bc],incr" --backend gpugem

See ``application/README.md`` for the data, the solver requirements and the
published reference results.
"""

from cugem_app.data import (
    DEFAULT_DATA_DIR,
    DiseaseEntry,
    PrecomputedData,
    WBModel,
    load_disease_list,
    load_model,
    load_precomputed,
    setup_wildtype_objective,
)
from cugem_app.biomarkers import DemandSpec, ExchangeSpec, parse_biomarkers
from cugem_app.pipeline import QueryResult, run_query
from cugem_app.scoring import score_genes

__version__ = "0.1.0"
__all__ = [
    "DEFAULT_DATA_DIR",
    "DemandSpec",
    "DiseaseEntry",
    "ExchangeSpec",
    "PrecomputedData",
    "QueryResult",
    "WBModel",
    "load_disease_list",
    "load_model",
    "load_precomputed",
    "parse_biomarkers",
    "run_query",
    "score_genes",
    "setup_wildtype_objective",
]
