"""Geometry test: zero-count furniture builds the rest (T021).

Covers spec 012 FR-010.
"""

from __future__ import annotations

import pytest

from storebro import (
    BerthParameters,
    FurnitureParameters,
    GalleyParameters,
    build_deck,
    build_hull,
    build_interior,
)


@pytest.mark.requires_freecad
def test_zero_cushions_and_disabled_cutouts(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    fp = FurnitureParameters(
        berth=BerthParameters(cushion_count=0),
        galley=GalleyParameters(cutouts_enabled=False),
    )
    interior = build_interior(hull, deck, layout="Alternativ1", parameters_furniture=fp)
    cabin = next(c for c in interior.compartments if c.spec.compartment_type == "forward_cabin")
    labels = [b.Label for b in cabin.furniture]
    assert any("Berth" in label for label in labels)
    assert not any("Cushion" in label for label in labels)
