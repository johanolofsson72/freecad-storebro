"""Geometry test: asymmetric layouts (spec 025 US4, T015).

Covers FR-006, FR-007, FR-013, SC-004.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from storebro import InteriorParameterError, build_deck, build_hull, build_interior

_ASYM = """schema_version: 1
layout_name: AsymTest
source: test
compartments:
  - {name: PortHead, type: head, position: {x: 3.2, y: 0.6, z: 0.5}, dimensions: {length: 1.0, width: 1.0, height: 1.4}}
  - {name: StbdLocker, type: wet_locker, position: {x: 3.2, y: -0.7, z: 0.5}, dimensions: {length: 0.8, width: 0.8, height: 1.6}}
"""


@pytest.mark.requires_freecad
def test_offcentre_compartments_build_at_their_y(freecad_doc: object, tmp_path: Path) -> None:
    p = tmp_path / "asym.yaml"
    p.write_text(_ASYM)
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    interior = build_interior(hull, deck, layout=str(p))

    by_name = {c.spec.name: c for c in interior.compartments}
    port_y = by_name["PortHead"].body.Shape.BoundBox.Center.y
    stbd_y = by_name["StbdLocker"].body.Shape.BoundBox.Center.y
    assert port_y > 300.0   # ~+600 mm (port)
    assert stbd_y < -300.0  # ~-700 mm (starboard)
    for c in interior.compartments:
        for pc in c.furniture:
            assert pc.Shape.isValid()


@pytest.mark.requires_freecad
def test_compartment_past_half_beam_rejected(freecad_doc: object, tmp_path: Path) -> None:
    bad = """schema_version: 1
layout_name: BadAsym
source: test
compartments:
  - {name: WayOut, type: head, position: {x: 3.0, y: 1.4, z: 0.5}, dimensions: {length: 1.0, width: 1.4, height: 1.4}}
"""
    p = tmp_path / "bad.yaml"
    p.write_text(bad)
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    with pytest.raises(InteriorParameterError) as exc:
        build_interior(hull, deck, layout=str(p))
    assert exc.value.field == "position.y"


@pytest.mark.requires_freecad
def test_offcentre_no_overlap_still_validates(freecad_doc: object, tmp_path: Path) -> None:
    # Two compartments at the same X but opposite Y do NOT overlap (FR-013).
    p = tmp_path / "asym.yaml"
    p.write_text(_ASYM)
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    interior = build_interior(hull, deck, layout=str(p))  # builds without overlap error
    assert len(interior.compartments) == 2

    # Two OVERLAPPING off-centre compartments are rejected.
    overlapping = """schema_version: 1
layout_name: Overlap
source: test
compartments:
  - {name: A, type: head, position: {x: 3.0, y: 0.2, z: 0.5}, dimensions: {length: 1.2, width: 1.2, height: 1.4}}
  - {name: B, type: wet_locker, position: {x: 3.0, y: 0.3, z: 0.5}, dimensions: {length: 1.2, width: 1.2, height: 1.4}}
"""
    bp = tmp_path / "overlap.yaml"
    bp.write_text(overlapping)
    with pytest.raises(InteriorParameterError):
        build_interior(hull, deck, layout=str(bp))
