"""Geometry test: default Alt1 build furnishes all compartments (T017).

Covers spec 012 SC-001, FR-008.
"""

from __future__ import annotations

import pytest

from storebro import build_deck, build_hull, build_interior


@pytest.mark.requires_freecad
def test_default_alt1_furnishes_all_four(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    interior = build_interior(hull, deck, layout="Alternativ1")
    assert len(interior.compartments) == 4
    assert all(c.is_furnished for c in interior.compartments)
    for c in interior.compartments:
        assert c.body.Shape.Volume > 0
