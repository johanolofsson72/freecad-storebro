"""Geometry test: the hull solid is never booleaned (T025, US1).

Covers spec 014 FR-007, SC-004 + spec.allium HullSolidNeverBooleaned.
"""

from __future__ import annotations

from storebro import build_deck, build_hull, build_propulsion


def test_hull_solid_count_and_volume_unchanged(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    solids_before = len(hull.body.Shape.Solids)
    volume_before = hull.body.Shape.Volume

    prop = build_propulsion(hull, deck)

    assert prop.hull_modified is False
    assert len(hull.body.Shape.Solids) == solids_before
    assert abs(hull.body.Shape.Volume - volume_before) < 1.0e-6 * max(volume_before, 1.0)
