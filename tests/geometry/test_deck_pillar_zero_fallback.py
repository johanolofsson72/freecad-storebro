"""Spec 008 — zero-pillar fallback path (clarification 4 in spec.md).

When ``PillarParameters.count_per_side == 0``, no pillar bodies are
constructed and the hardtop seats on the cabin trunk roof. Verified by
building with a zero-pillar parameter set and asserting:
- zero pillar bodies exist in the document
- the `Deck_HardtopPillars` legacy compound exists but has an empty shape
- the hardtop body still has positive volume (no construction failure)
"""

from __future__ import annotations

import pytest

from storebro import build_deck, build_hull
from storebro.deck import (
    DeckSuperstructureParameters,
    PillarParameters,
)


@pytest.mark.requires_freecad
def test_zero_pillars_builds_without_pillar_bodies(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    sp = DeckSuperstructureParameters(
        pillars=PillarParameters(count_per_side=0),
    )
    deck = build_deck(hull, parameters_superstructure=sp)
    pillar_bodies = [
        obj
        for obj in deck.document.Objects
        if obj.Label.startswith("Deck_Pillar_")
    ]
    assert pillar_bodies == [], (
        f"zero-pillar fallback: expected no pillar bodies, got {len(pillar_bodies)}"
    )


@pytest.mark.requires_freecad
def test_zero_pillars_hardtop_still_constructs(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    sp = DeckSuperstructureParameters(
        pillars=PillarParameters(count_per_side=0),
    )
    deck = build_deck(hull, parameters_superstructure=sp)
    assert deck.hardtop.body.Shape.Volume > 0, (
        "zero-pillar fallback: hardtop must still construct with positive volume"
    )
    assert deck.hardtop.body.TypeId == "PartDesign::Body"


@pytest.mark.requires_freecad
def test_zero_pillars_compound_wrapper_present_but_empty(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    sp = DeckSuperstructureParameters(
        pillars=PillarParameters(count_per_side=0),
    )
    deck = build_deck(hull, parameters_superstructure=sp)
    # The Deck_HardtopPillars legacy compound still exists for back-compat,
    # but its underlying shape has zero solids.
    pillars_wrapper = deck.hardtop_pillars.body
    assert pillars_wrapper is not None
    assert pillars_wrapper.Shape.Solids == [], (
        "zero-pillar fallback: legacy compound wrapper must have empty Solids"
    )
