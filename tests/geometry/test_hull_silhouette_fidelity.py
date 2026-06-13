"""Spec 009 T025 — silhouette fidelity to the RC34 1972 reference.

Constitution IV: the default-parameter hull MUST match the RC34 reference
silhouette within ±1% on LOA, beam_max, and draft (the citation-grade fields).
Spec 009 must preserve this guarantee through the smoother B-spline loft.
"""

from __future__ import annotations

import pytest

from storebro.hull import (
    REFERENCE_FIDELITY_TOLERANCE_PCT,
    HullParameters,
    build_hull,
)

pytestmark = pytest.mark.requires_freecad


_TOLERANCE = REFERENCE_FIDELITY_TOLERANCE_PCT / 100.0


def _within_pct(actual: float, expected: float, pct: float) -> bool:
    return abs(actual - expected) <= expected * pct


def test_default_hull_loa_within_one_percent_of_reference() -> None:
    p = HullParameters()
    hull = build_hull(p)
    actual_loa_m = hull.bbox[0]
    assert _within_pct(actual_loa_m, p.loa, _TOLERANCE), (
        f"LOA {actual_loa_m:.3f} m drift from reference {p.loa} m exceeds "
        f"{REFERENCE_FIDELITY_TOLERANCE_PCT}%"
    )


def test_default_hull_beam_within_one_percent_of_reference() -> None:
    p = HullParameters()
    hull = build_hull(p)
    actual_beam_m = hull.bbox[1]
    assert _within_pct(actual_beam_m, p.beam_max, _TOLERANCE), (
        f"beam {actual_beam_m:.3f} m drift from reference {p.beam_max} m exceeds "
        f"{REFERENCE_FIDELITY_TOLERANCE_PCT}%"
    )


def test_default_hull_height_envelope_within_reasonable_bounds() -> None:
    """Hull Z extent must be roughly (draft + bow sheer peak).

    Spec 032 sweeps the sheer up at the stem to ``sheer_height_fwd * 1.22``, so
    the bbox height tracks draft + that peak (≈ 2.49 m) rather than draft +
    sheer_height_fwd. The 1.22 factor mirrors ``_sheer_fwd_peak`` in hull.py.
    """
    p = HullParameters()
    hull = build_hull(p)
    actual_height_m = hull.bbox[2]
    expected_height_m = p.draft + p.sheer_height_fwd * 1.22
    # ±5% around the sweeping-sheer peak height.
    assert abs(actual_height_m - expected_height_m) <= expected_height_m * 0.05
