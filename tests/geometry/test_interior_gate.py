"""Geometry test: Alt3-5 remain boxy (gate) (T018).

Covers spec 012 FR-011, SC-006 + spec.allium FurnishedImpliesAlt1Alt2.
"""

from __future__ import annotations

import pytest

from storebro import build_deck, build_hull, build_interior


@pytest.mark.requires_freecad
@pytest.mark.parametrize("layout", ["Alternativ3", "Alternativ4", "Alternativ5"])
def test_non_alt12_layouts_stay_boxy(freecad_doc: object, layout: str) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    interior = build_interior(hull, deck, layout=layout)
    assert all(not c.is_furnished for c in interior.compartments)
    for c in interior.compartments:
        assert c.furniture == ()
