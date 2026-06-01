"""Geometry test: twin trains mirror about the centreline (T028, US2).

Covers spec 014 FR-006, SC-002 + spec.allium TwinTrainsSymmetric.
"""

from __future__ import annotations

from storebro import build_deck, build_hull, build_propulsion


def test_twin_engines_mirrored_about_y(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    prop = build_propulsion(hull, deck)

    port = [e for e in prop.engines if e.is_port]
    starboard = [e for e in prop.engines if not e.is_port]
    assert len(port) == len(starboard) == 1

    py = port[0].body.Shape.BoundBox.Center.y
    sy = starboard[0].body.Shape.BoundBox.Center.y
    assert py > 0 and sy < 0
    assert abs(py + sy) < 1.0  # equal magnitude, opposite sign


def test_twin_shafts_and_props_mirrored(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    prop = build_propulsion(hull, deck)
    offset = prop.parameters.engine_offset_y_mm
    for group in (prop.shafts, prop.propellers):
        ys = sorted(b.body.Shape.BoundBox.Center.y for b in group)
        assert len(ys) == 2
        # Trains are translated to ±offset about the centreline: one each side,
        # spread = 2*offset (blade geometry is identical, not handed, so the
        # absolute centres carry a common offset that cancels in the spread).
        assert ys[0] < 0 < ys[1]
        assert abs((ys[1] - ys[0]) - 2.0 * offset) < 1.0
