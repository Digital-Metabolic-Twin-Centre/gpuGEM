"""Tests for the violation-distribution figures' per-model color palette -- no GPU
required. The palette itself (CATEGORICAL_PALETTE) is a fixed, hand-validated constant
(see the module docstring comment in make_violation_distribution_figures.py for how it
was derived and checked against the dataviz skill's colorblind-safety validator); these
tests cover the *selection* logic (`_rank_colors`), not re-derive the color science.
"""
from __future__ import annotations

import pytest

from benchmarks.make_violation_distribution_figures import CATEGORICAL_PALETTE, _rank_colors


def test_rank_colors_returns_first_n_in_fixed_order():
    assert _rank_colors(3) == CATEGORICAL_PALETTE[:3]
    assert _rank_colors(len(CATEGORICAL_PALETTE)) == CATEGORICAL_PALETTE


def test_rank_colors_never_cycles_or_repeats():
    colors = _rank_colors(len(CATEGORICAL_PALETTE))
    assert len(set(colors)) == len(colors)


def test_rank_colors_raises_rather_than_silently_cycling_when_out_of_slots():
    with pytest.raises(ValueError):
        _rank_colors(len(CATEGORICAL_PALETTE) + 1)


def test_palette_entries_are_valid_hex_colors():
    for c in CATEGORICAL_PALETTE:
        assert c.startswith("#") and len(c) == 7
        int(c[1:], 16)  # raises ValueError if not valid hex
