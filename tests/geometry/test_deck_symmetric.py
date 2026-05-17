"""Geometry test: all six sub-Bodies symmetric about centerline (T032).

Covers FR-009.
"""

from __future__ import annotations

from storebro import build_deck, build_hull


def test_each_sub_body_symmetric(freecad_doc: object) -> None:
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
        wrapper = getattr(deck, name)
        bb = wrapper.body.Shape.BoundBox
        midpoint_y = (bb.YMin + bb.YMax) / 2.0
        # Allow 1 mm tolerance (FreeCAD reports mm).
        assert abs(midpoint_y) < 1.0, (
            f"FR-009 violation: {name} not symmetric about centerline "
            f"(YMin={bb.YMin}, YMax={bb.YMax})"
        )
