"""Geometry test: canonical layouts unchanged by spec 025 (T017).

Covers FR-011, SC-005. Alternativ1-4 + DS keep their pre-025 structure (no new
types, every compartment on the centreline) and build deterministically; only
Alternativ5 changed (it gained its galley).
"""

from __future__ import annotations

import contextlib

import FreeCAD  # type: ignore[import-not-found]
import pytest

from storebro import build_deck, build_hull, build_interior

_CANONICAL = ("Alternativ1", "Alternativ2", "Alternativ3", "Alternativ4", "DsSaloon")
_NEW_TYPES = {"aft_cabin", "dinette", "engine_room", "wet_locker", "salon_galley"}


@pytest.mark.requires_freecad
@pytest.mark.parametrize("layout", _CANONICAL)
def test_canonical_layout_unchanged_structure(layout: str, freecad_doc: object) -> None:
    variant = "ds" if layout == "DsSaloon" else "standard"
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull, superstructure_variant=variant)
    interior = build_interior(hull, deck, layout=layout, superstructure_variant=variant)
    # Canonical layouts (except Alt5) use no new types and stay on the centreline.
    for c in interior.compartments:
        assert c.spec.compartment_type not in _NEW_TYPES
        assert c.spec.position.y == 0.0


@pytest.mark.requires_freecad
@pytest.mark.parametrize("layout", _CANONICAL)
def test_canonical_layout_deterministic(layout: str) -> None:
    variant = "ds" if layout == "DsSaloon" else "standard"
    doc1 = FreeCAD.newDocument("CanA")
    doc2 = FreeCAD.newDocument("CanB")
    try:
        h1 = build_hull(document=doc1)
        h2 = build_hull(document=doc2)
        a = build_interior(h1, build_deck(h1, superstructure_variant=variant),
                           layout=layout, superstructure_variant=variant)
        b = build_interior(h2, build_deck(h2, superstructure_variant=variant),
                           layout=layout, superstructure_variant=variant)
        va = sorted(c.body.Shape.Volume for c in a.compartments)
        vb = sorted(c.body.Shape.Volume for c in b.compartments)
        assert va == vb, f"{layout}: volume drift {va} vs {vb}"
    finally:
        for doc in (doc1, doc2):
            with contextlib.suppress(Exception):
                FreeCAD.closeDocument(doc.Name)
