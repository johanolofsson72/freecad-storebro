"""Geometry test: head fittings + bulkheads (T015).

Covers spec 012 FR-001 (head toilet/sink, bulkheads).
"""

from __future__ import annotations

import pytest

from storebro import build_deck, build_hull, build_interior


@pytest.mark.requires_freecad
def test_head_has_toilet_and_sink(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    interior = build_interior(hull, deck, layout="Alternativ1")
    head = next(c for c in interior.compartments if c.spec.compartment_type == "head")
    labels = [b.Label for b in head.furniture]
    assert any("Toilet" in label for label in labels)
    assert any("Sink" in label for label in labels)


@pytest.mark.requires_freecad
def test_every_compartment_has_a_bulkhead(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    interior = build_interior(hull, deck, layout="Alternativ1")
    for c in interior.compartments:
        labels = [b.Label for b in c.furniture]
        assert any("Bulkhead" in label for label in labels), f"{c.spec.name} has no bulkhead"
