"""Geometry test: hardware reproducibility (T028).

Covers spec 010 FR-014, SC-004 + spec.allium DeterministicShapeDigest.
Two back-to-back builds on freshly-built hulls produce hardware bodies with
identical volumes.
"""

from __future__ import annotations

import FreeCAD  # type: ignore[import-not-found]

from storebro import build_deck, build_hull

RELATIVE_TOL = 1.0e-9


def _close(a: float, b: float) -> bool:
    if b == 0.0:
        return abs(a - b) <= RELATIVE_TOL
    return abs(a - b) / abs(b) <= RELATIVE_TOL


def test_two_decks_have_identical_hardware_volumes() -> None:
    doc1 = FreeCAD.newDocument("HwDet1")
    doc2 = FreeCAD.newDocument("HwDet2")
    try:
        d1 = build_deck(build_hull(document=doc1))
        d2 = build_deck(build_hull(document=doc2))
        for name in ("rubrail", "bow_pulpit", "anchor_locker", "cleats", "lifelines"):
            v1 = getattr(d1, name).body.Shape.Volume
            v2 = getattr(d2, name).body.Shape.Volume
            assert _close(v1, v2), f"{name}: hardware volume drift {v1} vs {v2}"
    finally:
        FreeCAD.closeDocument(doc1.Name)
        FreeCAD.closeDocument(doc2.Name)


def test_hardware_counts_are_stable() -> None:
    doc1 = FreeCAD.newDocument("HwCnt1")
    doc2 = FreeCAD.newDocument("HwCnt2")
    try:
        d1 = build_deck(build_hull(document=doc1))
        d2 = build_deck(build_hull(document=doc2))
        assert d1.cleats.count == d2.cleats.count
        assert d1.lifelines.line_count == d2.lifelines.line_count
    finally:
        FreeCAD.closeDocument(doc1.Name)
        FreeCAD.closeDocument(doc2.Name)
