"""Geometry test: default furniture fits every Alt3/4/5 compartment (T008).

Covers spec 013 FR-003, SC-001, SC-002 — a default build raises no
envelope-overflow error for any of the three new layouts.
"""

from __future__ import annotations

import pytest

from storebro import build_deck, build_hull, build_interior


@pytest.mark.requires_freecad
@pytest.mark.parametrize("layout", ["Alternativ3", "Alternativ4", "Alternativ5"])
def test_default_build_has_no_envelope_overflow(freecad_doc: object, layout: str) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    # Must not raise InteriorParameterError (envelope overflow) on defaults.
    interior = build_interior(hull, deck, layout=layout)
    assert all(c.is_furnished for c in interior.compartments)
    for c in interior.compartments:
        assert c.body.Shape.Volume > 0
