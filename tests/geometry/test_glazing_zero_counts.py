"""Geometry test: zero-count / disabled glazing builds the un-cut solid (T020).

Covers spec 011 FR-011 + spec.allium zero-count fallbacks.
"""

from __future__ import annotations

import pytest

from storebro import (
    CabinWindowParameters,
    DeckGlazingParameters,
    HullGlazingParameters,
    PortholeParameters,
    WindshieldGlazingParameters,
    build_deck,
    build_hull,
)


@pytest.mark.requires_freecad
def test_zero_portholes_no_error(freecad_doc: object) -> None:
    hg = HullGlazingParameters(portholes=PortholeParameters(count_per_side=0))
    hull = build_hull(document=freecad_doc, parameters_glazing=hg)
    assert hull.portholes.count == 0
    assert len(hull.body.Shape.Solids) == 1


@pytest.mark.requires_freecad
def test_zero_windows_and_disabled_windshield_no_error(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    dg = DeckGlazingParameters(
        cabin_windows=CabinWindowParameters(count_per_side=0),
        windshield=WindshieldGlazingParameters(enabled=False),
    )
    deck = build_deck(hull, parameters_glazing=dg)
    assert deck.cabin_windows.count == 0
    assert deck.windshield.glass_pane is None
    assert len(deck.cabin_trunk.body.Shape.Solids) == 1
    assert deck.windshield.body.Shape.Volume > 0.0  # solid slab fallback
