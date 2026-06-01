"""Geometry test: shaft is down-and-aft with exit below the waterline (T021, US1).

Covers spec 014 FR-004, FR-007, SC-003 + spec.allium DownAndAft / ExitBelowWaterline.
"""

from __future__ import annotations

from storebro import build_deck, build_hull, build_propulsion


def test_shaft_down_and_aft(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    prop = build_propulsion(hull, deck)
    for shaft in prop.shafts:
        assert shaft.forward_z_mm > shaft.aft_z_mm, "shaft must descend going aft"


def test_shaft_exit_below_waterline(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    prop = build_propulsion(hull, deck)
    for shaft in prop.shafts:
        assert shaft.exit_z_mm <= 0.0


def test_shaft_has_stern_tube_boss(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    prop = build_propulsion(hull, deck)
    for shaft in prop.shafts:
        assert shaft.has_stern_tube_boss is True
