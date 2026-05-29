"""Geometry test: default build_deck includes all five hardware classes (T027).

Covers spec 010 FR-001, FR-010, FR-011, SC-001.
"""

from __future__ import annotations

import pytest

from storebro import build_deck, build_hull

HARDWARE_LABEL_PREFIXES = (
    "Deck_Rubrail",
    "Deck_BowPulpit",
    "Deck_Lifelines",
    "Deck_AnchorLocker",
    "Deck_Cleats",
)


@pytest.mark.requires_freecad
def test_default_call_adds_all_hardware_bodies(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    labels = [obj.Label for obj in deck.document.Objects]
    for prefix in HARDWARE_LABEL_PREFIXES:
        assert any(label.startswith(prefix) for label in labels), (
            f"FR-001/SC-001: no document object with prefix {prefix!r}; got {labels}"
        )


@pytest.mark.requires_freecad
def test_default_call_no_regression_in_superstructure(freecad_doc: object) -> None:
    """Adding hardware must not drop any superstructure body."""
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    for name in (
        "deck_plate",
        "cabin_trunk",
        "windshield",
        "hardtop",
        "hardtop_pillars",
        "railings",
    ):
        assert getattr(deck, name).body.Shape is not None


@pytest.mark.requires_freecad
def test_default_call_within_time_budget(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    assert 0.0 < deck.build_duration_seconds < 60.0
