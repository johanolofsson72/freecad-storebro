"""Geometry test: spec 016 variant field population + standard back-compat (FR-002, FR-007, FR-008).

Requires FreeCAD. Asserts the standard variant is unchanged (six bodies, four
open-flybridge slots populated, deckhouse None) and the DS variant inverts the
population while sharing the deck plate + railings + all five hardware items,
and never mutates the hull (FR-018).
"""

from __future__ import annotations

from storebro import build_deck, build_hull


def test_standard_variant_population(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)  # default == standard
    assert deck.superstructure_variant == "standard"
    assert deck.deckhouse is None
    assert deck.cabin_trunk is not None
    assert deck.windshield is not None
    assert deck.hardtop is not None
    assert deck.hardtop_pillars is not None
    assert deck.cabin_windows is not None
    # Shared items present.
    assert deck.railings is not None
    for hw in (deck.rubrail, deck.bow_pulpit, deck.lifelines, deck.anchor_locker, deck.cleats):
        assert hw is not None


def test_ds_variant_population(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull, superstructure_variant="ds")
    assert deck.superstructure_variant == "ds"
    assert deck.deckhouse is not None
    # Open-flybridge bodies absent.
    assert deck.cabin_trunk is None
    assert deck.windshield is None
    assert deck.hardtop is None
    assert deck.hardtop_pillars is None
    assert deck.cabin_windows is None
    # Shared items still present in both variants (FR-007).
    assert deck.railings is not None
    for hw in (deck.rubrail, deck.bow_pulpit, deck.lifelines, deck.anchor_locker, deck.cleats):
        assert hw is not None


def test_ds_variant_does_not_mutate_hull(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    volume_before = hull.body.Shape.Volume
    build_deck(hull, superstructure_variant="ds")
    volume_after = hull.body.Shape.Volume
    # FR-018: the hull solid is shared read-only, never booleaned.
    assert abs(volume_after - volume_before) <= max(1.0, volume_before * 1e-9)
