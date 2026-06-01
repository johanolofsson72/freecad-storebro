"""Geometry test: propulsion reproducibility (T033).

Covers spec 014 FR-012, SC-005 + spec.allium DeterministicShapeDigest.
Two independent builds produce component bodies with identical volumes.
"""

from __future__ import annotations

import contextlib

import FreeCAD  # type: ignore[import-not-found]

from storebro import build_deck, build_hull, build_propulsion

RELATIVE_TOL = 1.0e-9
_GROUPS = ("engine_beds", "engines", "shafts", "propellers", "rudders")


def _close(a: float, b: float) -> bool:
    if b == 0.0:
        return abs(a - b) <= RELATIVE_TOL
    return abs(a - b) / abs(b) <= RELATIVE_TOL


def test_two_builds_identical_component_volumes() -> None:
    doc1 = FreeCAD.newDocument("PropDet1")
    doc2 = FreeCAD.newDocument("PropDet2")
    try:
        h1 = build_hull(document=doc1)
        h2 = build_hull(document=doc2)
        a = build_propulsion(h1, build_deck(h1))
        b = build_propulsion(h2, build_deck(h2))
        for group in _GROUPS:
            va = sorted(w.body.Shape.Volume for w in getattr(a, group))
            vb = sorted(w.body.Shape.Volume for w in getattr(b, group))
            assert len(va) == len(vb)
            for x, y in zip(va, vb, strict=True):
                assert _close(x, y), f"{group}: volume drift {x} vs {y}"
    finally:
        for doc in (doc1, doc2):
            with contextlib.suppress(Exception):
                FreeCAD.closeDocument(doc.Name)
