"""Geometry test: Alternativ3 furnished (T003).

Covers spec 013 FR-001, FR-004, SC-001, SC-003.
"""

from __future__ import annotations

import pytest

from storebro import build_deck, build_hull, build_interior


@pytest.mark.requires_freecad
def test_alt3_all_compartments_furnished(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    interior = build_interior(hull, deck, layout="Alternativ3")
    assert len(interior.compartments) == 4
    assert all(c.is_furnished for c in interior.compartments)
    types = {c.spec.compartment_type for c in interior.compartments}
    assert {"forward_cabin", "galley", "head", "salon"} == types


@pytest.mark.requires_freecad
def test_alt3_galley_counter_single_solid(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    interior = build_interior(hull, deck, layout="Alternativ3")
    galley = next(c for c in interior.compartments if c.spec.compartment_type == "galley")
    assert len(galley.furniture[0].Shape.Solids) == 1
    assert galley.furniture[0].Shape.isValid()
