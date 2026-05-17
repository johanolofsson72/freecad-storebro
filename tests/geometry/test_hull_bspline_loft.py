"""Geometry test: hull AdditiveLoft produces a valid solid.

Spec 007: the smooth B-spline loft (Ruled=False) target is deferred to v1.1+
(requires matching vertex topology between stem-rectangle and non-stem
profiles — a compound-curved-section refactor that exceeds PATCH scope).
The current loft auto-falls-back to Ruled=True (piecewise linear) which
produces a valid closed hull solid. This test only asserts validity, not
the smoothness mode.
"""

from __future__ import annotations

from typing import Any

import pytest

from storebro import build_hull

pytestmark = pytest.mark.requires_freecad


def test_hull_loft_produces_positive_volume(freecad_doc: Any) -> None:
    """The loft (Ruled=False or fallback Ruled=True) must produce a valid solid."""
    hull = build_hull(document=freecad_doc)
    loft = next(
        obj for obj in hull.body.Group if obj.TypeId == "PartDesign::AdditiveLoft"
    )
    assert loft.Shape is not None
    assert loft.Shape.Volume > 0.0
    assert loft.Shape.isClosed()
