"""Geometry test: Alternativ5 furnished with no galley (T005).

Covers spec 013 FR-002, SC-002 + spec.allium GalleyFurnitureRequiresGalleyCompartment.
"""

from __future__ import annotations

import pytest

from storebro import build_deck, build_hull, build_interior


@pytest.mark.requires_freecad
def test_alt5_furnished_without_galley(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    interior = build_interior(hull, deck, layout="Alternativ5")
    types = {c.spec.compartment_type for c in interior.compartments}
    assert "galley" not in types  # Alt5 has no galley compartment
    assert {"forward_cabin", "head", "salon"} == types
    assert all(c.is_furnished for c in interior.compartments)
    # No galley furniture anywhere in the document.
    labels = [o.Label for o in interior.document.Objects]
    assert not any("GalleyCounter" in label for label in labels)


@pytest.mark.requires_freecad
def test_alt5_every_compartment_has_bulkhead(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    interior = build_interior(hull, deck, layout="Alternativ5")
    for c in interior.compartments:
        assert any("Bulkhead" in b.Label for b in c.furniture)
