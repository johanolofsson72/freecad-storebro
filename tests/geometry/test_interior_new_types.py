"""Geometry test: additional compartment types (spec 025 US3, T013).

Covers FR-003, FR-004, FR-005, FR-008, SC-003.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from storebro import InteriorParameterError, build_deck, build_hull, build_interior

_NEW_TYPES = """schema_version: 1
layout_name: NewTypesTest
source: test
compartments:
  - {name: AftBerth, type: aft_cabin, position: {x: 0.5, y: 0, z: 0.6}, dimensions: {length: 2.0, width: 2.0, height: 1.2}}
  - {name: Dinette, type: dinette, position: {x: 2.7, y: 0, z: 0.5}, dimensions: {length: 1.6, width: 2.0, height: 1.4}}
  - {name: ER, type: engine_room, position: {x: 4.5, y: 0, z: 0.4}, dimensions: {length: 1.6, width: 1.8, height: 1.2}}
  - {name: Locker, type: wet_locker, position: {x: 6.3, y: 0, z: 0.5}, dimensions: {length: 0.9, width: 1.8, height: 1.6}}
"""


@pytest.mark.requires_freecad
def test_new_types_furnished(freecad_doc: object, tmp_path: Path) -> None:
    p = tmp_path / "newtypes.yaml"
    p.write_text(_NEW_TYPES)
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    interior = build_interior(hull, deck, layout=str(p))

    by_type = {c.spec.compartment_type: c for c in interior.compartments}
    assert set(by_type) == {"aft_cabin", "dinette", "engine_room", "wet_locker"}
    for c in interior.compartments:
        assert c.is_furnished
        for pc in c.furniture:
            assert pc.Shape.isValid()

    # Each new type carries its appropriate fitting.
    assert any("Berth" in pc.Label for pc in by_type["aft_cabin"].furniture)
    assert any("Settee" in pc.Label or "Table" in pc.Label for pc in by_type["dinette"].furniture)
    er = by_type["engine_room"]
    block = next(pc for pc in er.furniture if "EngineBlock" in pc.Label)
    assert len(block.Shape.Solids) == 1 and block.Shape.isValid()  # single-solid new-type fitting
    locker = by_type["wet_locker"]
    assert any("Shelf" in pc.Label for pc in locker.furniture)
    for pc in locker.furniture:
        if "Locker" in pc.Label:
            assert len(pc.Shape.Solids) == 1 and pc.Shape.isValid()


@pytest.mark.requires_freecad
def test_overtall_new_type_fitting_rejected(freecad_doc: object, tmp_path: Path) -> None:
    # engine_room block (600) + raised top (150) = 750 mm > a 0.5 m compartment.
    bad = """schema_version: 1
layout_name: BadER
source: test
compartments:
  - {name: ER, type: engine_room, position: {x: 0.5, y: 0, z: 0.4}, dimensions: {length: 1.6, width: 1.8, height: 0.5}}
"""
    p = tmp_path / "bad.yaml"
    p.write_text(bad)
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    with pytest.raises(InteriorParameterError):
        build_interior(hull, deck, layout=str(p))
