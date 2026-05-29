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


def test_default_build_deck_returns_all_hardware(freecad_doc: object) -> None:
    """Spec 010 FR-011/SC-001: hardware is built by default."""
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)

    assert deck.rubrail is not None
    assert deck.bow_pulpit is not None
    assert deck.lifelines is not None
    assert deck.anchor_locker is not None
    assert deck.cleats is not None
    assert deck.parameters_hardware is not None
    # Default cleat layout = 4 (1 per side x 2 stations x 2 sides).
    assert deck.cleats.count == 4
    # Default = 1 line per side = 2 lifeline bodies (port + starboard).
    assert deck.lifelines.line_count == 2


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


def test_default_hardware_bodies_have_positive_volume(freecad_doc: object) -> None:
    """Spec 010: every default hardware body encloses volume."""
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    for wrapper_name in ("rubrail", "bow_pulpit", "anchor_locker", "cleats", "lifelines"):
        shape = getattr(deck, wrapper_name).body.Shape
        assert shape.Volume > 0, f"{wrapper_name} has zero volume"
