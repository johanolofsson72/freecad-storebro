"""Geometry test: build_deck default call (T024).

Covers FR-001, FR-016, SC-002 (45-s budget).
"""

from __future__ import annotations

from storebro import build_deck, build_hull


def test_default_build_deck_returns_six_subbodies(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)

    assert deck.deck_plate is not None
    assert deck.cabin_trunk is not None
    assert deck.windshield is not None
    assert deck.hardtop is not None
    assert deck.hardtop_pillars is not None
    assert deck.railings is not None


def test_default_build_deck_uses_hull_document(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    assert deck.document is hull.document


def test_default_build_deck_within_budget(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    assert 0.0 < deck.build_duration_seconds < 45.0  # SC-002


def test_default_build_deck_bodies_have_positive_volume(
    freecad_doc: object,
) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    for wrapper_name in ("deck_plate", "cabin_trunk", "windshield", "hardtop"):
        body = getattr(deck, wrapper_name).body
        shape = body.Shape
        assert shape.Volume > 0, f"{wrapper_name} has zero volume"
