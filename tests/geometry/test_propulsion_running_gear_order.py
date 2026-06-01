"""Geometry test: prop aft of exit, rudder aft of prop, both below WL (T022, US1).

Covers spec 014 FR-004, SC-003 (aft = smaller X; bow = XMax).
"""

from __future__ import annotations

from storebro import build_deck, build_hull, build_propulsion


def test_propeller_aft_of_shaft_exit(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    prop = build_propulsion(hull, deck)
    for shaft, propeller in zip(prop.shafts, prop.propellers, strict=True):
        assert propeller.hub_x_mm < shaft.exit_x_mm, "propeller must sit aft of the shaft exit"


def test_rudder_aft_of_propeller(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    prop = build_propulsion(hull, deck)
    # Twin default: one rudder per propeller, matched by side.
    for propeller in prop.propellers:
        matching = [r for r in prop.rudders if r.is_port == propeller.is_port]
        assert matching
        for rudder in matching:
            assert rudder.x_mm < propeller.hub_x_mm, "rudder must sit aft of the propeller"


def test_running_gear_below_waterline(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    prop = build_propulsion(hull, deck)
    for propeller in prop.propellers:
        assert propeller.bbox_min_z_mm < 0.0
    for rudder in prop.rudders:
        assert rudder.bbox_min_z_mm < 0.0
