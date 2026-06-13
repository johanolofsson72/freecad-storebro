"""Geometry test: default build produces glazing (T017).

Covers spec 011 FR-009, FR-015, SC-001, SC-002.
"""

from __future__ import annotations

import pytest

from storebro import build_deck, build_hull


@pytest.mark.requires_freecad
def test_default_hull_and_deck_have_glazing(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    assert hull.portholes.count == 6
    assert deck.cabin_windows.count == 4  # spec 033 orientation fix: 2-window band per side
    assert deck.windshield.glass_pane is not None
    assert hull.parameters_glazing is not None
    assert deck.parameters_glazing is not None


@pytest.mark.requires_freecad
def test_glazing_objects_present_in_document(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    labels = [o.Label for o in deck.document.Objects]
    assert any(label.startswith("PortholePocket") for label in labels)
    assert any(label.startswith("CabinWindowPocket") for label in labels)
    assert any(label.startswith("Deck_WindshieldGlass") for label in labels)
