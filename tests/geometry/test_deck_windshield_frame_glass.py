"""Geometry test: windshield frame + glass rework (T016).

Covers spec 011 FR-003, FR-011 + spec.allium WindshieldFrame /
WindshieldGlassPane.
"""

from __future__ import annotations

import pytest

from storebro import (
    DeckGlazingParameters,
    WindshieldGlazingParameters,
    build_deck,
    build_hull,
)
from storebro.deck import DeckParameterError


@pytest.mark.requires_freecad
def test_default_windshield_has_frame_and_glass(freecad_doc: object) -> None:
    deck = build_deck(build_hull(document=freecad_doc))
    assert deck.windshield.glass_pane is not None
    assert deck.windshield.glass_pane.body.Shape.Volume > 0.0
    # The frame body has the opening pocketed → still a single valid solid.
    assert len(deck.windshield.body.Shape.Solids) == 1
    assert deck.windshield.body.Shape.isValid()


@pytest.mark.requires_freecad
def test_frame_has_opening_vs_solid_slab(freecad_doc: object) -> None:
    """The framed windshield encloses less volume than the solid-slab fallback."""
    framed = build_deck(build_hull(document=freecad_doc))
    solid = build_deck(
        build_hull(),
        parameters_glazing=DeckGlazingParameters(
            windshield=WindshieldGlazingParameters(enabled=False)
        ),
    )
    assert framed.windshield.body.Shape.Volume < solid.windshield.body.Shape.Volume
    assert solid.windshield.glass_pane is None


@pytest.mark.requires_freecad
def test_glass_pane_is_distinct_partdesign_body(freecad_doc: object) -> None:
    deck = build_deck(build_hull(document=freecad_doc))
    pane = deck.windshield.glass_pane
    assert pane is not None
    assert pane.body.TypeId == "PartDesign::Body"
    assert pane.body is not deck.windshield.body


@pytest.mark.requires_freecad
def test_oversized_frame_border_rejected(freecad_doc: object) -> None:
    dg = DeckGlazingParameters(windshield=WindshieldGlazingParameters(frame_border=5000.0))
    with pytest.raises(DeckParameterError) as exc:
        build_deck(build_hull(document=freecad_doc), parameters_glazing=dg)
    assert exc.value.parameter_name == "windshield_frame_border<>opening"
