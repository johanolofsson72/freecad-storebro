"""Geometry test: coloring never mutates geometry (spec 015 T013, FR-011).

Captures Volume / BoundBox / Solids count / validity before and after applying
render attributes and asserts they are unchanged (contract invariant 5).
"""

from __future__ import annotations

from typing import Any

from storebro import apply_render_attributes, build_deck, build_hull, build_propulsion


def _snapshot(body: Any) -> tuple[float, int, bool, tuple[float, ...]]:
    shape = body.Shape
    bb = shape.BoundBox
    return (
        round(shape.Volume, 6),
        len(shape.Solids),
        shape.isValid(),
        (
            round(bb.XMin, 6),
            round(bb.YMin, 6),
            round(bb.ZMin, 6),
            round(bb.XMax, 6),
            round(bb.YMax, 6),
            round(bb.ZMax, 6),
        ),
    )


def test_apply_does_not_change_geometry(freecad_doc: Any) -> None:
    # Build everything WITHOUT colors first, snapshot, then color in place.
    hull = build_hull(document=freecad_doc, apply_render_attributes=False)
    deck = build_deck(hull, apply_render_attributes=False)
    prop = build_propulsion(hull, deck, apply_render_attributes=False)

    bodies = [
        hull.body,
        deck.deck_plate.body,
        deck.cabin_trunk.body,
        deck.rubrail.body,
        *(e.body for e in prop.engines),
        *(p.body for p in prop.propellers),
        *(r.body for r in prop.rudders),
    ]
    before = {b.Label: _snapshot(b) for b in bodies}

    applied = apply_render_attributes(bodies, enabled=True)
    assert applied == len(bodies)

    for body in bodies:
        assert _snapshot(body) == before[body.Label], body.Label
