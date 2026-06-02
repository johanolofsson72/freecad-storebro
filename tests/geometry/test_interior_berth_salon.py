"""Geometry test: furnished forward cabin + salon (T009).

Covers spec 012 FR-001, FR-004, SC-001 + spec.allium AllFurnitureWithinEnvelope.
"""

from __future__ import annotations

import pytest

from storebro import build_deck, build_hull, build_interior

_M_TO_MM = 1000.0


def _within(piece_bb: object, comp: object) -> bool:
    # spec 017: geometry is built at millimetre scale, so the spec-derived
    # (metre-space) envelope bounds are converted to mm for comparison.
    s = comp.spec
    x0, z0 = s.position.x * _M_TO_MM, s.position.z * _M_TO_MM
    hw = s.dimensions.width / 2.0 * _M_TO_MM
    length = s.dimensions.length * _M_TO_MM
    height = s.dimensions.height * _M_TO_MM
    tol = 1e-3
    return (
        piece_bb.XMin >= x0 - tol
        and piece_bb.XMax <= x0 + length + tol
        and piece_bb.ZMin >= z0 - tol
        and piece_bb.ZMax <= z0 + height + tol
        and piece_bb.YMin >= -hw - tol
        and piece_bb.YMax <= hw + tol
    )


@pytest.mark.requires_freecad
def test_forward_cabin_has_berth_and_cushion(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    interior = build_interior(hull, deck, layout="Alternativ1")
    cabin = next(c for c in interior.compartments if c.spec.compartment_type == "forward_cabin")
    assert cabin.is_furnished
    labels = [b.Label for b in cabin.furniture]
    assert any("Berth" in label for label in labels)
    assert any("Cushion" in label for label in labels)
    for piece in cabin.furniture:
        assert _within(piece.Shape.BoundBox, cabin), f"{piece.Label} outside envelope"


@pytest.mark.requires_freecad
def test_salon_has_settee_and_table(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    interior = build_interior(hull, deck, layout="Alternativ1")
    salon = next(c for c in interior.compartments if c.spec.compartment_type == "salon")
    labels = [b.Label for b in salon.furniture]
    assert any("Settee" in label for label in labels)
    assert any("Table" in label for label in labels)
    for piece in salon.furniture:
        assert _within(piece.Shape.BoundBox, salon)
