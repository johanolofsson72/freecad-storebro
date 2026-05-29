"""Geometry test: glazing reproducibility (T018).

Covers spec 011 FR-013, SC-005 + spec.allium DeterministicShapeDigest.
"""

from __future__ import annotations

import FreeCAD  # type: ignore[import-not-found]

from storebro import build_deck, build_hull

RELATIVE_TOL = 1.0e-9


def _close(a: float, b: float) -> bool:
    if b == 0.0:
        return abs(a - b) <= RELATIVE_TOL
    return abs(a - b) / abs(b) <= RELATIVE_TOL


def test_two_glazed_hulls_have_identical_volume() -> None:
    doc1 = FreeCAD.newDocument("GlzDet1")
    doc2 = FreeCAD.newDocument("GlzDet2")
    try:
        h1 = build_hull(document=doc1)
        h2 = build_hull(document=doc2)
        assert _close(h1.body.Shape.Volume, h2.body.Shape.Volume)
        d1 = build_deck(h1)
        d2 = build_deck(h2)
        assert _close(d1.cabin_trunk.body.Shape.Volume, d2.cabin_trunk.body.Shape.Volume)
        assert _close(
            d1.windshield.glass_pane.body.Shape.Volume,
            d2.windshield.glass_pane.body.Shape.Volume,
        )
    finally:
        FreeCAD.closeDocument(doc1.Name)
        FreeCAD.closeDocument(doc2.Name)


def test_porthole_and_window_counts_stable() -> None:
    doc1 = FreeCAD.newDocument("GlzCnt1")
    doc2 = FreeCAD.newDocument("GlzCnt2")
    try:
        d1 = build_deck(build_hull(document=doc1))
        d2 = build_deck(build_hull(document=doc2))
        assert d1.hull.portholes.count == d2.hull.portholes.count
        assert d1.cabin_windows.count == d2.cabin_windows.count
    finally:
        FreeCAD.closeDocument(doc1.Name)
        FreeCAD.closeDocument(doc2.Name)
