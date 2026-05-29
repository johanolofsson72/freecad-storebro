"""Geometry test: hardware port/starboard symmetry (T014).

Covers spec 010 SC-002 + spec.allium SymmetricRubrails / SymmetricCleats.
"""

from __future__ import annotations

import pytest

from storebro import build_deck, build_hull

SYMMETRY_TOL_MM = 1.0


@pytest.mark.requires_freecad
def test_rubrail_symmetric_about_centerline(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    bb = deck.rubrail.body.Shape.BoundBox
    assert abs(bb.YMax - (-bb.YMin)) <= SYMMETRY_TOL_MM, (
        f"rubrail not symmetric: YMax={bb.YMax}, YMin={bb.YMin}"
    )


@pytest.mark.requires_freecad
def test_cleats_symmetric_port_starboard(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    labels = [obj.Label for obj in deck.document.Objects]
    port = [label for label in labels if label.startswith("Deck_Cleat_Port")]
    starboard = [label for label in labels if label.startswith("Deck_Cleat_Starboard")]
    assert len(port) == len(starboard)
    assert len(port) > 0


@pytest.mark.requires_freecad
def test_bow_pulpit_symmetric_about_centerline(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    bb = deck.bow_pulpit.body.Shape.BoundBox
    assert abs(bb.YMax - (-bb.YMin)) <= 5.0, (
        f"bow pulpit not symmetric: YMax={bb.YMax}, YMin={bb.YMin}"
    )
