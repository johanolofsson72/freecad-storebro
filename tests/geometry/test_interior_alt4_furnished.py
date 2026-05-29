"""Geometry test: Alternativ4 furnished, smaller galley (T004).

Covers spec 013 FR-001, FR-004, SC-001, SC-003.
"""

from __future__ import annotations

import pytest

from storebro import build_deck, build_hull, build_interior


@pytest.mark.requires_freecad
def test_alt4_all_compartments_furnished(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    interior = build_interior(hull, deck, layout="Alternativ4")
    assert len(interior.compartments) == 4
    assert all(c.is_furnished for c in interior.compartments)


@pytest.mark.requires_freecad
def test_alt4_small_galley_counter_fits_and_manifold(freecad_doc: object) -> None:
    # Alt4 galley is 0.9 x 1.6 m — the smallest galley; the counter + recesses
    # must still fit and stay a single solid.
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    interior = build_interior(hull, deck, layout="Alternativ4")
    galley = next(c for c in interior.compartments if c.spec.compartment_type == "galley")
    counter = galley.furniture[0]
    assert len(counter.Shape.Solids) == 1
    assert counter.Shape.Volume > 0
