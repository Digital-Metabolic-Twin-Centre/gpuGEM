"""
Parsing of patient biomarker strings into model modifications.

A biomarker string is a semicolon-separated list of ``metabolite,direction``
tokens, for example::

    "C02470[bc],incr;kynate[bc],incr"
    "phe_L[bc],increased;tyr_L[bc],decreased"

Two metabolite compartments are handled, and they are handled differently:

``[bc]`` (blood compartment)
    A demand reaction ``DM_<met>`` is added, draining one unit of the
    metabolite. Its bounds and objective coefficient encode the measured
    direction: an elevated biomarker is rewarded for carrying positive flux,
    a depleted one is rewarded for carrying negative flux.

``[u]``
    No new column. The existing exchange reaction ``EX_<met>`` has its
    objective coefficient and upper bound modified in place.

The LP then maximises the sum of these coefficients, so its optimum is the
flux distribution that best explains the observed biomarker pattern.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

#: Accepted spellings of each direction.
DIRECTION_ALIASES: dict[str, str] = {
    "incr": "incr", "increased": "incr", "increase": "incr", "up": "incr",
    "decr": "decr", "decreased": "decr", "decrease": "decr", "down": "decr",
}

#: (lower bound, upper bound, objective coefficient) for a [bc] demand column.
DIRECTION_BOUNDS: dict[str, tuple[float, float, float]] = {
    "incr": (0.0, 100.0, 1.0),
    "decr": (-1.0, 0.0, -1.0),
}

#: Objective coefficient and upper bound applied to an [u] exchange reaction.
EXCHANGE_OBJ = 1.0
EXCHANGE_UB = 100.0


@dataclass(frozen=True)
class DemandSpec:
    """A [bc] biomarker resolved against the model."""

    met_index: int    # row of S for this metabolite
    met_id: str
    direction: str    # 'incr' or 'decr'
    lb: float
    ub: float
    obj: float


@dataclass(frozen=True)
class ExchangeSpec:
    """An [u] biomarker resolved to an existing exchange reaction."""

    rxn_index: int
    rxn_id: str
    met_id: str
    direction: str


def _split_tokens(biomarker_str: str) -> list[tuple[str, str]]:
    out = []
    for token in biomarker_str.split(";"):
        token = token.strip()
        if not token:
            continue
        parts = [p.strip() for p in token.split(",")]
        out.append((parts[0], parts[1].lower() if len(parts) > 1 else ""))
    return out


def parse_biomarkers(
    biomarker_str: str, mets: np.ndarray, rxns: np.ndarray
) -> tuple[list[DemandSpec], list[ExchangeSpec], list[str]]:
    """
    Resolve a biomarker string against a model.

    Returns ``(demand_specs, exchange_specs, warnings)``. Tokens naming an
    unknown metabolite or an unrecognised direction are skipped and reported in
    ``warnings`` rather than raising, matching the behaviour of the original
    implementation.
    """
    met_index = {m: i for i, m in enumerate(mets)}
    rxn_index = {r: i for i, r in enumerate(rxns)}

    demands: list[DemandSpec] = []
    exchanges: list[ExchangeSpec] = []
    warnings: list[str] = []

    for met_id, direction_raw in _split_tokens(biomarker_str):
        direction = DIRECTION_ALIASES.get(direction_raw)
        if direction is None:
            warnings.append(
                f"unknown direction {direction_raw!r} for {met_id}; token skipped"
            )
            continue

        if "[bc]" in met_id:
            if met_id not in met_index:
                warnings.append(f"metabolite {met_id!r} not in model; token skipped")
                continue
            lb, ub, obj = DIRECTION_BOUNDS[direction]
            demands.append(
                DemandSpec(met_index[met_id], met_id, direction, lb, ub, obj)
            )

        elif "[u]" in met_id:
            ex_id = f"EX_{met_id}"
            if ex_id not in rxn_index:
                warnings.append(f"exchange {ex_id!r} not in model; token skipped")
                continue
            exchanges.append(
                ExchangeSpec(rxn_index[ex_id], ex_id, met_id, direction)
            )

        else:
            warnings.append(
                f"metabolite {met_id!r} has no [bc] or [u] compartment tag; token skipped"
            )

    if not demands and not exchanges:
        raise ValueError(
            f"No usable biomarker in {biomarker_str!r}. "
            + ("Reasons: " + "; ".join(warnings) if warnings else "")
        )

    return demands, exchanges, warnings
