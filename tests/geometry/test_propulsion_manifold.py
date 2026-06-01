"""Geometry test: every produced body is a single closed manifold (T024, US1).

Covers spec 014 FR-008, FR-009, SC-004 + spec.allium ValidManifold.
"""

from __future__ import annotations

from storebro import build_deck, build_hull, build_propulsion


def _all_bodies(prop: object) -> list[object]:
    p = prop
    return [
        *[b.body for b in p.engine_beds],  # type: ignore[attr-defined]
        *[b.body for b in p.engines],  # type: ignore[attr-defined]
        *[b.body for b in p.shafts],  # type: ignore[attr-defined]
        *[b.body for b in p.propellers],  # type: ignore[attr-defined]
        *[b.body for b in p.rudders],  # type: ignore[attr-defined]
    ]


def test_every_body_single_valid_solid(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    prop = build_propulsion(hull, deck)
    for body in _all_bodies(prop):
        shape = body.Shape
        assert len(shape.Solids) == 1, f"{body.Label}: expected 1 solid, got {len(shape.Solids)}"
        assert shape.isValid(), f"{body.Label}: shape is not valid"
        assert shape.Volume > 0.0


def test_bodies_are_partdesign(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    prop = build_propulsion(hull, deck)
    for body in _all_bodies(prop):
        assert body.TypeId == "PartDesign::Body", f"{body.Label}: {body.TypeId}"
