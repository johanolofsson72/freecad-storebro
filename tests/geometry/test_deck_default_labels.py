"""Geometry test: deck sub-Body labels (T025).

Covers FR-017.
"""

from __future__ import annotations

from storebro import build_deck, build_hull

REQUIRED_LABELS = {
    "Deck_DeckPlate",
    "Deck_CabinTrunk",
    "Deck_Windshield",
    "Deck_Hardtop",
    "Deck_HardtopPillars",
    "Deck_Railings",
}

REQUIRED_HARDWARE_LABELS = {
    "Deck_Rubrail",
    "Deck_BowPulpit",
    "Deck_Lifelines",
    "Deck_AnchorLocker",
    "Deck_Cleats",
}


def test_default_labels(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)

    sub_labels = {
        deck.deck_plate.body.Label,
        deck.cabin_trunk.body.Label,
        deck.windshield.body.Label,
        deck.hardtop.body.Label,
        deck.hardtop_pillars.body.Label,
        deck.railings.body.Label,
    }
    # FreeCAD may auto-number on Label collisions; allow the first one's exact match,
    # but the prefix should always be Deck_<Element>.
    for required in REQUIRED_LABELS:
        assert any(label.startswith(required) for label in sub_labels), (
            f"missing or differently-labeled sub-Body: expected prefix {required!r}, "
            f"got {sub_labels}"
        )


def test_hardware_labels(freecad_doc: object) -> None:
    """Spec 010: the five hardware items carry Deck_<Item> labels."""
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    hw_labels = {
        deck.rubrail.body.Label,
        deck.bow_pulpit.body.Label,
        deck.lifelines.body.Label,
        deck.anchor_locker.body.Label,
        deck.cleats.body.Label,
    }
    for required in REQUIRED_HARDWARE_LABELS:
        assert any(label.startswith(required) for label in hw_labels), (
            f"missing or differently-labeled hardware body: expected prefix "
            f"{required!r}, got {hw_labels}"
        )


def test_second_build_deck_auto_numbers(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck1 = build_deck(hull)
    deck2 = build_deck(hull)
    assert deck1.deck_plate.body.Label != deck2.deck_plate.body.Label
