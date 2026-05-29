"""Geometry test: Alt3/4/5 furniture reproducibility (T007).

Covers spec 013 SC-004.
"""

from __future__ import annotations

import FreeCAD  # type: ignore[import-not-found]
import pytest

from storebro import build_deck, build_hull, build_interior

RELATIVE_TOL = 1.0e-9


def _close(a: float, b: float) -> bool:
    if b == 0.0:
        return abs(a - b) <= RELATIVE_TOL
    return abs(a - b) / abs(b) <= RELATIVE_TOL


@pytest.mark.parametrize("layout", ["Alternativ3", "Alternativ4", "Alternativ5"])
def test_furniture_volumes_stable(layout: str) -> None:
    doc1 = FreeCAD.newDocument("Alt345Det1")
    doc2 = FreeCAD.newDocument("Alt345Det2")
    try:
        h1 = build_hull(document=doc1)
        i1 = build_interior(h1, build_deck(h1), layout=layout)
        h2 = build_hull(document=doc2)
        i2 = build_interior(h2, build_deck(h2), layout=layout)
        for c1, c2 in zip(i1.compartments, i2.compartments, strict=True):
            assert _close(c1.body.Shape.Volume, c2.body.Shape.Volume)
    finally:
        FreeCAD.closeDocument(doc1.Name)
        FreeCAD.closeDocument(doc2.Name)
