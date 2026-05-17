"""Geometry test: structural determinism (T031).

Covers FR-005, SC-003. Two back-to-back build_deck calls on freshly-built
hulls produce sub-Bodies with identical volumes within tolerance.
"""

from __future__ import annotations

import FreeCAD  # type: ignore[import-not-found]

from storebro import build_deck, build_hull

RELATIVE_TOL = 1.0e-9


def _close(a: float, b: float) -> bool:
    if b == 0.0:
        return abs(a - b) <= RELATIVE_TOL
    return abs(a - b) / abs(b) <= RELATIVE_TOL


def test_two_decks_have_identical_subbody_volumes() -> None:
    doc1 = FreeCAD.newDocument("Det1")
    doc2 = FreeCAD.newDocument("Det2")
    try:
        h1 = build_hull(document=doc1)
        h2 = build_hull(document=doc2)
        d1 = build_deck(h1)
        d2 = build_deck(h2)

        for name in ("deck_plate", "cabin_trunk", "windshield", "hardtop"):
            v1 = getattr(d1, name).body.Shape.Volume
            v2 = getattr(d2, name).body.Shape.Volume
            assert _close(v1, v2), f"{name}: volume drift {v1} vs {v2}"
    finally:
        FreeCAD.closeDocument(doc1.Name)
        FreeCAD.closeDocument(doc2.Name)
