"""Geometry test: zero-count hardware builds without raising (T030).

Covers spec 010 FR-016 + spec.allium zero-count fallbacks.
"""

from __future__ import annotations

import pytest

from storebro import (
    BowPulpitParameters,
    CleatParameters,
    DeckHardwareParameters,
    LifelineParameters,
    build_deck,
    build_hull,
)


@pytest.mark.requires_freecad
def test_zero_cleats_lifelines_stanchions_build_without_error(
    freecad_doc: object,
) -> None:
    hull = build_hull(document=freecad_doc)
    hw = DeckHardwareParameters(
        cleats=CleatParameters(count_per_station=0, station_count=0),
        lifelines=LifelineParameters(line_count=0),
        bow_pulpit=BowPulpitParameters(stanchion_count=0),
    )
    deck = build_deck(hull, parameters_hardware=hw)
    assert deck.cleats.count == 0
    assert deck.lifelines.line_count == 0
    # Empty compounds still exist; the rest of the deck is intact.
    assert deck.cleats.body is not None
    assert deck.lifelines.body is not None
    assert deck.rubrail.body.Shape.Volume > 0.0


@pytest.mark.requires_freecad
def test_zero_count_compounds_are_empty(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    hw = DeckHardwareParameters(
        cleats=CleatParameters(count_per_station=0, station_count=0),
        lifelines=LifelineParameters(line_count=0),
    )
    deck = build_deck(hull, parameters_hardware=hw)
    assert deck.cleats.body.Shape.Volume == 0.0
    assert deck.lifelines.body.Shape.Volume == 0.0
