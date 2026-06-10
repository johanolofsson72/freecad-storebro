"""Geometry test: Alternativ5 integrated galley-in-salon (spec 025 US1, T009).

Covers FR-001, FR-008, SC-001. Spec 013's "Alt5 has no galley" is reversed:
the combined compartment is now `salon_galley` and carries a galley counter.
"""

from __future__ import annotations

import pytest

from storebro import build_deck, build_hull, build_interior


@pytest.mark.requires_freecad
def test_alt5_has_salon_galley_with_counter(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    interior = build_interior(hull, deck, layout="Alternativ5")
    types = {c.spec.compartment_type for c in interior.compartments}
    assert "salon_galley" in types
    assert {"forward_cabin", "head", "salon_galley"} == types
    assert all(c.is_furnished for c in interior.compartments)

    sg = next(c for c in interior.compartments if c.spec.compartment_type == "salon_galley")
    labels = [p.Label for p in sg.furniture]
    # Carries BOTH a galley counter AND salon furniture (settee/table).
    counter = [p for p in sg.furniture if "Counter" in p.Label or "Galley" in p.Label]
    salon = [p for p in sg.furniture if any(k in p.Label for k in ("Settee", "Table", "Salon"))]
    assert counter, f"no galley counter in {labels}"
    assert salon, f"no salon furniture in {labels}"
    # The galley counter is a single valid solid (the spec 012 manifold guard).
    for c in counter:
        s = c.Shape
        assert len(s.Solids) == 1 and s.isValid()
    # Every piece is valid + STL-exportable.
    for p in sg.furniture:
        assert p.Shape.isValid()


@pytest.mark.requires_freecad
def test_alt5_every_compartment_has_bulkhead(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    interior = build_interior(hull, deck, layout="Alternativ5")
    for c in interior.compartments:
        assert any("Bulkhead" in b.Label for b in c.furniture)
