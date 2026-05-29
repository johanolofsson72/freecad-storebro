"""Geometry test: cleats seated on the deck top + counts (T025).

Covers spec 010 FR-004, FR-009 + spec.allium CleatsSeatedOnDeck /
CleatTotalMatchesParameters.
"""

from __future__ import annotations

import pytest

from storebro import CleatParameters, DeckHardwareParameters, build_deck, build_hull
from storebro.deck import _resolve_deck_top_z_at

SEATING_TOL_MM = 1.0


@pytest.mark.requires_freecad
def test_default_cleat_count_is_four(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    assert deck.cleats.count == 4  # 1/side x 2 stations x 2 sides


@pytest.mark.requires_freecad
def test_each_cleat_seated_on_deck_top(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    cleat_bodies = [obj for obj in deck.document.Objects if obj.Label.startswith("Deck_Cleat_")]
    assert cleat_bodies, "FR-009: at least one cleat on default parameters"
    for cleat in cleat_bodies:
        bb = cleat.Shape.BoundBox
        x_center = (bb.XMin + bb.XMax) / 2.0
        deck_z = _resolve_deck_top_z_at(deck.deck_plate, x_center)
        assert bb.ZMin >= deck_z - SEATING_TOL_MM, (
            f"{cleat.Label} ZMin={bb.ZMin:.2f} below deck top {deck_z:.2f}"
        )


@pytest.mark.requires_freecad
def test_custom_cleat_count(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    hw = DeckHardwareParameters(cleats=CleatParameters(count_per_station=1, station_count=3))
    deck = build_deck(hull, parameters_hardware=hw)
    assert deck.cleats.count == 6  # 1 x 3 x 2
