"""Geometry test: default deck dimensions match RC34 1972 reference (T027).

Covers SC-001 + FR-003. The three citation-grade fields are cabin_trunk_length,
hardtop_length, railing_height — each must match the REFERENCE constant within
±1%.
"""

from __future__ import annotations

from storebro import DeckParameters, build_deck, build_hull

REFERENCE = DeckParameters.REFERENCE_STOREBRO_DECK_RC34_1972


def test_default_cabin_trunk_length_within_one_percent(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    ref = REFERENCE["cabin_trunk_length"]
    measured = deck.cabin_trunk.length
    assert abs(measured - ref) <= ref * 0.01, (
        f"default cabin_trunk_length {measured} m drifted >1% from {ref} m"
    )


def test_default_hardtop_length_within_one_percent(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    ref = REFERENCE["hardtop_length"]
    measured = deck.hardtop.length
    assert abs(measured - ref) <= ref * 0.01


def test_default_railing_height_within_one_percent(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    ref = REFERENCE["railing_height"]
    measured = deck.railings.height
    assert abs(measured - ref) <= ref * 0.01
