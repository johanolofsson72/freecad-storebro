"""Geometry test: Alternativ2 furnished by the same builders (T016).

Covers spec 012 SC-006 (Alt2 == Alt1 detail level).
"""

from __future__ import annotations

import pytest

from storebro import build_deck, build_hull, build_interior


@pytest.mark.requires_freecad
def test_alt2_all_compartments_furnished(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    interior = build_interior(hull, deck, layout="Alternativ2")
    assert all(c.is_furnished for c in interior.compartments)
    types = {c.spec.compartment_type for c in interior.compartments}
    assert {"forward_cabin", "galley", "head", "salon"} <= types
    for c in interior.compartments:
        assert len(c.furniture) >= 2  # at least one piece + a bulkhead
