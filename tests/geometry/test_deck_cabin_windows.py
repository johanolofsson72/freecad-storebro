"""Geometry test: cabin-trunk side windows (T013).

Covers spec 011 FR-002, FR-007, FR-008 + spec.allium
CabinTrunkManifoldAfterGlazing / CabinWindowsSymmetricPortStarboard.
"""

from __future__ import annotations

import pytest

from storebro import (
    CabinWindowParameters,
    DeckGlazingParameters,
    build_deck,
    build_hull,
)
from storebro.deck import DeckParameterError


@pytest.mark.requires_freecad
def test_default_deck_cuts_window_band_per_side(freecad_doc: object) -> None:
    deck = build_deck(build_hull(document=freecad_doc))
    assert deck.cabin_windows.count == 4  # spec 033 orientation fix: 2 per side x 2 sides
    assert len(deck.cabin_trunk.body.Shape.Solids) == 1, "FR-008: trunk single solid"


@pytest.mark.requires_freecad
def test_windows_symmetric_and_partdesign(freecad_doc: object) -> None:
    deck = build_deck(build_hull(document=freecad_doc))
    port = [o for o in deck.document.Objects if o.Label.startswith("CabinWindowPocketPort")]
    star = [o for o in deck.document.Objects if o.Label.startswith("CabinWindowPocketStarboard")]
    assert len(port) == len(star) == 2  # spec 033 orientation fix: 2 windows per side
    assert all(o.TypeId == "PartDesign::Pocket" for o in port + star)


@pytest.mark.requires_freecad
def test_zero_windows_leaves_trunk_uncut(freecad_doc: object) -> None:
    dg = DeckGlazingParameters(cabin_windows=CabinWindowParameters(count_per_side=0))
    deck = build_deck(build_hull(document=freecad_doc), parameters_glazing=dg)
    assert deck.cabin_windows.count == 0
    assert len(deck.cabin_trunk.body.Shape.Solids) == 1


@pytest.mark.requires_freecad
def test_window_recess_deeper_than_wall_rejected(freecad_doc: object) -> None:
    dg = DeckGlazingParameters(cabin_windows=CabinWindowParameters(recess_depth=5000.0))
    with pytest.raises(DeckParameterError) as exc:
        build_deck(build_hull(document=freecad_doc), parameters_glazing=dg)
    assert exc.value.parameter_name == "cabin_window_recess_depth<>wall"
